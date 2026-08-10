"""
mlops-dev — Python SDK for MLOps.dev
pip install mlops-dev

Quick start:
    import mlops_dev as mlops

    client = mlops.Client(api_key="your-key")

    # Push model
    v = client.models.push("./model.onnx", name="defect-detector", tag="v1.0")

    # Deploy to device
    dep = client.deploy("defect-detector:v1.0", target="jetson-prod-01")
    dep.wait()   # blocks until done or fails

    # Staged canary rollout
    dep = client.deploy(
        "defect-detector:v2.0", target="all",
        stages=[
            {"hw_class": "jetson_orin", "count": 1},
            {"hw_class": "jetson_orin", "pct": 100},
            {"hw_class": "all",         "pct": 100},
        ],
        health_gate={"accuracy_delta": -0.03},
    )

    # Fleet status
    for d in client.devices.list():
        print(f"{d.id}  {d.status.value}  drift={d.drift_score:.3f}")

    # Drift
    report = client.drift.report()
    print(f"{report.drifting}/{report.total_devices} drifting")

    # Rollback
    client.rollback(device_id="jetson-prod-01", to="defect-detector:v1.0")

Links:
    PyPI:    https://pypi.org/project/mlops-dev
    GitHub:  https://github.com/Raghunath2604/Raghunath2604-mlops-dev
    Docs:    https://docs.mlops.dev/api
    Discord: https://discord.gg/Tb47N9NaPk

Author: Raghunathareddy GR <hello@mlops.dev>
"""

__version__ = "0.7.0"
__author__  = "Raghunathareddy GR"
__email__   = "hello@mlops.dev"
__license__ = "Apache-2.0"

from .client import Client
from .models import Model, ModelVersion
from .devices import Device, DeviceStatus
from .deployments import Deployment, DeploymentStage
from .drift import DriftReport, DriftAlert
from .exceptions import (
    MLOpsError, AuthenticationError,
    DeviceNotFoundError, ModelNotFoundError,
    DeploymentError, RateLimitError, NetworkError,
)

__all__ = [
    "Client",
    "Model", "ModelVersion",
    "Device", "DeviceStatus",
    "Deployment", "DeploymentStage",
    "DriftReport", "DriftAlert",
    "MLOpsError", "AuthenticationError",
    "DeviceNotFoundError", "ModelNotFoundError",
    "DeploymentError", "RateLimitError", "NetworkError",
]
