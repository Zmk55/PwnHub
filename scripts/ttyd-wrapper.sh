#!/bin/bash
# Wrapper script for ttyd that reads serial from query parameter or environment
# This script is called by ttyd for each connection

# Try to get serial from environment variable (set by docker-compose or nginx)
SERIAL="${SERIAL}"

# If not in environment, try to get from ttyd's URL query parameter
# Note: ttyd doesn't directly pass URL params, so we use environment variable
# The web UI should set this via nginx proxy configuration

if [ -z "$SERIAL" ]; then
    echo "Error: Device serial not provided"
    echo "Please provide SERIAL environment variable or URL parameter"
    exit 1
fi

# Call the connect script with the serial
exec /usr/local/bin/connect-to-device.sh "$SERIAL"

