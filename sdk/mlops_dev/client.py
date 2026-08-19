"""
mlops_dev.client — main entry point for the MLOps.dev Python SDK.

    import mlops_dev as mlops

    client = mlops.Client(api_key="your-key")  # or set MLOPS_API_KEY env var

    # ── Model management ─────────────────────────────────────────
    # Push a model
    v = client.models.push("./model.onnx", name="defect-detector", tag="v1.0")

    # Push TensorRT engine (Jetson Orin specific)
    v = client.models.push(
        "./model_orin_int8.engine",
        name="defect-detector",
        tag="v1.0",
        format="tensorrt",
        variant="jetson_orin",
        metadata={"accuracy": "0.942", "input_shape": "[1,3,224,224]"},
    )

    # List all registered models
    for model in client.models.list():
        for ver in model.versions:
            print(f"{model.name}:{ver.tag}  {ver.format}  {ver.size_mb}MB  active={ver.active_devices}")

    # ── Deployments ───────────────────────────────────────────────
    # Simple deploy to one device
    dep = client.deploy("defect-detector:v1.0", target="jetson-prod-01")
    dep.wait()

    # Staged canary rollout
    dep = client.deploy(
        "defect-detector:v2.0",
        target="all",
        stages=[
            {"hw_class": "jetson_orin", "count": 1},
            {"hw_class": "jetson_orin", "pct": 100},
            {"hw_class": "jetson_nano", "pct": 25},
            {"hw_class": "all",         "pct": 100},
        ],
        health_gate={"accuracy_delta": -0.03, "latency_delta": 0.20},
        stage_interval="30m",
    )
    dep.wait(on_stage=lambda s, st, d: print(f"Stage {s}: {st}"))

    # Rollback entire fleet
    client.rollback(to="defect-detector:v1.0")

    # Rollback one device
    client.rollback(device_id="jetson-prod-01", to="defect-detector:v1.0")

    # ── Fleet monitoring ─────────────────────────────────────────
    # All devices
    for d in client.devices.list():
        print(f"{d.id:20}  {d.status.value:8}  drift={d.drift_score:.3f}  latency={d.latency_ms:.1f}ms")

    # Drifting Jetson Orins only
    for d in client.devices.list(status="drift", hw_class="jetson_orin"):
        print(f"  DRIFT: {d.id}  KL={d.drift_score:.3f}")

    # ── Drift detection ──────────────────────────────────────────
    report = client.drift.report()
    print(f"{report.drifting}/{report.total_devices} drifting  avg_kl={report.fleet_avg_kl:.3f}")

    for alert in client.drift.alerts():
        print(f"  [{alert.severity}] {alert.device_id}  KL={alert.kl_score:.3f}")

    # Reset baseline after an expected distribution change
    client.drift.reset_baseline("jetson-prod-01")
"""

import os
from typing import Optional, List, Dict, Any

from .http import HTTPClient, DEFAULT_BASE
from .exceptions import AuthenticationError


class Client:
    """
    MLOps.dev Python SDK — main client.

    All API calls go through this object.
    Instantiate once and reuse across your application.

    Args:
        api_key:  Your MLOps.dev API key.
                  If not provided, reads MLOPS_API_KEY environment variable.
                  Get your key at https://www.mlops.dev/dashboard → Settings.
        base_url: Override the API base URL (default: https://api.mlops.dev/v1).
                  Useful for local development or Enterprise on-premise deployments.
        timeout:  Request timeout in seconds (default: 30).
                  Model pushes use a separate 300s timeout regardless.

    Raises:
        AuthenticationError: if no API key is provided or found in the environment.

    Examples:
        # Standard usage
        import mlops_dev as mlops
        client = mlops.Client(api_key="mlops_live_xxxx")

        # From environment variable (recommended for production)
        # export MLOPS_API_KEY=mlops_live_xxxx
        client = mlops.Client()

        # Enterprise on-premise deployment
        client = mlops.Client(
            api_key="mlops_live_xxxx",
            base_url="https://mlops.yourcompany.internal/api/v1",
        )

        # Local development (against the Flask backend)
        client = mlops.Client(
            api_key="demo_key",
            base_url="http://localhost:8000/api/v1",
        )
    """

    def __init__(
        self,
        api_key:  Optional[str] = None,
        base_url: str = DEFAULT_BASE,
        timeout:  int = 30,
    ):
        resolved_key = api_key or os.environ.get("MLOPS_API_KEY", "").strip()
        if not resolved_key:
            raise AuthenticationError(
                "No API key provided.\n"
                "  Pass it directly:       mlops.Client(api_key='mlops_live_xxx')\n"
                "  Or set env variable:    export MLOPS_API_KEY=mlops_live_xxx\n"
                "  Get your key at:        https://www.mlops.dev/dashboard → Settings"
            )

        self._http = HTTPClient(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
        )

        # Sub-API namespaces
        from .models      import ModelsAPI
        from .devices     import DevicesAPI
        from .deployments import DeploymentsAPI
        from .drift       import DriftAPI

        self.models      = ModelsAPI(self._http)
        self.devices     = DevicesAPI(self._http)
        self.deployments = DeploymentsAPI(self._http)
        self.drift       = DriftAPI(self._http)

    # ── Convenience methods ───────────────────────────────────────────

    def deploy(
        self,
        model:          str,
        target:         str,
        stages:         Optional[List[Dict]] = None,
        health_gate:    Optional[Dict] = None,
        stage_interval: Optional[str] = None,
    ) -> "Any": # noqa: F821
        """
        Deploy a model version to one device, a hardware class, or your entire fleet.

        This is the primary way to update models on edge devices.
        The mlops-agent on each device pulls the update, verifies the SHA-256
        checksum, loads the new model, and reports back. If the device is
        offline, the update queues and is applied on reconnection.

        Args:
            model:          Model reference: "name:tag" e.g. "defect-detector:v2.0"
            target:         Where to deploy:
                              - Device ID:    "jetson-prod-01"
                              - Hardware class: "jetson_orin" | "jetson_nano" | "rpi5" | ...
                              - All devices:  "all"
            stages:         Staged canary rollout. List of stage dicts:
                              {"hw_class": "jetson_orin", "count": 1}   # first N devices
                              {"hw_class": "jetson_orin", "pct": 100}   # % of hw_class
                              {"hw_class": "all",         "pct": 100}   # all remaining
                            If omitted, deploys to all matching devices simultaneously.
            health_gate:    Halt the rollout if metrics degrade beyond thresholds:
                              {"accuracy_delta": -0.03}     # stop if accuracy drops >3%
                              {"latency_delta":  0.20}      # stop if latency rises >20%
                              {"error_rate":     0.01}      # stop if error rate >1%
                            Multiple thresholds are ANDed. Failed stages trigger
                            automatic rollback on affected devices.
            stage_interval: Time to wait between stages e.g. "30m" | "2h" | "1d"
                            Gives time for metrics to stabilise before progressing.

        Returns:
            Deployment — call .wait() to block, or poll with .refresh()

        Examples:
            # Deploy to one device
            dep = client.deploy("defect-detector:v1.0", target="jetson-prod-01")
            dep.wait()
            print(dep.status)  # completed

            # Deploy to all Jetson Nanos immediately
            dep = client.deploy("defect-detector:v1.0", target="jetson_nano")
            dep.wait(timeout=300)

            # Staged canary across a mixed fleet
            dep = client.deploy(
                "defect-detector:v2.0",
                target="all",
                stages=[
                    {"hw_class": "jetson_orin", "count": 1},   # 1 pilot
                    {"hw_class": "jetson_orin", "pct": 100},   # all Orins
                    {"hw_class": "jetson_nano", "pct": 25},    # 25% Nanos
                    {"hw_class": "all",         "pct": 100},   # full fleet
                ],
                health_gate={"accuracy_delta": -0.03, "latency_delta": 0.20},
                stage_interval="30m",
            )

            # Non-blocking with callback
            def on_stage(stage_num, status, dep):
                print(f"Stage {stage_num}/{dep.total_stages}: {status}")
                if status == "failed":
                    alert_team(dep)

            dep.wait(on_stage=on_stage)
        """
        from .deployments import Deployment
        name, tag = model.split(":", 1) if ":" in model else (model, "latest")
        payload: Dict[str, Any] = {
            "model_name": name,
            "model_tag":  tag,
            "target":     target,
        }
        if stages:          payload["stages"]          = stages
        if health_gate:     payload["health_gate"]     = health_gate
        if stage_interval:  payload["stage_interval"]  = stage_interval

        data = self._http.request("POST", "/deployments", json=payload)
        return Deployment.from_dict(data["data"], http=self._http)

    def rollback(
        self,
        device_id: Optional[str] = None,
        to:        Optional[str] = None,
    ) -> Dict:
        """
        Roll back a device or the entire fleet to a previous model version.

        The rollback uses the same delta-compression mechanism as a normal
        deployment — the agent receives only the diff between the current
        and target version. If the device is offline it will roll back
        on next reconnection.

        Args:
            device_id: Target device ID.
                         If None, rolls back the entire fleet.
            to:        Model version to roll back to e.g. "defect-detector:v1.0"
                         If None, rolls back to the previous active version.

        Returns:
            Dict with rollback status and affected device count

        Examples:
            # Emergency fleet-wide rollback
            result = client.rollback()
            print(f"Rolling back {result['affected_devices']} devices")

            # Roll back one device to a specific version
            result = client.rollback(
                device_id="jetson-prod-01",
                to="defect-detector:v1.0",
            )

            # Roll back all Jetson Nanos (via deployment)
            dep = client.deploy(
                "defect-detector:v1.0",
                target="jetson_nano",
            )
            dep.wait()
        """
        payload: Dict[str, Any] = {}
        if device_id: payload["device_id"] = device_id
        if to:
            name, tag = to.split(":", 1) if ":" in to else (to, "latest")
            payload["model_name"] = name
            payload["model_tag"]  = tag

        return self._http.request("POST", "/deployments/rollback", json=payload)

    def status(self) -> Dict:
        """
        Get a fleet-wide health summary.

        Returns:
            Dict with:
              total_devices:  int
              online:         int
              offline:        int
              drifting:       int
              active_deployments: int
              api_version:    str

        Example:
            s = client.status()
            print(f"Fleet: {s['online']}/{s['total_devices']} online")
            print(f"Drifting: {s['drifting']}")
        """
        return self._http.request("GET", "/status")

    def health(self) -> bool:
        """
        Check if the MLOps.dev API is reachable and your key is valid.

        Returns:
            True if the API is reachable and the key is authenticated.
            False on network error (does not raise).

        Example:
            if not client.health():
                print("API unreachable — check https://www.mlops.dev/status")
        """
        try:
            self._http.request("GET", "/health")
            return True
        except Exception:
            return False

    def audit(
        self,
        device_id:  Optional[str] = None,
        event_type: Optional[str] = None,
        since:      Optional[str] = None,
        until:      Optional[str] = None,
        format:     str = "json",
        limit:      int = 100,
    ) -> Dict:
        """
        Export the immutable audit log.

        Required for FDA 21 CFR Part 11, ISO 13485, and CE MDR Article 10
        software change control documentation.

        Args:
            device_id:  Filter by device
            event_type: Filter by event type — "deployment" | "drift" | "rollback" | "auth"
            since:      ISO 8601 start date e.g. "2025-01-01"
            until:      ISO 8601 end date e.g. "2025-07-15"
            format:     "json" (default) or "csv"
            limit:      Max records (default 100, max 10000)

        Returns:
            Dict with "data" list of audit records, or CSV string if format="csv"

        Example:
            # Export all deployments for a device in Q1 2025
            log = client.audit(
                device_id="jetson-prod-01",
                event_type="deployment",
                since="2025-01-01",
                until="2025-03-31",
                format="csv",
            )
            with open("audit-q1-jetson-prod-01.csv", "w") as f:
                f.write(log["csv"])
        """
        params: Dict[str, Any] = {"format": format, "limit": limit}
        if device_id:  params["device_id"]  = device_id
        if event_type: params["event_type"] = event_type
        if since:      params["since"]      = since
        if until:      params["until"]      = until
        return self._http.request("GET", "/audit", params=params)

    def __repr__(self) -> str:
        return f"<mlops_dev.Client base_url={self._http.base_url!r}>"
