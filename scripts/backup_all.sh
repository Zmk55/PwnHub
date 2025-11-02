#!/bin/bash
# Backup all hub data to a timestamped archive
# Usage: ./backup_all.sh [backup_directory]

# TODO: Implement backup functionality
# - Create timestamped tarball of /srv/pwnhub
# - Include database and handshake files
# - Rotate old backups if configured
# - Support external storage/NAS targets

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup: ${BACKUP_DIR}/pwnhub_backup_${TIMESTAMP}.tar.gz"
echo "TODO: Implement backup functionality"

