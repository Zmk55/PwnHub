# 🧠 PwnHub — Development Guide & Playbook

## Overview
**PwnHub** is a management and monitoring server for multiple **Pwnagotchi** devices.
It runs on a **Raspberry Pi 5** (or other Linux host) and provides a **local web interface** for:
- Device discovery and management via USB or network
- Automated handshake ingestion and backup
- SSH / SFTP / web terminal access per device
- Configuration syncing and backup/restore
- Persistent tracking of devices by hardware serial, even across SD card swaps

This document is the canonical developer playbook: architecture, workflows, file structure, tasks, and checklists to build a professional, reliable, and user-friendly PwnHub solution.

---

## Goals & Success Criteria

**Primary goals**
- Plug-and-play USB hub detection for Pwnagotchi devices with minimal user setup.
- Persistent, hardware-serial-based device identity that survives SD card swaps.
- Friendly web UI listing devices with actions: SSH, SFTP, GUI (ttyd), Settings, Backup, Restore.
- Automated handshake ingestion and safe storage.
- Easy installation via Docker Compose, and optional pre-built Pi image for one-click deployment.

**Success metrics**
- Device shows up in UI within 30 seconds of being plugged in.
- Device remains recognized by hardware serial after re-imaging or SD swap.
- Web-based SSH connects to device via one click (after provisioning a key).
- Handshake files uploaded and stored at `/srv/pwnhub/handshakes/<device_serial>/` and downloadable.
- Basic security controls in place: auth tokens for agent->hub, web UI restricted to LAN or protected by TLS/auth.

---

## High-level Architecture

```
                                +----------------------------+
                                |        User Browser        |
                                |  (Dashboard / Admin UI)    |
                                +-------------+--------------+
                                              |
                               HTTPS / HTTP | Web API (FastAPI)
                                              |
+------------------------+   +---------------v--------------+   +------------------------+
| Raspberry Pi 5 (Hub)   |   |  Docker Compose / Services  |   | External Storage / NAS |
| - usb0..usbN interfaces|   | - pwnhub-api (FastAPI)      |   | - optional backups     |
| - local network access |   | - pwnhub-web (frontend)     |   |                        |
|                        |   | - ttyd (web terminal proxy) |   |                        |
|                        |   | - filebrowser (SFTP UI)     |   |                        |
|                        |   | - dnsmasq (DHCP for usb(s)) |   |                        |
+------------+-----------+   +---------------+--------------+   +------------------------+
             |                                |
             | USB Ethernet / Link-local      |
             |                                |
+------------v-----------+                    |
| Pwnagotchi Devices     |                    |
| - pwnhub plugin agent  |--------------------+
| - reports serial/sshfp |
+------------------------+
```

Key principles:
- Use Docker Compose for modular services and easy deployment.
- Device-side code is a Pwnagotchi **plugin** (`pwnhub.py`) placed in `custom-plugins/` and configured by `config.toml`.
- Device identity anchored by hardware serial (`/proc/cpuinfo`), machine-id, and SSH host key fingerprint.
- Hub supports both push (device -> hub) and pull (hub -> device via rsync/ssh) models for handshake transfer.

---

## Components & Responsibilities

### Hub (Raspberry Pi 5)
- Runs Docker Compose stack hosting API, UI, terminal proxy, and file manager.
- Provides predictable networking for plugged-in Pwnagotchis (via dnsmasq or systemd-networkd static host IPs per USB port).
- Stores handshakes and device backups under `/srv/pwnhub/` with per-device directories.
- Exposes REST API for registration, heartbeat, handshake upload, backup, and admin actions.

### PwnHub API (FastAPI)
- Endpoints:
  - `POST /api/devices/register` — register new device (serial, hostname, ssh_fingerprint, handshake_count, image_gen)
  - `POST /api/devices/heartbeat` — periodic heartbeat to update last_seen and metrics
  - `GET /api/devices` — list devices and statuses
  - `POST /api/handshakes/upload` — accept handshake file multipart uploads
  - `POST /api/devices/{serial}/backup` — request a backup (pull) of device files
  - `POST /api/devices/{serial}/restore` — restore files to device
  - `POST /api/devices/{serial}/command` — run one-off commands (careful; admin-only)
- Auth: support a simple bearer token for agent->hub calls; extendable to mTLS if required.
- Storage: start with SQLite for MVP; allow migration to Postgres later.

### Web UI (static React or server-rendered)
- Device grid/cards with metadata (name, serial, last_seen, handshake_count, battery if available).
- Action buttons per device: SSH, Files, Backup, Restore, Rename, Settings.
- New-device pending registration modal to approve and name devices.
- Admin page for settings, tokens, storage status, and logs.

### Web-based SSH (ttyd/wetty)
- ttyd container wraps the SSH command for the target device; hub will create an ephemeral SSH session connecting to device IP.
- Prefer connecting from the hub to device over local USB network; store private key on hub protected by filesystem permissions and require user auth in UI before using it.

### File browser / SFTP (filebrowser or similar)
- Allow browsing stored files under `/srv/pwnhub/handshakes/<serial>` and download/upload where appropriate.
- Optionally expose a direct SFTP web UI for backups and manual file operations.

### Agent (Pwnagotchi plugin)
- Runs as a Pwnagotchi plugin (`pwnhub.py`) in `/usr/local/share/pwnagotchi/custom-plugins/`.
- Responsibilities:
  - Gather device info: hardware serial, machine-id, hostname, ssh host fingerprint, handshake_count.
  - Register to hub on first boot or when `register_on_boot = true` in config.
  - Send periodic heartbeat (configurable interval).
  - Upload handshake files via HTTP multipart POST, or rsync via SSH as fallback.
  - Persist local agent state in `/root/.pwnhub_agent_state.json` to detect SD swaps (image_gen increment).

---

## File Layout (Repository)

```
PwnHub/
├─ pwnhub-api/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ database.py
│  │  ├─ models.py
│  │  ├─ routers/
│  │  │  ├─ devices.py
│  │  │  └─ handshakes.py
│  ├─ Dockerfile
│  └─ requirements.txt
│
├─ web/
│  ├─ index.html
│  ├─ app.js
│  └─ Dockerfile
│
├─ agent/
│  ├─ pwnhub.py
│  └─ README-agent.md
│
├─ deploy/
│  ├─ docker-compose.yml
│  ├─ systemd-networkd/   # sample .network files
│  └─ dnsmasq.conf
│
├─ docs/
│  ├─ INSTALL.md
│  ├─ USER_GUIDE.md
│  └─ API_REFERENCE.md
│
├─ scripts/
│  ├─ connect-to-device.sh
│  ├─ sync_all.sh
│  └─ backup_all.sh
│
├─ tests/
│  ├─ test_api.py
│  └─ test_agent.py
├─ .github/
│  └─ workflows/ci.yml
├─ PwnHub_PLAN.md
└─ PwnHub_GUIDE.md
```

---

## Phase-by-Phase Plan (Concrete Tasks)

### Phase 0 — Prep & Repo
**Goal:** repo scaffolding and dev environment ready.
- Create directories and placeholder files (use the file layout above).
- Add LICENSE (MIT or Apache2), .gitignore, README.md, CONTRIBUTING.md.
- Create PwnHub_PLAN.md and PwnHub_GUIDE.md (this file).

**Deliverable:** repo with skeleton committed to GitHub.

### Phase 1 — MVP: Discovery & Register (2–4 days)
**Goal:** Devices can register and appear on the hub list.
- Implement FastAPI service with the endpoints above; use SQLite for data.
- Implement `agent/pwnhub.py` plugin with register & heartbeat.
- Minimal web UI to list devices and show last_seen/handshake_count.
- Example systemd-networkd and dnsmasq configs to create predictable USB host IPs.

**Acceptance:** Plugin registers device and device appears in web UI within 60s.

### Phase 2 — Handshake Sync & Storage (2–4 days)
**Goal:** Reliable handshake ingestion and storage.
- Implement `/api/handshakes/upload` to accept multipart POST file uploads.
- Agent sends new .cap/.pcap/.hccapx files and deletes local copies on success (or mark uploaded).
- Hub stores files under `/srv/pwnhub/handshakes/<serial>/` and computes SHA256 for each file for integrity.
- UI displays handshake counts and last upload timestamp per device.

**Acceptance:** File uploaded from device is visible in server directory and via UI download link.

### Phase 3 — Web SSH, Files, and UX (2–5 days)
**Goal:** Tight one-click UX for common operations.
- Integrate ttyd and write `connect-to-device.sh` wrapper that SSHes to device IP using hub's key.
- Add filebrowser to browse backup folders and device handshakes.
- Polished UI: device cards, new-device modal, device actions, logs view, settings page.
- Add confirmation modals for destructive actions (factory reset, wipe handshakes).

**Acceptance:** Admin can SSH into device from browser and download a handshake via UI.

### Phase 4 — Automation, Provisioning, & Policies (3–6 days)
**Goal:** Make onboarding repeatable and safe.
- Add key-provisioning flow: Admin approves new device, then hub pushes public key to device via agent endpoint or `ssh-copy-id` (depending on trust model).
- Scheduled tasks: automatic handshake sync every X minutes, retention cleanup policy (e.g., keep 90 days or N GB).
- Add device tagging/grouping and bulk actions (backup all, reboot all).

**Acceptance:** Admin approves device and can SSH without password.

### Phase 5 — Packaging & Distribution (3–6 days)
**Goal:** Provide easy install and distribution options.
- Finalize Dockerfiles for each service and create deploy/docker-compose.yml.
- Create an automated build and release process for Docker images (GHCR or DockerHub).
- Optionally build a Pi OS image (using pi-gen or packer) with Docker and Docker Compose preinstalled and a post-install setup script.

**Acceptance:** Fresh Pi 5 can be set up from `git clone` + `docker-compose up -d` following docs.

### Phase 6 — Hardening & Community Release (ongoing)
**Goal:** Productionize and publish.
- Add auth (local user accounts or LDAP/OAuth), TLS, rate limiting, and logging retention.
- Add test coverage and CI (GitHub Actions): unit tests, integration tests, and build checks.
- Publish documentation and sample images, encourage community contributions.

**Acceptance:** Release v1.0 with docs, CI, and basic security checklist.

---

## Implementation Details & Examples

### Device identity detection (agent)
Agent should collect a set of identifying values in this order of preference:
1. CPU / hardware serial (`/proc/cpuinfo` Serial)
2. `/proc/device-tree/serial-number`
3. `/etc/machine-id` (not stable across images; used to detect new image)
4. SSH host key fingerprint (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key`)

Persist `agent_state` locally at `/root/.pwnhub_agent_state.json`:
```json
{
  "device_info": {
     "serial": "00000000abcdef",
     "machine_id": "....",
     "ssh_fp": "...."
  },
  "image_gen": 0,
  "last_registered": 1690000000
}
```

When plugin boots, it compares serial and machine_id to detect whether the same hardware has a new image (increment `image_gen`). The hub can show `image_gen` in UI to indicate number of times the SD image was changed/re-imaged.

### Example minimal register payload
```json
{
  "serial": "00000000abcdef",
  "hostname": "pwn-ghost",
  "ssh_fingerprint": "ecdsa-sha2-nistp256 AAAA...",
  "handshake_count": 12,
  "image_gen": 0
}
```

### Example API behavior
- `POST /api/devices/register`:
  - If `serial` exists → update `last_seen`, `hostname`, `ssh_fp`, `handshake_count` → return existing device record.
  - If `serial` unknown → create device record with `status: pending` and return `{ "status": "pending", "message": "Approve device in UI" }`.
- `POST /api/devices/heartbeat`:
  - Accepts `serial` and metrics; updates `last_seen`, `last_ip` (derived from request or agent), `handshake_count` and returns 200.

### Handshake upload
- Endpoint: `POST /api/handshakes/upload`
- Accepts multipart form-data with fields: `serial`, `file`.
- Server stores at `/srv/pwnhub/handshakes/<serial>/YYYYMMDD_HHMMSS_filename.cap` and returns `{ "status":"ok", "path": "..." }`.
- Hub computes SHA256 and saves metadata in DB (filename, size, sha256, uploaded_at).

---

## Security & Hardening Checklist (must do before wide deployment)
- Use **SSH keys** for any hub<->device SSH operations; do not store plaintext passwords.
- Protect the web UI: restrict to LAN, or require auth + TLS. For remote access, use Tailscale or VPN.
- Require an **auth token** in plugin config to authenticate agent->hub API calls. Rotate tokens periodically.
- Limit file upload size and validate file types (accept only `.cap`, `.pcap`, `.hccapx`).
- Run containers with least privileges; do not bind mount sensitive host directories unless necessary.
- Regular backups of `/srv/pwnhub` to an external location.
- Log and monitor suspicious events (many registration attempts, repeated failed uploads).

---

## Testing Strategy
- Unit tests for API (pytest): register, heartbeat, handshake upload, DB migrations.
- Agent tests: mock responses for register and heartbeat; test handshake upload behavior (mock server).
- Integration tests: spin up API in Docker, run agent script against it, ensure DB records created and filesystem stored.
- Manual tests: plug a Pwnagotchi into Pi host, confirm registration flow, handshake upload and UI operations.

---

## Helpful Scripts (suggested)
- `scripts/sync_all.sh` — iterate devices and rsync handshakes to hub (if using hub pull mode).
- `scripts/backup_all.sh` — create a timestamped tarball of `/srv/pwnhub` and rotate.
- `scripts/connect-to-device.sh` — wrapper used by ttyd to SSH into device by serial (resolves IP from DB).

---

## Developer Workflow & Best Practices
- Branch naming: `feat/<name>`, `fix/<name>`, `docs/<name>`.
- PR checklist: linting, unit tests, changeset, documentation update, reviewer assigned.
- Commit style: Conventional Commits (feat, fix, chore, docs, refactor).
- Keep `main` protected and deployable; merge from `develop` via reviewed PRs.

---

## Deploy & Quickstart (for your Pi 5)

### Prereqs (on Pi 5)
- Debian/Ubuntu based OS or Raspberry Pi OS (64-bit recommended)
- Docker & docker-compose
- Optional: `dnsmasq` for DHCP on USB interfaces, `systemd-networkd` for predictable interface naming

### Quick start (developer mode)
1. Clone repo:
```bash
git clone https://github.com/Zmk55/PwnHub.git
cd PwnHub/deploy
```
2. Copy example env and adjust:
```bash
cp .env.example .env
# edit .env to set HUB_HOST, etc.
```
3. Start services:
```bash
docker-compose up -d --build
```
4. Start dev API locally (optional):
```bash
cd pwnhub-api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

### Install the plugin on a Pwnagotchi
1. Copy agent plugin file to device:
```bash
scp agent/pwnhub.py pi@pwnagotchi:/tmp/
ssh pi@pwnagotchi "sudo mv /tmp/pwnhub.py /usr/local/share/pwnagotchi/custom-plugins/; sudo chown root:root /usr/local/share/pwnagotchi/custom-plugins/pwnhub.py; sudo chmod 644 /usr/local/share/pwnagotchi/custom-plugins/pwnhub.py"
```
2. Add config snippet to `/etc/pwnagotchi/config.toml`:
```toml
[pwnhub]
enabled = true
hub_url = "http://10.67.0.1:5000"
auth_token = "REPLACE_WITH_TOKEN"
push_handshakes = true
upload_method = "http"
handshake_path = "/root/handshakes"
```
3. Reboot the device or restart pwnagotchi service.
4. Approve device in PwnHub web UI (if auto-approve disabled).

---

## Roadmap & Future Ideas
- Grafana dashboard for historical telemetry (influxdb + grafana).
- Plugin manager UI to push community plugins to devices.
- Per-device scheduled tasks and flexible retention policies.
- Multi-hub federation (syncing hubs across locations) via secure replication.
- OTA plugin update mechanism for Pwnagotchi devices (signed plugin packages).

---

## Appendix: Useful Commands

```bash
# Start compose
cd deploy && docker-compose up -d --build

# Check logs
docker-compose logs -f pwnhub-api

# Run API directly for dev
cd pwnhub-api && uvicorn app.main:app --reload --host 0.0.0.0 --port 5000

# Create DB (example)
python3 pwnhub-api/app/database_init.py

# Add plugin to device
scp agent/pwnhub.py pi@pwnagotchi:/tmp/ && ssh pi@pwnagotchi 'sudo mv /tmp/pwnhub.py /usr/local/share/pwnagotchi/custom-plugins/'
```

---

## Contacts & Ownership
- Repo: `https://github.com/Zmk55/PwnHub`
- Maintainer: Tim (primary developer)
- Contributors: Add via PRs and issues on GitHub

---

*Keep this file updated as the single source of truth for PwnHub. Append decisions, configuration changes, and operational notes here for future reference.*
