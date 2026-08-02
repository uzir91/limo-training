#!/usr/bin/env bash

set -euo pipefail

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
    echo "Error: NVM was not found at $NVM_DIR/nvm.sh" >&2
    exit 1
fi

# Load NVM and select Node.js 24.
source "$NVM_DIR/nvm.sh"
nvm use 24 >/dev/null

USER_DIR="${NODE_RED_USER_DIR:-$HOME/.node-red}"
PORT="${NODE_RED_PORT:-1880}"

echo "Starting Node-RED"
echo "  User directory: $USER_DIR"
echo "  Port: $PORT"

exec node-red \
    --userDir "$USER_DIR" \
    --port "$PORT" \
    "$@"
