from pydantic import BaseModel
from typing import Optional


class DeviceRegisterRequest(BaseModel):
    """Request model for device registration."""
    serial: str
    hostname: Optional[str] = None
    ssh_fingerprint: Optional[str] = None
    image_gen: Optional[int] = 0
    handshake_count: Optional[int] = 0


class DeviceHeartbeatRequest(BaseModel):
    """Request model for device heartbeat."""
    serial: str
    hostname: Optional[str] = None
    ssh_fingerprint: Optional[str] = None
    image_gen: Optional[int] = None
    handshake_count: Optional[int] = None


class DeviceResponse(BaseModel):
    """Response model for device data."""
    id: Optional[int] = None
    serial: str
    name: Optional[str] = None
    hostname: Optional[str] = None
    ssh_fingerprint: Optional[str] = None
    image_gen: int = 0
    handshake_count: int = 0
    last_seen: Optional[int] = None
    last_ip: Optional[str] = None
    ssh_provisioned: bool = False

    class Config:
        from_attributes = True
