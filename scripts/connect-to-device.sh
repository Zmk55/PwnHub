#!/bin/bash
# Connect to a Pwnagotchi device via SSH
# Usage: ./connect-to-device.sh <device_serial>

set -e

# Get serial from environment variable (set by docker-compose) or argument
SERIAL="${SERIAL:-${1}}"
API_URL="${PWNHUB_API_URL:-http://pwnhub-api:5000}"
SSH_KEY="/srv/pwnhub/keys/pwnhub_id_ed25519"
SSH_USER="pi"

if [ -z "$SERIAL" ]; then
    echo "Error: Device serial required"
    echo "Usage: $0 <device_serial>"
    echo "Or set SERIAL environment variable"
    exit 1
fi

# Query API for device information
echo "Looking up device $SERIAL..."
DEVICE_INFO=$(curl -s "${API_URL}/api/devices" 2>&1)

if [ $? -ne 0 ]; then
    echo "Error: Failed to connect to API at ${API_URL}"
    exit 1
fi

# Extract device IP from JSON response
# Try to use jq if available, otherwise use basic parsing
if command -v jq >/dev/null 2>&1; then
    DEVICE_IP=$(echo "$DEVICE_INFO" | jq -r ".[] | select(.serial == \"${SERIAL}\") | .last_ip")
else
    # Basic parsing: look for serial match and extract last_ip
    DEVICE_IP=$(echo "$DEVICE_INFO" | grep -o "\"serial\":\"${SERIAL}\"[^}]*" | grep -o "\"last_ip\":\"[^\"]*" | cut -d'"' -f4)
fi

if [ -z "$DEVICE_IP" ] || [ "$DEVICE_IP" = "null" ]; then
    echo "Error: Device with serial ${SERIAL} not found or has no IP address"
    echo "Make sure the device has registered and sent a heartbeat."
    exit 1
fi

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at ${SSH_KEY}"
    echo "Please provision the SSH key first."
    exit 1
fi

# Set proper permissions on key
chmod 600 "$SSH_KEY" 2>/dev/null || true

echo "Connecting to device ${SERIAL} at ${DEVICE_IP}..."

# Execute SSH connection
exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "$SSH_KEY" "${SSH_USER}@${DEVICE_IP}"

