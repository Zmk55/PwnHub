import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import devices, handshakes
from app.database import init_db, get_conn, get_handshake_storage_path

logger = logging.getLogger(__name__)


def run_retention_cleanup():
    """Run retention policy cleanup job."""
    retention_enabled = os.getenv("RETENTION_ENABLED", "true").lower() == "true"
    if not retention_enabled:
        logger.info("Retention cleanup disabled")
        return
    
    try:
        retention_days = int(os.getenv("RETENTION_DAYS", "90"))
        retention_max_gb = float(os.getenv("RETENTION_MAX_GB_PER_DEVICE", "10"))
        retention_max_bytes = retention_max_gb * 1024 * 1024 * 1024
        
        logger.info(f"Running retention cleanup: days={retention_days}, max_gb={retention_max_gb}")
        
        conn = get_conn()
        cursor = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_timestamp = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get all devices
        cursor.execute("SELECT serial FROM devices")
        devices = cursor.fetchall()
        
        total_deleted = 0
        
        for (device_serial,) in devices:
            # Get handshakes for device
            cursor.execute("""
                SELECT id, filename, bytes, uploaded_at
                FROM handshakes
                WHERE serial = ?
                ORDER BY uploaded_at ASC
            """, (device_serial,))
            handshakes = cursor.fetchall()
            
            if not handshakes:
                continue
            
            # Get storage path
            storage_base = get_handshake_storage_path()
            device_dir = storage_base / device_serial
            
            deleted_count = 0
            
            # Delete files older than retention_days
            for handshake_id, filename, size_bytes, uploaded_at in handshakes:
                if uploaded_at:
                    try:
                        # Parse SQLite timestamp (format: YYYY-MM-DD HH:MM:SS)
                        uploaded_dt = datetime.strptime(uploaded_at, "%Y-%m-%d %H:%M:%S")
                        if uploaded_dt < cutoff_date:
                            # Delete old file
                            file_path = device_dir / filename
                            if file_path.exists():
                                file_path.unlink()
                                logger.debug(f"Deleted old handshake: {device_serial}/{filename}")
                            
                            # Delete from database
                            cursor.execute("DELETE FROM handshakes WHERE id = ?", (handshake_id,))
                            deleted_count += 1
                            total_deleted += 1
                            continue
                    except ValueError:
                        # Invalid date format, skip
                        logger.warning(f"Invalid date format for handshake {handshake_id}: {uploaded_at}")
                        continue
            
            # Re-fetch remaining handshakes and calculate total size
            cursor.execute("""
                SELECT id, filename, bytes, uploaded_at
                FROM handshakes
                WHERE serial = ?
                ORDER BY uploaded_at ASC
            """, (device_serial,))
            remaining_handshakes = cursor.fetchall()
            
            # Calculate total size of remaining handshakes
            total_size = sum(row[2] for row in remaining_handshakes if row[2])
            
            # If still over size limit, delete oldest files
            if total_size > retention_max_bytes:
                for handshake_id, filename, size_bytes, uploaded_at in remaining_handshakes:
                    if total_size <= retention_max_bytes:
                        break
                    
                    # Delete file
                    file_path = device_dir / filename
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug(f"Deleted oversized handshake: {device_serial}/{filename}")
                    
                    # Delete from database
                    cursor.execute("DELETE FROM handshakes WHERE id = ?", (handshake_id,))
                    deleted_count += 1
                    total_deleted += 1
                    total_size -= (size_bytes or 0)
            
            # Update device handshake_count
            cursor.execute("""
                UPDATE devices 
                SET handshake_count = (
                    SELECT COUNT(*) FROM handshakes WHERE serial = ?
                )
                WHERE serial = ?
            """, (device_serial, device_serial))
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} handshakes for device {device_serial}")
        
        conn.commit()
        conn.close()
        
        if total_deleted > 0:
            logger.info(f"Retention cleanup completed: {total_deleted} handshakes deleted")
        else:
            logger.info("Retention cleanup completed: no handshakes deleted")
            
    except Exception as e:
        logger.error(f"Error during retention cleanup: {e}")


async def retention_cleanup_task():
    """Background task for retention cleanup."""
    retention_interval = int(os.getenv("RETENTION_INTERVAL_HOURS", "24")) * 3600
    
    while True:
        try:
            await asyncio.sleep(retention_interval)
            run_retention_cleanup()
        except Exception as e:
            logger.error(f"Error in retention cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize database
    init_db()
    
    # Start retention cleanup task
    retention_task = asyncio.create_task(retention_cleanup_task())
    
    yield
    
    # Shutdown: cancel retention task
    retention_task.cancel()
    try:
        await retention_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="PwnHub API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(handshakes.router, prefix="/api/handshakes", tags=["handshakes"])


@app.get("/")
async def root():
    return {"message": "PwnHub API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}

