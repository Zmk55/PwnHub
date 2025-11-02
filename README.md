# PwnHub

PwnHub is a management and monitoring server for multiple Pwnagotchi devices. It runs on a Raspberry Pi 5 (or other Linux host) and provides a local web interface for device discovery and management via USB or network, automated handshake ingestion and backup, SSH/SFTP/web terminal access per device, configuration syncing, and persistent tracking of devices by hardware serial.

## Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Zmk55/PwnHub.git
   cd PwnHub
   ```

2. **Start with Docker Compose:**
   ```bash
   cd deploy
   cp env.example .env  # Optional: edit .env if needed
   docker-compose up -d --build
   ```

3. **Access the web interface:**
   - Web UI: http://localhost:8080
   - API Docs: http://localhost:5000/docs

## Development Quick Test

For local API development without Docker:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pwnhub-api/requirements.txt
uvicorn pwnhub-api.app.main:app --reload --host 0.0.0.0 --port 5000
```

Then open http://localhost:5000/docs for the API documentation.

For more information, see [PwnHub_GUIDE.md](PwnHub_GUIDE.md) and [docs/INSTALL.md](docs/INSTALL.md).
