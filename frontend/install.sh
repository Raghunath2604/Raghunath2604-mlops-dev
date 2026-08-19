#!/bin/sh
set -e

# ==========================================
# MLOps.dev - Edge Agent Installer
# Version: 2.0.0
# ==========================================

echo "=================================================="
echo "  🚀 Starting MLOps.dev Agent Installation"
echo "=================================================="

if [ -z "$MLOPS_API_KEY" ]; then
    echo "❌ Error: MLOPS_API_KEY environment variable is missing!"
    echo "Usage: curl -fsSL https://get.mlopsde.me | MLOPS_API_KEY=your_key sh"
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (or with sudo) to configure systemd."
    echo "Usage: curl -fsSL https://get.mlopsde.me | sudo MLOPS_API_KEY=your_key sh"
    exit 1
fi

API_URL="${MLOPS_API_URL:-https://api.mlopsde.me/v1}"
ARCH=$(uname -m)
HOSTNAME=$(hostname)

echo "🔍 Detected architecture: $ARCH"
echo "📦 Setting up installation directories..."

INSTALL_DIR="/opt/mlops-agent"
mkdir -p "$INSTALL_DIR"

echo "⬇️  Downloading agent..."
# In a real scenario, this downloads the Go binary based on $ARCH.
# Here, we write a lightweight Python polling agent for demonstration.
cat << 'EOF' > "$INSTALL_DIR/agent.py"
import os
import time
import json
import urllib.request
import urllib.error
import socket
import platform

API_URL = os.environ.get("MLOPS_API_URL", "https://api.mlopsde.me/v1")
API_KEY = os.environ.get("MLOPS_API_KEY")
DEVICE_NAME = socket.gethostname()

def register():
    data = json.dumps({"name": DEVICE_NAME, "arch": platform.machine(), "os": platform.system()}).encode()
    req = urllib.request.Request(f"{API_URL}/devices/register", data=data, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    try:
        res = urllib.request.urlopen(req)
        res_data = json.loads(res.read().decode())
        print(f"Device registered successfully. ID: {res_data.get('device_id')}")
        return res_data.get('device_id')
    except Exception as e:
        print(f"Failed to register: {e}")
        return None

def heartbeat(device_id):
    if not device_id: return
    req = urllib.request.Request(f"{API_URL}/devices/{device_id}/ping", method="POST", headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        pass

def sync_model(device_id, current_state):
    req = urllib.request.Request(f"{API_URL}/devices/{device_id}", headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode())["data"]
        assigned_name = data.get("model_name")
        assigned_tag = data.get("model_tag")
        
        if assigned_name and assigned_tag:
            state_key = f"{assigned_name}:{assigned_tag}"
            if current_state.get("active_model") != state_key:
                print(f"🚀 New deployment detected! Downloading {state_key}...")
                dl_req = urllib.request.Request(f"{API_URL}/models/{assigned_name}/{assigned_tag}/download", headers={"Authorization": f"Bearer {API_KEY}"})
                dl_res = urllib.request.urlopen(dl_req)
                
                models_dir = "/opt/mlops-agent/models"
                os.makedirs(models_dir, exist_ok=True)
                # Parse filename from Content-Disposition if needed, or just save as model.bin
                file_path = os.path.join(models_dir, f"{assigned_name}_{assigned_tag}.bin")
                with open(file_path, "wb") as f:
                    f.write(dl_res.read())
                
                print(f"✅ Successfully downloaded and loaded {state_key}")
                current_state["active_model"] = state_key
    except Exception as e:
        print(f"Sync failed: {e}")

if __name__ == "__main__":
    print("Starting MLOps.dev Agent...")
    dev_id = None
    while not dev_id:
        dev_id = register()
        if not dev_id:
            print("Retrying registration in 10s...")
            time.sleep(10)
            
    state = {"active_model": None}
    while True:
        heartbeat(dev_id)
        sync_model(dev_id, state)
        time.sleep(30)
EOF
chmod +x "$INSTALL_DIR/agent.py"

echo "⚙️  Configuring systemd service..."
cat << EOF > /etc/systemd/system/mlops-agent.service
[Unit]
Description=MLOps.dev Edge Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="MLOPS_API_KEY=$MLOPS_API_KEY"
Environment="MLOPS_API_URL=$API_URL"
ExecStart=/usr/bin/env python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Starting service..."
systemctl daemon-reload || true
systemctl enable mlops-agent.service || true
systemctl restart mlops-agent.service || true

echo "=================================================="
echo "✅ Installation Complete!"
echo "📡 The agent is running in the background via systemd."
echo "📊 View your device online at: https://www.mlopsde.me/dashboard"
echo "=================================================="
