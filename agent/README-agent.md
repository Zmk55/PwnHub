# PwnHub Agent Plugin

This is the Pwnagotchi plugin that enables devices to connect to a PwnHub server.

## Installation

1. Copy the plugin file to your Pwnagotchi device:

```bash
scp agent/pwnhub.py root@pwnagotchi:/usr/local/share/pwnagotchi/custom-plugins/
```

Or manually copy `pwnhub.py` to `/usr/local/share/pwnagotchi/custom-plugins/` on your device.

2. Set proper permissions:

```bash
chmod 644 /usr/local/share/pwnagotchi/custom-plugins/pwnhub.py
chown root:root /usr/local/share/pwnagotchi/custom-plugins/pwnhub.py
```

3. Add configuration to `/etc/pwnagotchi/config.toml`:

```toml
[pwnhub]
enabled = true
hub_url = "http://10.67.0.1:5000"
auth_token = ""
heartbeat_interval = 300
push_handshakes = true
upload_method = "http"
handshake_path = "~/handshakes"
agent_id_file = "~/.pwnhub_agent_state.json"
log_level = "INFO"
```

4. Restart the Pwnagotchi service:

```bash
systemctl restart pwnagotchi
```

## Configuration Options

- `enabled` (default: `true`): Enable or disable the plugin
- `hub_url` (default: `"http://10.67.0.1:5000"`): URL of the PwnHub server API
- `auth_token` (default: `""`): Authentication token for hub communication (not enforced yet, present for future)
- `heartbeat_interval` (default: `300`): Seconds between heartbeat messages
- `push_handshakes` (default: `true`): Automatically upload captured handshakes
- `upload_method` (default: `"http"`): Method for uploads ("http" or "ssh")
- `handshake_path` (default: `"~/handshakes"`): Local path to handshake files
- `agent_id_file` (default: `"~/.pwnhub_agent_state.json"`): Path to agent state file for tracking device identity and image generation
- `log_level` (default: `"INFO"`): Logging level (DEBUG, INFO, WARNING, ERROR)

## Features

- **Automatic Device Registration**: Device registers with hub on plugin load
- **Device Identity Tracking**: Captures CPU serial, machine-id, and SSH host key fingerprint
- **Image Generation Detection**: Tracks when device is re-imaged on the same hardware (increments `image_gen`)
- **Periodic Heartbeat**: Sends heartbeat to hub every `heartbeat_interval` seconds
- **Automatic Handshake Upload**: Uploads `.cap`, `.pcap`, and `.hccapx` files to hub
- **State Persistence**: Saves device state to track identity across reboots

## How It Works

1. On plugin load, the agent:
   - Captures device identity (serial, machine-id, SSH fingerprint)
   - Loads previous state if available
   - Detects if this is a new image on the same hardware
   - Registers with the hub immediately

2. Background thread continuously:
   - Sends heartbeat every `heartbeat_interval` seconds
   - Syncs handshakes from `handshake_path` if `push_handshakes` is enabled

3. On handshake capture:
   - If `push_handshakes` is enabled, uploads the file immediately
   - Deletes local file on successful upload

## Troubleshooting

### Check plugin logs:

```bash
tail -f /var/log/pwnagotchi.log | grep PwnHub
```

### Verify state file exists:

```bash
cat /root/.pwnhub_agent_state.json
```

The state file should contain:
- `device_info.serial`: Device CPU serial
- `device_info.machine_id`: System machine ID
- `device_info.ssh_fp`: SSH host key fingerprint
- `image_gen`: Image generation counter
- `last_registered`: Timestamp of last registration

### Check network connectivity to hub:

```bash
curl http://10.67.0.1:5000/health
```

### Verify handshake_path exists and is readable:

```bash
ls -la ~/handshakes
```

### Common Issues

**Device not appearing in web UI:**
- Check that `hub_url` is correct and accessible from the device
- Verify device registration in logs: `grep "Device registered" /var/log/pwnagotchi.log`

**Handshakes not uploading:**
- Verify `push_handshakes = true` in config
- Check `handshake_path` exists and contains `.cap`, `.pcap`, or `.hccapx` files
- Check for upload errors in logs: `grep "uploading handshake" /var/log/pwnagotchi.log`

**Plugin not loading:**
- Check plugin syntax: `python3 -m py_compile /usr/local/share/pwnagotchi/custom-plugins/pwnhub.py`
- Verify permissions on plugin file
- Check Pwnagotchi logs for import errors

