# Installation Guide

This guide explains how to set up and run PwnHub using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- A Raspberry Pi 5 or other Linux host
- Network access to connect Pwnagotchi devices

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/Zmk55/PwnHub.git
cd PwnHub
```

2. Navigate to the deploy directory:

```bash
cd deploy
```

3. Copy the example environment file:

```bash
cp .env.example .env
```

4. Edit `.env` if needed (default values should work for local setup)

5. Start the services:

```bash
docker-compose up -d --build
```

6. Verify services are running:

```bash
docker-compose ps
```

7. Access the web interface at `http://localhost:8080`

8. Access the API documentation at `http://localhost:5000/docs`

## SSH Key Setup

Before you can use SSH features, you need to generate an SSH key pair for the hub:

1. Generate SSH key pair:

```bash
mkdir -p storage/keys
ssh-keygen -t ed25519 -f storage/keys/pwnhub_id_ed25519 -N ""
```

This will create:
- Private key: `storage/keys/pwnhub_id_ed25519`
- Public key: `storage/keys/pwnhub_id_ed25519.pub`

2. The private key will be used for SSH connections to devices
3. The public key will be pushed to devices via the "Approve + Push Key" button in the web UI

**Important:** Keep the private key secure and never commit it to version control.

## Environment Configuration

The `.env` file supports the following options:

- `HUB_HOST`: Hub hostname or IP (default: `localhost`)
- `RETENTION_ENABLED`: Enable/disable retention cleanup (default: `true`)
- `RETENTION_DAYS`: Number of days to keep handshakes (default: `90`)
- `RETENTION_MAX_GB_PER_DEVICE`: Maximum GB per device (default: `10`)
- `RETENTION_INTERVAL_HOURS`: Hours between cleanup runs (default: `24`)

## Network Setup

### USB Networking

For USB-connected Pwnagotchi devices, you may want to set up predictable IP addresses:

1. Install `dnsmasq` or configure `systemd-networkd`
2. Configure static IP mappings per USB port
3. Devices will typically appear on `10.67.0.x` network

### Device Network Access

Ensure devices can reach the hub:
- Hub API: `http://<hub-ip>:5000`
- Hub should be accessible from device network
- For USB networking, use hub's USB interface IP
- For Wi-Fi, ensure devices and hub are on same network

## Storage Setup

Data is stored in the `deploy` directory:

- `./data/`: SQLite database (`pwnhub.db`)
- `./storage/handshakes/`: Handshake files per device
- `./storage/backups/`: Backup tarballs per device
- `./storage/keys/`: SSH keys (private and public)

**Backup Recommendation:** Regularly backup the `deploy` directory to external storage.

## First Device Connection

1. **Install agent plugin on Pwnagotchi:**
   - Copy `agent/pwnhub.py` to device
   - Configure in `/etc/pwnagotchi/config.toml`

2. **Device will register automatically:**
   - Device appears in web UI within 60 seconds
   - Device shows as "pending" until approved

3. **Provision SSH key:**
   - Click "Approve + Push Key" button in web UI
   - This pushes the hub's public key to the device
   - Device status changes to "provisioned"

4. **Access device via SSH:**
   - Click "SSH" button to open web terminal
   - Or use SSH directly from command line

## Backup Configuration

Backups are created per device:
- Location: `storage/backups/<serial>/YYYYMMDD.tar.gz`
- Contains all handshake files for that device
- Created on-demand via "Backup" button in web UI

**Automated Backups:**
- Schedule regular backups using cron or systemd timer
- Example cron job (daily at 2 AM):
  ```bash
  0 2 * * * cd /path/to/PwnHub/deploy && docker-compose exec pwnhub-api python3 -c "from app.routers.devices import backup_device; import asyncio; asyncio.run(backup_device('SERIAL'))"
  ```

## Stopping Services

To stop all services:

```bash
docker-compose down
```

To stop and remove volumes (deletes all data):

```bash
docker-compose down -v
```

## Troubleshooting

### Check logs:

```bash
docker-compose logs -f pwnhub-api
docker-compose logs -f pwnhub-web
docker-compose logs -f ttyd
```

### Check if ports are already in use:

```bash
netstat -tulpn | grep -E '5000|8080|7681'
```

### Common Issues

**Services not starting:**
- Check Docker is running: `docker ps`
- Check disk space: `df -h`
- Check logs for errors

**Devices not appearing:**
- Verify device can reach hub API
- Check device plugin is enabled
- Check device logs: `tail -f /var/log/pwnagotchi.log | grep PwnHub`

**SSH connection fails:**
- Verify SSH key is provisioned (check Status column)
- Verify device IP is correct (check Last Seen)
- Check SSH key exists: `ls -la storage/keys/`

**Handshakes not uploading:**
- Check device `push_handshakes` config
- Check device `handshake_path` exists
- Verify hub has disk space: `df -h`
