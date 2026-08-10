"""
mlops_dev.models — register and manage ML models in the MLOps.dev registry.

Usage:
    # Push ONNX model
    v = client.models.push("./model.onnx", name="defect-detector", tag="v1.0")
    print(f"Pushed {v.name}:{v.tag}  {v.size_mb}MB  sha={v.sha256[:8]}...")

    # Push hardware-specific TensorRT engine
    v = client.models.push(
        "./model_orin_int8.engine",
        name="defect-detector",
        tag="v1.0",
        variant="jetson_orin",
        metadata={"input_shape": "[1,3,224,224]", "quantisation": "int8"},
    )

    # List all models
    for model in client.models.list():
        for ver in model.versions:
            print(f"  {model.name}:{ver.tag}  {ver.format}  {ver.size_mb}MB  active={ver.active_devices}")

    # Delete a version
    client.models.delete("defect-detector", "v0.9")
"""

import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class ModelVersion:
    """A single version of a registered model."""
    id:             str
    name:           str
    tag:            str
    format:         str          # onnx | tflite | tensorrt
    variant:        str          # all | jetson_orin | jetson_nano | rpi5 | ...
    size_bytes:     int
    sha256:         str
    created_at:     str
    active_devices: int = 0
    metadata:       Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict) -> "ModelVersion":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            tag=d.get("tag", "latest"),
            format=d.get("format", "onnx"),
            variant=d.get("variant", "all"),
            size_bytes=d.get("size_bytes", 0),
            sha256=d.get("sha256", ""),
            created_at=d.get("created_at", ""),
            active_devices=d.get("active_devices", 0),
            metadata=d.get("metadata", {}),
        )

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / 1_000_000, 2)

    @property
    def ref(self) -> str:
        """Deployment reference string e.g. defect-detector:v1.0"""
        return f"{self.name}:{self.tag}"

    def __repr__(self) -> str:
        return (f"<ModelVersion {self.name}:{self.tag}  "
                f"format={self.format}  variant={self.variant}  "
                f"{self.size_mb}MB  active_devices={self.active_devices}>")


@dataclass
class Model:
    """A model with all its registered versions."""
    id:       str
    name:     str
    versions: List[ModelVersion] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict) -> "Model":
        versions = [ModelVersion.from_dict(v) for v in d.get("versions", [])]
        return cls(id=d.get("id", ""), name=d.get("name", ""), versions=versions)

    @property
    def latest(self) -> Optional[ModelVersion]:
        return self.versions[0] if self.versions else None

    def version(self, tag: str) -> Optional[ModelVersion]:
        """Get a specific version by tag."""
        return next((v for v in self.versions if v.tag == tag), None)

    def __repr__(self) -> str:
        return f"<Model {self.name}  versions={[v.tag for v in self.versions]}>"


class ModelsAPI:
    """
    Register and manage ML models in the MLOps.dev registry.
    Access via: client.models
    """

    def __init__(self, http):
        self._http = http

    # ── List ──────────────────────────────────────────────────────
    def list(self) -> List[Model]:
        """
        List all models in the registry.

        Returns:
            List of Model objects, each with .versions

        Example:
            for model in client.models.list():
                print(f"{model.name}")
                for v in model.versions:
                    print(f"  :{v.tag}  {v.format}  {v.size_mb}MB  on {v.active_devices} devices")
        """
        data = self._http.request("GET", "/models")
        return [Model.from_dict(m) for m in data.get("data", [])]

    # ── Get ───────────────────────────────────────────────────────
    def get(self, name: str) -> Model:
        """
        Get a model by name.

        Args:
            name: Model name e.g. "defect-detector"

        Raises:
            ModelNotFoundError: if no model with this name exists

        Example:
            model = client.models.get("defect-detector")
            latest = model.latest
            print(f"Latest: {latest.tag}  {latest.size_mb}MB")
        """
        from .exceptions import ModelNotFoundError
        try:
            data = self._http.request("GET", f"/models/{name}")
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise ModelNotFoundError(f"Model not found: {name}")
            raise
        return Model.from_dict(data["data"])

    # ── Push ──────────────────────────────────────────────────────
    def push(
        self,
        path:     str,
        name:     str,
        tag:      str = "latest",
        format:   Optional[str] = None,
        variant:  Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ModelVersion:
        """
        Push a model file to the MLOps.dev registry.

        The agent on each device will automatically pull the correct variant
        based on its hardware fingerprint — you don't need to manage this.

        Args:
            path:     Path to model file (.onnx, .tflite, .engine/.plan)
            name:     Model name e.g. "defect-detector"
            tag:      Version tag e.g. "v1.0" (default: "latest")
            format:   Override format detection: "onnx" | "tflite" | "tensorrt"
            variant:  Hardware variant for TensorRT engines:
                        "all" | "jetson_orin" | "jetson_nano" | "rpi5" | ...
                        Required when format="tensorrt" — TRT engines are device-specific!
            metadata: Optional dict of key-value metadata to store with the version
                        e.g. {"input_shape": "[1,3,224,224]", "accuracy": "0.94"}

        Returns:
            ModelVersion — the registered version

        Raises:
            FileNotFoundError: if the file does not exist
            MLOpsError:        on API errors

        Examples:
            # Push ONNX model (works on all ARM devices)
            v = client.models.push(
                "./model.onnx",
                name="defect-detector",
                tag="v1.0",
                metadata={"input_shape": "[1,3,224,224]", "accuracy": "0.942"},
            )
            print(f"Pushed {v.ref}  {v.size_mb}MB  sha={v.sha256[:8]}...")

            # Push TFLite INT8 for CPU-only ARM devices
            v = client.models.push(
                "./model_int8.tflite",
                name="defect-detector",
                tag="v1.0",
                variant="rpi5",
                metadata={"quantisation": "int8"},
            )

            # Push TensorRT engine for Jetson Orin — MUST specify variant!
            v = client.models.push(
                "./model_orin_int8.engine",
                name="defect-detector",
                tag="v1.0",
                format="tensorrt",
                variant="jetson_orin",
            )
            # Now do the same for Nano — same name:tag, different variant
            v = client.models.push(
                "./model_nano_fp16.engine",
                name="defect-detector",
                tag="v1.0",
                format="tensorrt",
                variant="jetson_nano",
            )
            # One deployment will send the right engine to each device type
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}\n"
                f"Make sure the path is correct and the file exists."
            )

        # Auto-detect format from extension
        if not format:
            ext_map = {
                ".onnx":   "onnx",
                ".tflite": "tflite",
                ".engine": "tensorrt",
                ".plan":   "tensorrt",
                ".pt":     "torchscript",
            }
            format = ext_map.get(p.suffix.lower(), "onnx")

        # Warn about TensorRT without variant
        if format == "tensorrt" and not variant:
            import warnings
            warnings.warn(
                "TensorRT engines are device-specific. "
                "Set variant= e.g. variant='jetson_orin' so the agent "
                "selects the correct engine for each device.",
                UserWarning, stacklevel=2,
            )

        # Compute local SHA-256 for integrity verification
        sha256 = hashlib.sha256()
        file_size = p.stat().st_size
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        local_sha = sha256.hexdigest()

        # Upload
        with open(p, "rb") as f:
            form_data = {
                "name":      name,
                "tag":       tag,
                "format":    format,
                "sha256":    local_sha,
            }
            if variant:  form_data["variant"]  = variant
            if metadata: form_data["metadata"] = str(metadata)

            data = self._http.upload(
                "/models",
                files={"model": (p.name, f, "application/octet-stream")},
                data=form_data,
            )

        return ModelVersion.from_dict(data["data"])

    # ── Delete ────────────────────────────────────────────────────
    def delete(self, name: str, tag: str) -> bool:
        """
        Delete a specific model version from the registry.

        Args:
            name: Model name
            tag:  Version tag to delete

        Returns:
            True on success

        Raises:
            ModelNotFoundError: if the version does not exist
            MLOpsError:         if the version is currently active on devices

        Example:
            # Remove old version — fails if still active on any device
            client.models.delete("defect-detector", "v0.9")
        """
        self._http.request("DELETE", f"/models/{name}/{tag}")
        return True
