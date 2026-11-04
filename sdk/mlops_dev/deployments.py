"""
mlops_dev.deployments — deploy models to edge devices with health gates and staged rollouts.

Usage:
    # Simple deploy to one device
    dep = client.deploy("defect-detector:v1.0", target="jetson-prod-01")
    dep.wait()
    print(dep.status)   # completed | failed

    # Staged canary rollout across a mixed fleet
    dep = client.deploy(
        "defect-detector:v2.0",
        target="all",
        stages=[
            # Stage 1: one Jetson Orin pilot device
            {"hw_class": "jetson_orin", "count": 1},
            # Stage 2: all Jetson Orins (100%)
            {"hw_class": "jetson_orin", "pct": 100},
            # Stage 3: 25% of Jetson Nanos
            {"hw_class": "jetson_nano", "pct": 25},
            # Stage 4: everything
            {"hw_class": "all", "pct": 100},
        ],
        health_gate={
            "accuracy_delta": -0.03,   # halt if accuracy drops > 3%
            "latency_delta":  0.20,    # halt if latency increases > 20%
            "error_rate":     0.01,    # halt if error rate exceeds 1%
        },
        stage_interval="30m",  # wait 30 minutes between stages
    )

    # Poll progress
    while dep.status == "running":
        dep.refresh()
        print(f"Stage {dep.stage}/{dep.total_stages}  {dep.status}")
        time.sleep(10)

    # Or block until done
    dep.wait(poll_interval=10, timeout=600)

    # Rollback if something went wrong
    if dep.status == "failed":
        client.rollback(to="defect-detector:v1.0")
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class DeploymentStage:
    """One stage in a staged canary rollout."""
    stage:          int
    target:         str
    status:         str    # pending | running | passed | failed | skipped
    devices_total:  int
    devices_done:   int    = 0
    started_at:     Optional[str] = None
    passed_at:      Optional[str] = None
    accuracy_delta: Optional[float] = None
    latency_delta:  Optional[float] = None

    @classmethod
    def from_dict(cls, d: Dict) -> "DeploymentStage":
        return cls(
            stage=d.get("stage", 0),
            target=d.get("target", ""),
            status=d.get("status", "pending"),
            devices_total=d.get("devices_total", 0),
            devices_done=d.get("devices_done", 0),
            started_at=d.get("started_at"),
            passed_at=d.get("passed_at"),
            accuracy_delta=d.get("accuracy_delta"),
            latency_delta=d.get("latency_delta"),
        )

    def __repr__(self) -> str:
        return (f"<Stage {self.stage}  {self.target}  {self.status}  "
                f"{self.devices_done}/{self.devices_total} devices>")


@dataclass
class Deployment:
    """
    A model deployment operation.

    Created by client.deploy() — do not instantiate directly.

    Attributes:
        id:           Unique deployment ID
        model_name:   Name of the model being deployed
        model_tag:    Version tag being deployed
        status:       Current status: pending | running | completed | failed | rolled_back
        stage:        Current stage number (1-indexed)
        total_stages: Total number of stages in the rollout
        target:       Deployment target (device ID, hw_class, or "all")
        created_at:   ISO 8601 creation timestamp
        stages:       List of DeploymentStage objects
        health_gate:  Health gate thresholds applied
    """
    id:           str
    model_name:   str
    model_tag:    str
    status:       str
    stage:        int
    total_stages: int
    target:       str
    created_at:   str
    stages:       List[DeploymentStage] = field(default_factory=list)
    health_gate:  Dict = field(default_factory=dict)
    _http:        Any  = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, d: Dict, http=None) -> "Deployment":
        stages = [DeploymentStage.from_dict(s) for s in d.get("stages", [])]
        return cls(
            id=d.get("id", ""),
            model_name=d.get("model_name", ""),
            model_tag=d.get("model_tag", ""),
            status=d.get("status", "pending"),
            stage=d.get("stage", 0),
            total_stages=d.get("total_stages", 1),
            target=d.get("target", ""),
            created_at=d.get("created_at", ""),
            stages=stages,
            health_gate=d.get("health_gate", {}),
            _http=http,
        )

    @property
    def model_ref(self) -> str:
        return f"{self.model_name}:{self.model_tag}"

    @property
    def is_done(self) -> bool:
        return self.status in ("completed", "failed", "rolled_back")

    def refresh(self) -> "Deployment":
        """
        Fetch the latest status from the API and update this object in place.

        Returns:
            self (updated)

        Example:
            dep = client.deploy("defect-detector:v2.0", target="all")
            while not dep.is_done:
                dep.refresh()
                print(f"Stage {dep.stage}/{dep.total_stages}  {dep.status}")
                time.sleep(5)
        """
        data = self._http.request("GET", f"/deployments/{self.id}")
        updated = Deployment.from_dict(data["data"], http=self._http)
        self.__dict__.update(updated.__dict__)
        return self

    def wait(
        self,
        poll_interval: float = 5.0,
        timeout:       float = 600.0,
        on_stage:      Optional[Any] = None,
    ) -> "Deployment":
        """
        Block until this deployment completes, fails, or times out.

        Args:
            poll_interval: Seconds between status polls (default 5.0)
            timeout:       Maximum seconds to wait (default 600 = 10 min)
            on_stage:      Optional callback called on each stage transition:
                             on_stage(stage: int, status: str, dep: Deployment)

        Returns:
            self (with final status)

        Raises:
            TimeoutError: if deployment has not completed within timeout seconds

        Example:
            def log_stage(stage, status, dep):
                print(f"  → Stage {stage}: {status}")

            dep = client.deploy("defect-detector:v2.0", target="all", stages=[...])
            dep.wait(poll_interval=10, timeout=300, on_stage=log_stage)

            if dep.status == "completed":
                print("All devices updated ✓")
            elif dep.status == "failed":
                print(f"Failed at stage {dep.stage} — rolling back")
                client.rollback(to="defect-detector:v1.0")
        """
        last_stage = self.stage
        elapsed = 0.0
        while elapsed < timeout:
            self.refresh()
            if on_stage and self.stage != last_stage:
                on_stage(self.stage, self.status, self)
                last_stage = self.stage
            if self.is_done:
                return self
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(
            f"Deployment {self.id} did not complete within {timeout}s. "
            f"Last status: {self.status} at stage {self.stage}/{self.total_stages}. "
            f"Check the dashboard at https://www.mlops.dev/dashboard"
        )

    def rollback(self) -> Dict:
        """
        Trigger a rollback for this deployment specifically.
        Reverts all devices that received this deployment to the previous version.

        Returns:
            Dict with rollback status

        Example:
            dep.wait()
            if dep.status == "failed":
                result = dep.rollback()
                print(f"Rollback: {result['status']}")
        """
        return self._http.request("POST", f"/deployments/{self.id}/rollback")

    def __repr__(self) -> str:
        return (f"<Deployment {self.id[:8]}...  {self.model_ref}  "
                f"{self.status}  stage={self.stage}/{self.total_stages}>")


class DeploymentsAPI:
    """
    Manage model deployments.
    Access via: client.deployments
    """

    def __init__(self, http):
        self._http = http

    def list(self, limit: int = 20, status: Optional[str] = None) -> List[Deployment]:
        """
        List recent deployments.

        Args:
            limit:  Number of deployments to return (default 20)
            status: Filter by status — "running" | "completed" | "failed" | "rolled_back"

        Example:
            # Find any currently running deployments
            active = client.deployments.list(status="running")
            for dep in active:
                print(f"{dep.model_ref}  stage {dep.stage}/{dep.total_stages}")
        """
        params: Dict = {"limit": limit}
        if status: params["status"] = status
        data = self._http.request("GET", "/deployments", params=params)
        return [Deployment.from_dict(d, http=self._http) for d in data.get("data", [])]

    def get(self, deployment_id: str) -> Deployment:
        """
        Get a deployment by ID.

        Example:
            dep = client.deployments.get("dep_abc123")
            print(dep.status)
        """
        data = self._http.request("GET", f"/deployments/{deployment_id}")
        return Deployment.from_dict(data["data"], http=self._http)
