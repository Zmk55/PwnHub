#!/bin/bash
# Provision SSH key to device using ssh-copy-id
# Usage: ./provision-ssh-key.sh <device_ip> [ssh_username]
# Security: Validates inputs, uses explicit paths, no shell expansion

set -e

DEVICE_IP="${1}"
SSH_USERNAME="${2:-pi}"
SSH_PUB_KEY="/srv/pwnhub/keys/pwnhub_id_ed25519.pub"

# Use local path if Docker path doesn't exist
if [ ! -f "$SSH_PUB_KEY" ]; then
    SSH_PUB_KEY="./storage/keys/pwnhub_id_ed25519.pub"
fi

# Validate inputs
if [ -z "$DEVICE_IP" ]; then
    echo "Error: Device IP required"
    echo "Usage: $0 <device_ip> [ssh_username]"
    exit 1
fi

# Validate IP format (basic regex check)
if ! echo "$DEVICE_IP" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
    echo "Error: Invalid IP address format: $DEVICE_IP"
    exit 1
fi

# Validate username (alphanumeric only)
if ! echo "$SSH_USERNAME" | grep -qE '^[a-zA-Z0-9_-]+$'; then
    echo "Error: Invalid username format: $SSH_USERNAME"
    exit 1
fi

# Validate SSH public key exists
if [ ! -f "$SSH_PUB_KEY" ]; then
    echo "Error: SSH public key not found at $SSH_PUB_KEY"
    exit 1
fi

# Execute ssh-copy-id with timeout
# Use explicit paths for security (no PATH dependencies)
SSH_COPY_ID=$(which ssh-copy-id 2>/dev/null || echo "ssh-copy-id")

if [ -z "$SSH_COPY_ID" ] || [ "$SSH_COPY_ID" = "ssh-copy-id" ] && ! command -v ssh-copy-id >/dev/null 2>&1; then
    echo "Error: ssh-copy-id command not found"
    exit 1
fi

echo "Provisioning SSH key to ${SSH_USERNAME}@${DEVICE_IP}..."

# Execute ssh-copy-id with timeout
# -i: specify identity file (public key)
# -o StrictHostKeyChecking=no: don't prompt for host key confirmation
# -o UserKnownHostsFile=/dev/null: don't save host key
timeout 30 "$SSH_COPY_ID" \
    -i "$SSH_PUB_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "${SSH_USERNAME}@${DEVICE_IP}" 2>&1

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "SSH key provisioned successfully"
    exit 0
elif [ $exit_code -eq 124 ]; then
    echo "Error: ssh-copy-id timed out"
    exit 1
else
    echo "Error: ssh-copy-id failed with exit code $exit_code"
    exit $exit_code
fi

