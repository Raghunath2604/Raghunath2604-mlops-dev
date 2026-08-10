# mlops-dev

Python SDK and CLI for [MLOps.dev](https://www.mlops.dev) — deploy, monitor, and manage ML models on edge devices at scale.

[![PyPI](https://img.shields.io/pypi/v/mlops-dev)](https://pypi.org/project/mlops-dev)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2)](https://discord.gg/Tb47N9NaPk)

## Install

```bash
pip install mlops-dev
```

## Authenticate

```bash
export MLOPS_API_KEY=mlops_live_xxxx
```

Get your API key at [mlops.dev/dashboard](https://www.mlops.dev/dashboard) → Settings.

## Quick start — Python

```python
import mlops_dev as mlops

client = mlops.Client()  # reads MLOPS_API_KEY from env

# Push a model
v = client.models.push("./model.onnx", name="defect-detector", tag="v1.0")
print(f"Pushed {v.name}:{v.tag}  {v.size_mb}MB  sha={v.sha256[:8]}...")

# Push TensorRT engine for Jetson Orin
v = client.models.push(
    "./model_orin_int8.engine",
    name="defect-detector",
    tag="v1.0",
    format="tensorrt",
    variant="jetson_orin",
    metadata={"accuracy": "0.942", "input_shape": "[1,3,224,224]"},
)

# Deploy to one device (blocks until done)
dep = client.deploy("defect-detector:v1.0", target="jetson-prod-01")
dep.wait()
print(dep.status)  # completed

# Staged canary rollout across a mixed fleet
dep = client.deploy(
    "defect-detector:v2.0",
    target="all",
    stages=[
        {"hw_class": "jetson_orin", "count": 1},    # 1 pilot device
        {"hw_class": "jetson_orin", "pct": 100},    # all Jetson Orins
        {"hw_class": "jetson_nano", "pct": 25},     # 25% of Nanos
        {"hw_class": "all",         "pct": 100},    # full fleet
    ],
    health_gate={
        "accuracy_delta": -0.03,   # halt if accuracy drops > 3%
        "latency_delta":  0.20,    # halt if latency rises > 20%
    },
    stage_interval="30m",
)

def log_stage(stage, status, dep):
    print(f"Stage {stage}/{dep.total_stages}: {status}")

dep.wait(poll_interval=10, on_stage=log_stage)

if dep.status == "failed":
    client.rollback(to="defect-detector:v1.0")

# Fleet status
for device in client.devices.list():
    print(f"{device.id:20}  {device.status.value:8}  drift={device.drift_score:.3f}")

# Drift monitoring
report = client.drift.report()
print(f"{report.drifting}/{report.total_devices} drifting  avg_kl={report.fleet_avg_kl:.3f}")

for alert in client.drift.alerts():
    print(f"  [{alert.severity}] {alert.device_id}  KL={alert.kl_score:.3f}  {alert.monitor}")

# Reset drift baseline after a planogram change
client.drift.reset_baseline("jetson-prod-01")

# Rollback
client.rollback(device_id="jetson-prod-01", to="defect-detector:v1.0")
client.rollback()  # entire fleet

# Audit log (for FDA/ISO compliance)
log = client.audit(device_id="jetson-prod-01", since="2025-01-01", format="csv")
```

## Quick start — CLI

```bash
# Fleet status
mlops status

# List all devices
mlops devices list
mlops devices list --status drift --hw-class jetson_orin

# Get one device
mlops devices get jetson-prod-01

# Device logs
mlops devices logs jetson-prod-01 --limit 50 --level error

# Push a model
mlops models push ./model.onnx --name defect-detector --tag v1.0
mlops models push ./model_orin_int8.engine --name defect-detector --tag v1.0 \
    --format tensorrt --variant jetson_orin

# Deploy
mlops deploy defect-detector:v1.0 --target jetson-prod-01
mlops deploy defect-detector:v2.0 --target all \
    --stage hw_class=jetson_orin,count=1 \
    --stage hw_class=jetson_orin,pct=100 \
    --stage hw_class=all,pct=100 \
    --health-gate accuracy_delta=-0.03 \
    --stage-interval 30m

# Rollback
mlops rollback --to defect-detector:v1.0
mlops rollback --device jetson-prod-01 --to defect-detector:v1.0

# Drift monitoring
mlops drift report
mlops drift alerts
mlops drift reset jetson-prod-01

# Audit log
mlops audit --device jetson-prod-01 --since 2025-01-01 --format csv -o audit.csv
```

## Model formats

| Format | Best for | Install on |
|--------|----------|------------|
| ONNX | All ARM devices | `pip install onnxruntime` |
| TFLite | CPU-only ARM, low-power | Built into agent |
| TensorRT | Jetson GPU (max throughput) | Requires CUDA + TRT |

> **Note:** TensorRT engines are device-specific. Always set `variant=` when pushing `.engine` files.
> Push one version per hardware class — the agent selects automatically.

## Enterprise / on-premise

```python
# Point SDK at your on-premise control plane
client = mlops.Client(
    api_key="your-key",
    base_url="https://mlops.yourcompany.internal/api/v1",
)
```

## Links

- Website: https://www.mlops.dev
- Docs: https://docs.mlops.dev/api
- GitHub: https://github.com/Raghunath2604/Raghunath2604-mlops-dev
- Discord: https://discord.gg/Tb47N9NaPk
- Roadmap: https://roadmap.mlops.dev
- PyPI: https://pypi.org/project/mlops-dev

## License

Apache 2.0 — see [LICENSE](LICENSE)

## Author

Raghunathareddy GR — CEO & Founder, MLOps.dev
hello@mlops.dev | Bengaluru, India
