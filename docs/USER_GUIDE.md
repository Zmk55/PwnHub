# User Guide

Complete guide to using PwnHub for managing your Pwnagotchi devices.

## Overview

PwnHub provides a web-based interface for managing multiple Pwnagotchi devices. It allows you to:
- Monitor device status and handshake counts
- Access devices via web-based SSH terminal
- Download handshake files
- Create backups of device handshakes
- Manage device configurations

## Getting Started

1. **Access the Web Interface:**
   - Open your browser to `http://<hub-ip>:8080`
   - You should see the device management dashboard

2. **First Device Registration:**
   - Install the PwnHub agent plugin on your Pwnagotchi device
   - Device will automatically register when plugin loads
   - Device appears in the web UI within 60 seconds

## Device Management

### Device List

The main dashboard shows all registered devices in a table:

- **Serial**: Unique device identifier (CPU serial)
- **Hostname**: Device hostname
- **Last Seen**: Timestamp of last heartbeat
- **Handshake Count**: Number of handshakes stored
- **Status**: SSH key provisioning status (✓ = provisioned, ⚠ = not provisioned)
- **Actions**: Device management buttons

### Device Actions

**SSH Button:**
- Opens web-based SSH terminal to the device
- Requires SSH key to be provisioned first
- Opens in a new window/tab

**Files Button:**
- Opens modal showing all handshake files for the device
- Lists filename, size, upload date, and SHA256 hash
- Download individual handshake files

**Backup Button:**
- Creates a compressed tarball of all handshake files
- Backup saved to: `storage/backups/<serial>/YYYYMMDD.tar.gz`
- Shows success notification with backup filename and size

**Approve + Push Key Button:**
- Only visible for unprovisioned devices
- Pushes hub's SSH public key to device
- Required before using SSH access
- Shows success notification on completion

## SSH Key Provisioning

Before you can SSH into a device, you need to provision the SSH key:

1. **Ensure SSH keys are generated:**
   - SSH key pair should exist at `storage/keys/pwnhub_id_ed25519` and `.pub`

2. **Provision key to device:**
   - Click "Approve + Push Key" button for the device
   - Confirm the action in the dialog
   - Wait for success notification
   - Device status changes to "provisioned" (green ✓)

3. **Verify provisioning:**
   - Status icon should show green ✓
   - SSH button should become enabled

**Note:** SSH provisioning requires:
- Device to have an IP address (device must have sent a heartbeat)
- Device to be accessible from hub
- SSH service running on device
- Device to accept password authentication (for initial key push)

## Handshake Management

### Viewing Handshakes

1. Click "Files" button for a device
2. Modal opens showing all handshake files
3. Table displays:
   - Filename
   - File size (formatted as KB/MB)
   - Upload date
   - SHA256 hash (truncated)
   - Download link

### Downloading Handshakes

1. Click "Files" button to open handshake list
2. Click "Download" link next to desired file
3. File downloads to your browser's download folder

### Handshake Files

Handshake files are stored per device:
- Location: `storage/handshakes/<serial>/`
- Filename format: `YYYYMMDD_HHMMSS_<original>.cap`
- Automatically uploaded from devices if `push_handshakes` is enabled

## Backups

### Creating Backups

1. Click "Backup" button for a device
2. Confirm backup creation
3. Backup is created as compressed tarball
4. Success notification shows backup filename and size

### Backup Location

Backups are stored at:
- `storage/backups/<serial>/YYYYMMDD.tar.gz`
- Contains all handshake files for that device
- Can be downloaded manually from hub

### Automated Backups

Set up cron job or systemd timer to create backups automatically:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/PwnHub/deploy && docker-compose exec pwnhub-api curl -X POST http://localhost:5000/api/devices/SERIAL/backup
```

## Web-Based SSH Terminal

### Accessing Terminal

1. Ensure device SSH key is provisioned
2. Click "SSH" button for the device
3. Terminal opens in new window
4. You're now connected via SSH to the device

### Using the Terminal

- Standard SSH session
- Use exit command or close window to disconnect
- Terminal supports standard Linux commands
- Full shell access to device

**Note:** Terminal connection uses SSH key authentication, so no password is required once provisioned.

## Retention Policy

PwnHub automatically cleans up old handshake files based on retention policy:

- **Retention Days**: Keeps handshakes for last N days (default: 90)
- **Max Size**: Maximum GB per device (default: 10 GB)
- **Cleanup Interval**: Runs every N hours (default: 24)

Configure retention in `.env` file:
- `RETENTION_ENABLED=true`
- `RETENTION_DAYS=90`
- `RETENTION_MAX_GB_PER_DEVICE=10`
- `RETENTION_INTERVAL_HOURS=24`

**How it works:**
- Files older than retention days are automatically deleted
- If total size exceeds limit, oldest files are deleted first
- Device handshake count is updated after cleanup
- Cleanup runs automatically in background

## Troubleshooting

### Device Not Appearing

- Check device can reach hub API: `curl http://<hub-ip>:5000/health`
- Verify agent plugin is installed and enabled
- Check device logs: `tail -f /var/log/pwnagotchi.log | grep PwnHub`
- Ensure device has sent a heartbeat

### SSH Connection Fails

- Verify SSH key is provisioned (green ✓ status)
- Check device has IP address (Last Seen column)
- Verify SSH key exists on hub: `ls -la storage/keys/`
- Test SSH manually: `ssh -i storage/keys/pwnhub_id_ed25519 pi@<device-ip>`

### Handshakes Not Uploading

- Check device `push_handshakes = true` in config
- Verify `handshake_path` exists on device
- Check device can reach hub API
- Verify device logs for upload errors

### Backup Fails

- Check hub has disk space: `df -h`
- Verify handshakes exist for device
- Check hub logs: `docker-compose logs pwnhub-api`

### Files Button Shows Empty

- Verify handshakes have been uploaded
- Check handshake files exist: `ls -la storage/handshakes/<serial>/`
- Refresh device list and try again

## Best Practices

- **Regular Backups**: Create backups regularly, especially before major updates
- **Monitor Storage**: Check disk usage periodically: `df -h storage/`
- **Retention Policy**: Adjust retention settings based on your storage capacity
- **SSH Security**: Keep SSH private key secure, don't commit to version control
- **Network Security**: Use Tailscale or VPN for remote access
