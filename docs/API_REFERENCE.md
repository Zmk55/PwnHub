# API Reference

This document is under development. API endpoints are available at `http://localhost:5000/api/`.

## Interactive Documentation

FastAPI provides interactive API documentation:

- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

## Endpoints

### Devices

- `GET /api/devices` - List all registered devices
- `POST /api/devices/register` - Register a new device
- `POST /api/devices/heartbeat` - Send heartbeat from device

### Handshakes

- `GET /api/handshakes` - List all handshake files
- `POST /api/handshakes/upload` - Upload a handshake file

More detailed documentation coming soon...

