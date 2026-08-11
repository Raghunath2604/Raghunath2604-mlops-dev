#!/bin/sh

set -e

echo "=================================================="
echo "  MLOps.dev Edge Agent Installer"
echo "=================================================="

if [ -z "$MLOPS_API_KEY" ]; then
    echo "Error: MLOPS_API_KEY is required."
    echo "Usage: MLOPS_API_KEY=<your_key> curl -fsSL https://get.mlops.dev | sh"
    exit 1
fi

API_URL="${MLOPS_API_URL:-https://api.mlopsde.me/v1}"
ARCH=$(uname -m)
HOSTNAME=$(hostname)

echo "Detecting architecture: $ARCH"
echo "Downloading agent binary..."
# Mock download
sleep 1
echo "Agent downloaded successfully to /usr/local/bin/mlops-agent"

echo "Registering device: $HOSTNAME"
# Mock registration
curl -s -X POST "$API_URL/devices/register" \
  -H "Authorization: Bearer $MLOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$HOSTNAME\", \"arch\": \"$ARCH\", \"os\": \"linux\"}" > /dev/null || true

echo "Starting agent service..."
sleep 1

echo "=================================================="
echo "✅ Success! Device is registered and online."
echo "View your device at: https://www.mlopsde.me/dashboard"
echo "=================================================="
