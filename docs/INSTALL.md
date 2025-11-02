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

## Stopping Services

To stop all services:

```bash
docker-compose down
```

To stop and remove volumes (deletes all data):

```bash
docker-compose down -v
```

## Data Persistence

All data is stored in `./data/` directory in the deploy folder. This includes:
- SQLite database (`pwnhub.db`)
- Handshake files (per device)
- Device backups

Make sure to backup this directory regularly.

## Troubleshooting

Check logs:

```bash
docker-compose logs -f pwnhub-api
docker-compose logs -f pwnhub-web
```

Check if ports are already in use:

```bash
netstat -tulpn | grep -E '5000|8080'
```

