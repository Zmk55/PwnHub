import time
from fastapi import APIRouter, HTTPException, Request
from app.database import get_conn
from app.models import DeviceRegisterRequest, DeviceHeartbeatRequest, DeviceResponse

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded IP first (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded.split(",")[0].strip()
    # Fall back to direct client host
    return request.client.host if request.client else "unknown"


def row_to_device_response(row: tuple) -> DeviceResponse:
    """Convert database row tuple to DeviceResponse model."""
    return DeviceResponse(
        id=row[0],
        serial=row[1],
        name=row[2],
        hostname=row[3],
        ssh_fingerprint=row[4],
        image_gen=row[5] or 0,
        handshake_count=row[6] or 0,
        last_seen=row[7],
        last_ip=row[8],
        ssh_provisioned=bool(row[9] if len(row) > 9 else 0)
    )


@router.get("/", response_model=list[DeviceResponse])
async def list_devices():
    """List all registered devices, ordered by last_seen descending."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, serial, name, hostname, ssh_fp, image_gen, 
               handshake_count, last_seen, last_ip, ssh_provisioned
        FROM devices
        ORDER BY last_seen DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_device_response(row) for row in rows]


@router.post("/register", response_model=DeviceResponse)
async def register_device(request_body: DeviceRegisterRequest, request: Request):
    """Register a new device or update existing device by serial."""
    client_ip = get_client_ip(request)
    current_time = int(time.time())
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # Check if device exists
    cursor.execute("SELECT id FROM devices WHERE serial = ?", (request_body.serial,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing device
        cursor.execute("""
            UPDATE devices 
            SET hostname = ?, ssh_fp = ?, image_gen = ?, handshake_count = ?,
                last_seen = ?, last_ip = ?
            WHERE serial = ?
        """, (
            request_body.hostname,
            request_body.ssh_fingerprint,
            request_body.image_gen or 0,
            request_body.handshake_count or 0,
            current_time,
            client_ip,
            request_body.serial
        ))
    else:
        # Insert new device
        cursor.execute("""
            INSERT INTO devices 
            (serial, name, hostname, ssh_fp, image_gen, handshake_count, last_seen, last_ip, ssh_provisioned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_body.serial,
            None,  # name (can be set later)
            request_body.hostname,
            request_body.ssh_fingerprint,
            request_body.image_gen or 0,
            request_body.handshake_count or 0,
            current_time,
            client_ip,
            0  # ssh_provisioned = false by default
        ))
    
        # Get the updated/inserted device
        cursor.execute("""
            SELECT id, serial, name, hostname, ssh_fp, image_gen, 
                   handshake_count, last_seen, last_ip, ssh_provisioned
            FROM devices
            WHERE serial = ?
        """, (request_body.serial,))
    
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to register device")
    
    return row_to_device_response(row)


@router.post("/heartbeat")
async def heartbeat(request_body: DeviceHeartbeatRequest, request: Request):
    """Receive heartbeat from device and update last_seen and optional fields."""
    client_ip = get_client_ip(request)
    current_time = int(time.time())
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # Check if device exists
    cursor.execute("SELECT id FROM devices WHERE serial = ?", (request_body.serial,))
    device = cursor.fetchone()
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with serial {request_body.serial} not found")
    
    # Build update query dynamically based on provided fields
    update_fields = ["last_seen = ?", "last_ip = ?"]
    update_values = [current_time, client_ip]
    
    if request_body.hostname is not None:
        update_fields.append("hostname = ?")
        update_values.append(request_body.hostname)
    
    if request_body.ssh_fingerprint is not None:
        update_fields.append("ssh_fp = ?")
        update_values.append(request_body.ssh_fingerprint)
    
    if request_body.image_gen is not None:
        update_fields.append("image_gen = ?")
        update_values.append(request_body.image_gen)
    
    if request_body.handshake_count is not None:
        update_fields.append("handshake_count = ?")
        update_values.append(request_body.handshake_count)
    
    update_values.append(request_body.serial)
    
    query = f"""
        UPDATE devices 
        SET {', '.join(update_fields)}
        WHERE serial = ?
    """
    
    cursor.execute(query, update_values)
    conn.commit()
    conn.close()
    
    return {"status": "ok"}


@router.post("/{serial}/provision-ssh")
async def provision_ssh(serial: str):
    """Provision SSH key to device by pushing public key via ssh-copy-id."""
    import subprocess
    from pathlib import Path
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # Get device from database
    cursor.execute("""
        SELECT id, serial, last_ip FROM devices WHERE serial = ?
    """, (serial,))
    device = cursor.fetchone()
    
    if not device:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Device with serial {serial} not found")
    
    device_ip = device[2]  # last_ip
    
    if not device_ip:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Device {serial} has no IP address. Device must send a heartbeat first.")
    
    # Validate SSH public key exists
    ssh_pub_key = Path("/srv/pwnhub/keys/pwnhub_id_ed25519.pub")
    if not Path("/srv/pwnhub").exists():
        ssh_pub_key = Path("./storage/keys/pwnhub_id_ed25519.pub")
    
    if not ssh_pub_key.exists():
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"SSH public key not found at {ssh_pub_key}. Please generate SSH key pair first."
        )
    
    # Validate IP format (basic check)
    import re
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if not ip_pattern.match(device_ip):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Invalid IP address format: {device_ip}")
    
    # Call helper script for ssh-copy-id
    ssh_username = "pi"
    script_path = Path("/usr/local/bin/provision-ssh-key.sh")
    if not script_path.exists():
        script_path = Path("./scripts/provision-ssh-key.sh")
    
    if not script_path.exists():
        conn.close()
        raise HTTPException(status_code=500, detail="Provision script not found")
    
    try:
        # Execute provision script with timeout
        result = subprocess.run(
            [str(script_path), device_ip, ssh_username],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "ssh-copy-id failed"
            conn.close()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to provision SSH key: {error_msg}"
            )
        
        # Update database: set ssh_provisioned = 1
        cursor.execute("""
            UPDATE devices 
            SET ssh_provisioned = 1
            WHERE serial = ?
        """, (serial,))
        
        conn.commit()
        conn.close()
        
        return {"status": "ok", "message": "SSH key provisioned successfully"}
        
    except subprocess.TimeoutExpired:
        conn.close()
        raise HTTPException(status_code=500, detail="SSH provisioning timed out")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error during SSH provisioning: {str(e)}")

