"""
Basic SDK tests using mocked HTTP responses.

Run: pytest sdk/tests/ -v
"""
import pytest
import json

try:
    import responses
    HAS_RESPONSES = True
except ImportError:
    HAS_RESPONSES = False

skip_if_no_responses = pytest.mark.skipif(
    not HAS_RESPONSES,
    reason="pip install responses"
)

MOCK_DEVICE = {
    "id": "jetson-test-01",
    "name": "Test Device",
    "status": "online",
    "hw_class": "jetson_orin",
    "arch": "arm64",
    "model_name": "defect-detector",
    "model_tag": "v1.0",
    "model_format": "tensorrt",
    "drift_score": 0.12,
    "latency_ms": 3.8,
    "last_seen": "2025-07-15T10:00:00Z",
    "agent_version": "0.6.0",
    "os": "linux",
    "ram_mb": 14,
}

MOCK_MODEL_VERSION = {
    "id": "mv_001",
    "name": "defect-detector",
    "tag": "v1.0",
    "format": "onnx",
    "variant": "all",
    "size_bytes": 7_400_000,
    "sha256": "abc123def456" * 4,
    "created_at": "2025-07-01T00:00:00Z",
    "active_devices": 42,
}

MOCK_DEPLOYMENT = {
    "id": "dep_test_001",
    "model_name": "defect-detector",
    "model_tag": "v2.0",
    "status": "completed",
    "stage": 1,
    "total_stages": 1,
    "target": "jetson-test-01",
    "created_at": "2025-07-15T10:00:00Z",
    "stages": [],
    "health_gate": {},
}

MOCK_DRIFT = {
    "total_devices": 100,
    "healthy": 92,
    "warning": 5,
    "drifting": 3,
    "offline": 0,
    "fleet_avg_kl": 0.087,
    "worst_device_id": "jetson-floor-b-12",
    "worst_kl": 0.72,
    "alerts": [
        {
            "device_id": "jetson-floor-b-12",
            "device_name": "Floor B Camera 12",
            "kl_score": 0.72,
            "severity": "alert",
            "monitor": "input_distribution",
            "detected_at": "2025-07-15T09:00:00Z",
            "model_name": "defect-detector",
            "model_tag": "v2.0",
        }
    ],
}


def make_client():
    """Create a client pointing at the mock API."""
    from mlops_dev import Client
    return Client(
        api_key="test_key_xxx",
        base_url="https://api.mlops.dev/v1",
    )


# ── Unit tests (no HTTP) ──────────────────────────────────────────

def test_device_from_dict():
    from mlops_dev.devices import Device, DeviceStatus
    d = Device.from_dict(MOCK_DEVICE)
    assert d.id == "jetson-test-01"
    assert d.status == DeviceStatus.ONLINE
    assert d.is_online is True
    assert d.has_drift is False
    assert d.model_ref == "defect-detector:v1.0"
    assert d.drift_level == "ok"


def test_device_drift_levels():
    from mlops_dev.devices import Device
    d = Device.from_dict({**MOCK_DEVICE, "drift_score": 0.55, "status": "warning"})
    assert d.drift_level == "warning"
    assert d.has_drift is True

    d2 = Device.from_dict({**MOCK_DEVICE, "drift_score": 0.75, "status": "drift"})
    assert d2.drift_level == "alert"
    assert d2.has_drift is True


def test_model_version_from_dict():
    from mlops_dev.models import ModelVersion
    v = ModelVersion.from_dict(MOCK_MODEL_VERSION)
    assert v.name == "defect-detector"
    assert v.tag == "v1.0"
    assert v.size_mb == 7.4
    assert v.ref == "defect-detector:v1.0"


def test_drift_report_from_dict():
    from mlops_dev.drift import DriftReport
    r = DriftReport.from_dict(MOCK_DRIFT)
    assert r.total_devices == 100
    assert r.drifting == 3
    assert r.pct_healthy == 92.0
    assert len(r.alerts) == 1
    assert r.alerts[0].severity == "alert"


def test_deployment_is_done():
    from mlops_dev.deployments import Deployment
    d = Deployment.from_dict(MOCK_DEPLOYMENT)
    assert d.is_done is True
    assert d.model_ref == "defect-detector:v2.0"


def test_client_no_key_raises():
    import os
    from mlops_dev import Client, AuthenticationError
    old = os.environ.pop("MLOPS_API_KEY", None)
    try:
        with pytest.raises(AuthenticationError):
            Client(api_key="")
    finally:
        if old:
            os.environ["MLOPS_API_KEY"] = old


# ── Integration tests (with mocked HTTP) ─────────────────────────

@skip_if_no_responses
@responses.activate
def test_devices_list():
    responses.add(
        responses.GET,
        "https://api.mlops.dev/v1/devices",
        json={"data": [MOCK_DEVICE], "total": 1},
        status=200,
    )
    client = make_client()
    devices = client.devices.list()
    assert len(devices) == 1
    assert devices[0].id == "jetson-test-01"


@skip_if_no_responses
@responses.activate
def test_devices_get():
    responses.add(
        responses.GET,
        "https://api.mlops.dev/v1/devices/jetson-test-01",
        json={"data": MOCK_DEVICE},
        status=200,
    )
    client = make_client()
    d = client.devices.get("jetson-test-01")
    assert d.latency_ms == 3.8


@skip_if_no_responses
@responses.activate
def test_deploy():
    responses.add(
        responses.POST,
        "https://api.mlops.dev/v1/deployments",
        json={"data": MOCK_DEPLOYMENT},
        status=200,
    )
    client = make_client()
    dep = client.deploy("defect-detector:v2.0", target="jetson-test-01")
    assert dep.status == "completed"
    assert dep.is_done is True


@skip_if_no_responses
@responses.activate
def test_drift_report():
    responses.add(
        responses.GET,
        "https://api.mlops.dev/v1/drift",
        json={"data": MOCK_DRIFT},
        status=200,
    )
    client = make_client()
    r = client.drift.report()
    assert r.drifting == 3
    assert r.worst_kl == 0.72


@skip_if_no_responses
@responses.activate
def test_rollback():
    responses.add(
        responses.POST,
        "https://api.mlops.dev/v1/deployments/rollback",
        json={"status": "queued", "affected_devices": 42},
        status=200,
    )
    client = make_client()
    result = client.rollback(to="defect-detector:v1.0")
    assert result["affected_devices"] == 42


@skip_if_no_responses
@responses.activate
def test_health_ok():
    responses.add(
        responses.GET,
        "https://api.mlops.dev/v1/health",
        json={"status": "ok"},
        status=200,
    )
    client = make_client()
    assert client.health() is True
