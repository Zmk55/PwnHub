import hashlib
import time
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.database import get_conn, get_handshake_storage_path

router = APIRouter()


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@router.post("/upload")
async def upload_handshake(
    serial: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a handshake file from a device."""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # Check if device exists, create if not
        cursor.execute("SELECT id FROM devices WHERE serial = ?", (serial,))
        device = cursor.fetchone()
        
        if not device:
            # Create pending device record
            current_time = int(time.time())
            cursor.execute("""
                INSERT INTO devices (serial, name, hostname, ssh_fp, image_gen, 
                                   handshake_count, last_seen, last_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (serial, None, None, None, 0, 0, current_time, None))
            conn.commit()
        
        # Get storage path for this device
        storage_base = get_handshake_storage_path()
        device_dir = storage_base / serial
        device_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename: YYYYMMDD_HHMMSS_<original>
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = file.filename or "handshake"
        # Preserve file extension
        if "." in original_filename:
            name, ext = original_filename.rsplit(".", 1)
            timestamped_filename = f"{timestamp}_{name}.{ext}"
        else:
            timestamped_filename = f"{timestamp}_{original_filename}"
        
        file_path = device_dir / timestamped_filename
        
        # Save file to disk
        file_size = 0
        with open(file_path, "wb") as f:
            # Read file in chunks
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
        
        # Compute SHA256 hash
        sha256 = compute_sha256(file_path)
        
        # Insert metadata into handshakes table
        cursor.execute("""
            INSERT INTO handshakes (serial, filename, bytes, sha256, uploaded_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (serial, timestamped_filename, file_size, sha256))
        
        # Increment handshake_count for device
        cursor.execute("""
            UPDATE devices 
            SET handshake_count = handshake_count + 1
            WHERE serial = ?
        """, (serial,))
        
        conn.commit()
        
        return {
            "status": "ok",
            "filename": timestamped_filename,
            "sha256": sha256
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading handshake: {str(e)}")
    finally:
        conn.close()


@router.get("/")
async def list_handshakes():
    """List all handshake files."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, serial, filename, bytes, sha256, uploaded_at
        FROM handshakes
        ORDER BY uploaded_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    handshakes = []
    for row in rows:
        handshakes.append({
            "id": row[0],
            "serial": row[1],
            "filename": row[2],
            "bytes": row[3],
            "sha256": row[4],
            "uploaded_at": row[5]
        })
    
    return {"handshakes": handshakes}

