"""
mlops_dev.devices — query and manage edge devices in your fleet.

Usage:
    # List all devices
    for device in client.devices.list():
        print(f"{device.id:20}  {device.status.value:8}  model={device.model_ref}  drift={device.drift_score:.3f}")

    # Filter — only drifting Jetson Orins
    drifting = client.devices.list(status="drift", hw_class="jetson_orin")

    # Get one device
    d = client.devices.get("jetson-prod-01")
    print(f"  RAM used:     {d.ram_mb}MB")
    print(f"  Latency:      {d.latency_ms}ms")
    print(f"  Drift score:  {d.drift_score:.3f}  ({'OK' if d.drift_score < 0.4 else 'WARNING'})")
    print(f"  Agent:        v{d.agent_version}")
    print(f"  Last seen:    {d.last_seen}")

    # Stream device logs
    for entry in client.devices.logs("jetson-prod-01", limit=50):
        print(f"  [{entry['level']}] {entry['ts']}  {entry['msg']}")

    # Deregister a device (removes from fleet, does not uninstall the agent)
    client.devices.deregister("jetson-retired-04")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any


class DeviceStatus(str, Enum):
    """Current operational status of an edge device."""
    ONLINE  = "online"    # heartbeat received within last 60s, model loaded
    OFFLINE = "offline"   # no heartbeat for >60s
    DRIFT   = "drift"     # KL divergence above alert threshold (0.7)
    WARNING = "warning"   # KL divergence above warn threshold (0.4)
    ERROR   = "error"     # agent error, model load failure, or health gate failed
    UNKNOWN = "unknown"   # never registered a heartbeat


@dataclass
class Device:
    """
    A single edge device registered in your MLOps.dev fleet.

    Attributes:
        id:            Unique device identifier (set on first agent registration)
        name:          Human-readable name (set via dashboard or mlops devices rename)
        status:        DeviceStatus enum
        hw_class:      Hardware class e.g. "jetson_orin" | "jetson_nano" | "rpi5" | "x86_64"
        arch:          CPU architecture: "arm64" | "armv7" | "amd64"
        model_name:    Name of the currently active model
        model_tag:     Tag of the currently active model version
        model_format:  Format of the active model: "onnx" | "tflite" | "tensorrt"
        drift_score:   KL divergence score (0.0 = no drift, >0.7 = alert)
        latency_ms:    Average inference latency in milliseconds
        last_seen:     ISO 8601 timestamp of most recent heartbeat
        agent_version: Version of the mlops-agent running on the device
        os:            OS string e.g. "linux/arm64"
        ram_mb:        Current RAM usage of the agent process in MB
        cpu_pct:       CPU % used by the agent (0-100)
        temp_c:        Device temperature in Celsius (-1 if unavailable)
        uptime_s:      Agent uptime in seconds
        metadata:      Dict of custom key-value pairs set at registration
    """
    id:            str
    name:          str
    status:        DeviceStatus
    hw_class:      str
    arch:          str
    model_name:    str
    model_tag:     str
    model_format:  str
    drift_score:   float
    latency_ms:    float
    last_seen:     str
    agent_version: str
    os:            str
    ram_mb:        int
    cpu_pct:       float = 0.0
    temp_c:        float = -1.0
    uptime_s:      int   = 0
    metadata:      Dict  = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict) -> "Device":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            status=DeviceStatus(d.get("status", "unknown")),
            hw_class=d.get("hw_class", ""),
            arch=d.get("arch", "arm64"),
            model_name=d.get("model_name", ""),
            model_tag=d.get("model_tag", ""),
            model_format=d.get("model_format", "onnx"),
            drift_score=float(d.get("drift_score", 0.0)),
            latency_ms=float(d.get("latency_ms", 0.0)),
            last_seen=d.get("last_seen", ""),
            agent_version=d.get("agent_version", ""),
            os=d.get("os", "linux"),
            ram_mb=int(d.get("ram_mb", 0)),
            cpu_pct=float(d.get("cpu_pct", 0.0)),
            temp_c=float(d.get("temp_c", -1.0)),
            uptime_s=int(d.get("uptime_s", 0)),
            metadata=d.get("metadata", {}),
        )

    @property
    def is_online(self) -> bool:
        return self.status == DeviceStatus.ONLINE

    @property
    def has_drift(self) -> bool:
        return self.status in (DeviceStatus.DRIFT, DeviceStatus.WARNING)

    @property
    def model_ref(self) -> str:
        """Active model reference e.g. defect-detector:v1.0"""
        if not self.model_name:
            return "none"
        return f"{self.model_name}:{self.model_tag}"

    @property
    def drift_level(self) -> str:
        """Human-readable drift level: ok | warning | alert"""
        if self.drift_score >= 0.7:
            return "alert"
        if self.drift_score >= 0.4:
            return "warning"
        return "ok"

    def __repr__(self) -> str:
        return (f"<Device {self.id!r}  {self.status.value}  "
                f"model={self.model_ref}  drift={self.drift_score:.3f}  "
                f"latency={self.latency_ms:.1f}ms>")


class DevicesAPI:
    """
    Query and manage edge devices in your fleet.
    Access via: client.devices
    """

    def __init__(self, http):
        self._http = http

    def list(
        self,
        status:   Optional[str] = None,
        hw_class: Optional[str] = None,
        model:    Optional[str] = None,
        limit:    int = 100,
        offset:   int = 0,
    ) -> List[Device]:
        """
        List all registered devices.

        Args:
            status:   Filter by status — "online" | "offline" | "drift" |
                        "warning" | "error"
            hw_class: Filter by hardware class — "jetson_orin" | "jetson_nano" |
                        "rpi5" | "rpi4" | "coral" | "x86_64" | ...
            model:    Filter by active model name e.g. "defect-detector"
            limit:    Page size (default 100, max 500)
            offset:   Pagination offset for large fleets

        Returns:
            List[Device]

        Examples:
            # All online Jetson Orins
            orins = client.devices.list(status="online", hw_class="jetson_orin")

            # All drifting devices across any hardware
            drifting = client.devices.list(status="drift")
            for d in drifting:
                print(f"  {d.id}  KL={d.drift_score:.3f}  level={d.drift_level}")

            # Paginate a large fleet
            page = 0
            while True:
                batch = client.devices.list(limit=100, offset=page * 100)
                if not batch:
                    break
                for d in batch:
                    process(d)
                page += 1
        """
        params: Dict = {"limit": limit, "offset": offset}
        if status:   params["status"]   = status
        if hw_class: params["hw_class"] = hw_class
        if model:    params["model"]    = model
        data = self._http.request("GET", "/devices", params=params)
        return [Device.from_dict(d) for d in data.get("data", [])]

    def get(self, device_id: str) -> Device:
        """
        Get a single device by ID.

        Args:
            device_id: Device identifier set at agent registration

        Returns:
            Device

        Raises:
            DeviceNotFoundError: if no device with this ID exists

        Example:
            d = client.devices.get("jetson-prod-01")
            print(f"Model:   {d.model_ref}")
            print(f"Drift:   {d.drift_score:.3f} ({d.drift_level})")
            print(f"Latency: {d.latency_ms:.1f}ms")
            print(f"RAM:     {d.ram_mb}MB")
            print(f"Temp:    {d.temp_c:.1f}°C")
        """
        from .exceptions import DeviceNotFoundError
        try:
            data = self._http.request("GET", f"/devices/{device_id}")
        except Exception as e:
            if "not found" in str(e).lower():
                raise DeviceNotFoundError(f"Device not found: {device_id}")
            raise
        return Device.from_dict(data["data"])

    def logs(
        self,
        device_id: str,
        limit:     int = 100,
        level:     Optional[str] = None,
        since:     Optional[str] = None,
    ) -> List[Dict]:
        """
        Get recent event log entries for a device.

        Args:
            device_id: Device identifier
            limit:     Number of log entries (default 100, max 1000)
            level:     Filter by level — "info" | "warn" | "error"
            since:     ISO 8601 timestamp — only entries after this time

        Returns:
            List of dicts with keys: ts, level, event, msg, data

        Example:
            logs = client.devices.logs("jetson-prod-01", limit=50, level="error")
            for entry in logs:
                print(f"[{entry['level'].upper()}] {entry['ts']}  {entry['msg']}")
        """
        params: Dict = {"limit": limit}
        if level: params["level"] = level
        if since: params["since"] = since
        data = self._http.request("GET", f"/devices/{device_id}/logs", params=params)
        return data.get("data", [])

    def config(self, device_id: str, **kwargs) -> Dict:
        """
        Update agent configuration for a device.

        Supported kwargs:
            heartbeat_interval: int (seconds, default 30)
            sync_interval:      int (seconds, default 30)
            drift_enabled:      bool
            drift_warn:         float (KL threshold, default 0.4)
            drift_alert:        float (KL threshold, default 0.7)
            telemetry_buffer_mb: int (default 500)
            log_level:          str (debug | info | warn | error)

        Example:
            # Tighten drift thresholds for a sensitive deployment
            client.devices.config(
                "jetson-prod-01",
                drift_warn=0.25,
                drift_alert=0.5,
                heartbeat_interval=15,
            )
        """
        return self._http.request("PATCH", f"/devices/{device_id}/config", json=kwargs)

    def deregister(self, device_id: str) -> bool:
        """
        Remove a device from the fleet.

        This does NOT uninstall the agent from the device — it removes the
        device from your fleet dashboard and stops tracking it. Run
        `mlops deregister` on the device itself to fully remove the agent.

        Args:
            device_id: Device identifier

        Returns:
            True on success

        Example:
            client.devices.deregister("jetson-retired-04")
        """
        self._http.request("DELETE", f"/devices/{device_id}")
        return True
