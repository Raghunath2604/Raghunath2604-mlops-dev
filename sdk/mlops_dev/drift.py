"""
mlops_dev.drift — monitor statistical drift in your edge fleet.

Drift detection runs on each device using KL divergence on the input
distribution. The agent compares the current distribution against a baseline
captured at model activation time.

Thresholds (configurable per-device via client.devices.config()):
    KL < 0.4  →  ok (normal variation)
    KL 0.4–0.7 →  warning (investigate)
    KL > 0.7  →  alert (likely distribution shift, consider rollback)

Usage:
    # Fleet-wide summary
    report = client.drift.report()
    print(f"Fleet: {report.drifting} drifting / {report.total_devices} total")
    print(f"Avg KL: {report.fleet_avg_kl:.3f}")
    print(f"Worst:  {report.worst_device_id}  KL={report.worst_kl:.3f}")

    # Active alerts
    for alert in client.drift.alerts():
        print(f"  [{alert.severity.upper()}] {alert.device_id}  KL={alert.kl_score:.3f}  since={alert.detected_at}")

    # Per-device history
    history = client.drift.device_history("jetson-prod-01")
    for point in history["data"]:
        print(f"  {point['ts']}  kl={point['kl_score']:.3f}")

    # Reset baseline after a planogram change or product line switch
    client.drift.reset_baseline("jetson-prod-01")
    print("Baseline reset — drift monitoring will recalibrate over next 200 inferences")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class DriftAlert:
    """
    A drift alert — fired when KL divergence exceeds a threshold on a device.

    Attributes:
        device_id:   Device that triggered the alert
        device_name: Human-readable device name
        kl_score:    KL divergence value that triggered the alert
        severity:    "warning" (KL 0.4–0.7) or "alert" (KL > 0.7)
        monitor:     Which distribution is drifting:
                       "input_distribution" | "output_confidence"
        detected_at: ISO 8601 timestamp when alert was first triggered
        resolved_at: ISO 8601 timestamp when alert resolved (None if still active)
        model_name:  Model that was active when drift was detected
        model_tag:   Model version that was active
    """
    device_id:   str
    device_name: str
    kl_score:    float
    severity:    str
    monitor:     str
    detected_at: str
    model_name:  str = ""
    model_tag:   str = ""
    resolved_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict) -> "DriftAlert":
        return cls(
            device_id=d.get("device_id", ""),
            device_name=d.get("device_name", ""),
            kl_score=float(d.get("kl_score", 0.0)),
            severity=d.get("severity", "warning"),
            monitor=d.get("monitor", "input_distribution"),
            detected_at=d.get("detected_at", ""),
            model_name=d.get("model_name", ""),
            model_tag=d.get("model_tag", ""),
            resolved_at=d.get("resolved_at"),
        )

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None

    @property
    def model_ref(self) -> str:
        if not self.model_name:
            return "unknown"
        return f"{self.model_name}:{self.model_tag}"

    def __repr__(self) -> str:
        state = "active" if self.is_active else "resolved"
        return (f"<DriftAlert [{self.severity}] {self.device_id}  "
                f"KL={self.kl_score:.3f}  monitor={self.monitor}  {state}>")


@dataclass
class DriftReport:
    """
    Fleet-wide drift summary.

    Attributes:
        total_devices:   Total devices in fleet
        healthy:         Devices with KL < 0.4
        warning:         Devices with 0.4 ≤ KL < 0.7
        drifting:        Devices with KL ≥ 0.7 (alert level)
        offline:         Devices not currently reachable
        fleet_avg_kl:    Average KL divergence across online devices
        worst_device_id: ID of the device with the highest KL score
        worst_kl:        KL score of the worst device
        alerts:          List of active DriftAlert objects
    """
    total_devices:   int
    healthy:         int
    warning:         int
    drifting:        int
    offline:         int
    fleet_avg_kl:    float
    worst_device_id: str
    worst_kl:        float
    alerts:          List[DriftAlert] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict) -> "DriftReport":
        alerts = [DriftAlert.from_dict(a) for a in d.get("alerts", [])]
        return cls(
            total_devices=int(d.get("total_devices", 0)),
            healthy=int(d.get("healthy", 0)),
            warning=int(d.get("warning", 0)),
            drifting=int(d.get("drifting", 0)),
            offline=int(d.get("offline", 0)),
            fleet_avg_kl=float(d.get("fleet_avg_kl", 0.0)),
            worst_device_id=d.get("worst_device_id", ""),
            worst_kl=float(d.get("worst_kl", 0.0)),
            alerts=alerts,
        )

    @property
    def pct_healthy(self) -> float:
        if self.total_devices == 0:
            return 0.0
        return round(self.healthy / self.total_devices * 100, 1)

    def __repr__(self) -> str:
        return (f"<DriftReport  "
                f"healthy={self.healthy}  warning={self.warning}  "
                f"drifting={self.drifting}  offline={self.offline}  "
                f"total={self.total_devices}  "
                f"avg_kl={self.fleet_avg_kl:.3f}  "
                f"worst_kl={self.worst_kl:.3f}>")


class DriftAPI:
    """
    Monitor and manage statistical drift across your edge fleet.
    Access via: client.drift
    """

    def __init__(self, http):
        self._http = http

    def report(self) -> DriftReport:
        """
        Get a fleet-wide drift summary.

        Returns:
            DriftReport with counts, averages, and active alerts

        Example:
            report = client.drift.report()

            print(f"Fleet health:  {report.pct_healthy}% healthy")
            print(f"Average KL:    {report.fleet_avg_kl:.3f}")
            print(f"Worst device:  {report.worst_device_id}  KL={report.worst_kl:.3f}")
            print()
            print(f"Breakdown:")
            print(f"  Healthy:   {report.healthy}")
            print(f"  Warning:   {report.warning}")
            print(f"  Drifting:  {report.drifting}")
            print(f"  Offline:   {report.offline}")

            if report.drifting > 0:
                print(f"\nActive alerts ({len(report.alerts)}):")
                for alert in report.alerts:
                    print(f"  [{alert.severity}] {alert.device_id}  KL={alert.kl_score:.3f}")
        """
        data = self._http.request("GET", "/drift")
        return DriftReport.from_dict(data["data"])

    def alerts(self, resolved: bool = False) -> List[DriftAlert]:
        """
        List drift alerts.

        Args:
            resolved: If True, return resolved alerts instead of active ones

        Returns:
            List[DriftAlert]

        Example:
            # Active alerts — need attention
            for alert in client.drift.alerts():
                print(f"  [{alert.severity.upper()}] {alert.device_id}")
                print(f"    KL={alert.kl_score:.3f}  monitor={alert.monitor}")
                print(f"    Model: {alert.model_ref}")
                print(f"    Since: {alert.detected_at}")

            # Resolved alerts — for audit/history
            for alert in client.drift.alerts(resolved=True):
                print(f"  {alert.device_id}  resolved={alert.resolved_at}")
        """
        data = self._http.request(
            "GET", "/drift/alerts",
            params={"resolved": str(resolved).lower()},
        )
        return [DriftAlert.from_dict(a) for a in data.get("data", [])]

    def device_history(
        self,
        device_id: str,
        hours:     int = 24,
        interval:  str = "5m",
    ) -> Dict:
        """
        Get KL divergence history for a specific device.

        Args:
            device_id: Device identifier
            hours:     Hours of history to return (default 24)
            interval:  Aggregation interval e.g. "1m" | "5m" | "1h"

        Returns:
            Dict with "data" list of {ts, kl_score, monitor} points

        Example:
            history = client.drift.device_history("jetson-prod-01", hours=6)
            for point in history["data"]:
                bar = "█" * int(point["kl_score"] * 20)
                print(f"  {point['ts']}  {point['kl_score']:.3f}  {bar}")
        """
        return self._http.request(
            "GET", f"/drift/{device_id}/history",
            params={"hours": hours, "interval": interval},
        )

    def reset_baseline(self, device_id: str) -> bool:
        """
        Reset the drift baseline for a device.

        Use this after:
        - A planogram change or product line switch (retail)
        - A lighting or environment change (manufacturing)
        - A patient population change (medical)
        - Any known distribution shift that is expected and acceptable

        The agent will capture a new baseline over the next 200 inferences.
        Drift monitoring is paused during recalibration.

        Args:
            device_id: Device identifier

        Returns:
            True on success

        Example:
            # After a product line switch at the factory
            client.drift.reset_baseline("jetson-floor-b-12")
            print("Baseline reset — recalibrating over next 200 inferences")
        """
        self._http.request("POST", f"/drift/{device_id}/baseline/reset")
        return True

    def reset_baseline_fleet(
        self,
        hw_class: Optional[str] = None,
        model:    Optional[str] = None,
    ) -> Dict:
        """
        Reset drift baselines for all matching devices (or entire fleet).

        Args:
            hw_class: Only reset devices of this hardware class
            model:    Only reset devices running this model

        Returns:
            Dict with count of devices reset

        Example:
            # Reset all Jetson Nanos after a lighting rig change
            result = client.drift.reset_baseline_fleet(hw_class="jetson_nano")
            print(f"Reset baseline on {result['count']} devices")

            # Reset everything running the retail model after a planogram update
            result = client.drift.reset_baseline_fleet(model="shelf-detector")
            print(f"Reset baseline on {result['count']} devices")
        """
        payload: Dict = {}
        if hw_class: payload["hw_class"] = hw_class
        if model:    payload["model"]    = model
        return self._http.request("POST", "/drift/baseline/reset-fleet", json=payload)
