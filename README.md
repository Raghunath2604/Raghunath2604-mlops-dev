<div align="center">
  <img src="https://raw.githubusercontent.com/Raghunath2604/Raghunath2604-mlops-dev/main/brand/logo-128-dark.svg" width="128" alt="MLOps.dev Logo">
  <h1>MLOps.dev</h1>
  <p><strong>Deploy ML models to edge devices without SSH scripts. Offline-first, drift-aware.</strong></p>

  <a href="https://pypi.org/project/mlops-dev/"><img src="https://img.shields.io/pypi/v/mlops-dev.svg?style=flat-square" alt="PyPI version"></a>
  <a href="https://www.mlopsde.me"><img src="https://img.shields.io/badge/Website-mlopsde.me-blue.svg?style=flat-square" alt="Website"></a>
  <a href="https://discord.gg/Tb47N9NaPk"><img src="https://img.shields.io/discord/1337?color=7289da&label=Discord&logo=discord&style=flat-square" alt="Discord"></a>
  <a href="https://github.com/Raghunath2604/Raghunath2604-mlops-dev/blob/main/sdk/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License"></a>
</div>

<br />

**MLOps.dev** is a powerful Python SDK and CLI designed for managing fleet-wide machine learning model deployments to edge devices. Stop writing brittle bash scripts to copy models to Jetson Nanos and Raspberry Pis—use MLOps.dev to deploy, monitor drift, and rollback instantly.

<div align="center">
  <img src="https://raw.githubusercontent.com/Raghunath2604/Raghunath2604-mlops-dev/main/brand/og-image.png" alt="MLOps.dev Dashboard" width="800">
</div>

## ✨ Features

- 🚀 **One-Command Deploys:** Ship models directly to thousands of edge devices with a single CLI command.
- 📡 **Offline-First Resilience:** Devices continue running and buffering telemetry even when disconnected.
- 📊 **Drift Detection:** Built-in statistical drift monitoring alerts you when real-world data drifts from training data.
- ⏪ **Instant Rollbacks:** Bad deployment? Rollback a specific fleet to the previous stable model instantly.
- 🐍 **Native Python SDK:** Manage your fleets programmatically directly from your Jupyter Notebooks or CI/CD pipelines.

---

## 📦 Installation

Install the CLI and SDK via pip:

```bash
pip install mlops-dev
```

---

## ⚡ Quickstart

### Using the CLI

Manage your edge devices directly from the terminal:

```bash
# Check platform status
mlops status

# List all active edge devices in your fleet
mlops devices list

# Deploy a new model to a specific device group
mlops deploy defect-detector:v1.0 --target jetson-prod-01

# Run a data drift analysis report
mlops drift report

# Oh no, precision dropped! Rollback instantly:
mlops rollback --to defect-detector:v0.9
```

### Using the Python SDK

Integrate fleet management directly into your training pipelines:

```python
import os
from mlops_dev.client import MLOpsClient

# 1. Initialize the client
# (Ensure MLOps_API_KEY is set in your environment)
client = MLOpsClient()

# 2. Check platform status
status = client.get_status()
print(f"Platform status: {status['status']} ({status['version']})")

# 3. List active devices
devices = client.devices.list()
print(f"Found {len(devices)} edge devices online.")

# 4. Deploy a model programmatically
deployment = client.deployments.create(
    model_name="defect-detector",
    tag="v1.0",
    target="jetson-prod-01"
)
print("Deployment initiated:", deployment)
```

---

## 🛠️ Local Development

If you'd like to run the API server locally for development or testing:

1. Clone the repository:
   ```bash
   git clone https://github.com/Raghunath2604/Raghunath2604-mlops-dev.git
   cd Raghunath2604-mlops-dev
   ```

2. Run the mock local API server:
   ```bash
   cd sdk
   pip install flask flask-cors requests resend gunicorn
   python server/api.py
   ```

3. Run the demo script (in a new terminal):
   ```bash
   export MLOPS_API_KEY=demo
   export MLOPS_API_URL=http://localhost:8000/v1
   python demo.py
   ```

---

## 🔗 Links & Community

- **Website:** [www.mlopsde.me](https://www.mlopsde.me)
- **Waitlist:** [Join the Early Access Waitlist](https://www.mlopsde.me/#wl)
- **Public Roadmap:** [roadmap.mlopsde.me](https://roadmap.mlopsde.me)
- **Discord Community:** [Join Discord](https://discord.gg/Tb47N9NaPk)

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

<div align="center">
  <br/>
  <i>Built for the edge by Raghunathareddy GR</i>
</div>

## 🌐 Running the Edge Agent
To run the Edge Agent on your IoT devices (Raspberry Pi, Jetson Nano, Coral), use the `MLOpsAgent` class:

```python
from mlops_dev.agent import MLOpsAgent

# Initialize the agent
agent = MLOpsAgent(
    api_key="your_api_key_here",
    device_name="jetson-prod-01",
    hw_class="jetson_orin"
)

# Start background sync & heartbeats
agent.start()

# Log inferences (calculates drift on the edge!)
agent.log_inference(input_data={"image": "camera1"}, output_data={"confidence": 0.85})
```
