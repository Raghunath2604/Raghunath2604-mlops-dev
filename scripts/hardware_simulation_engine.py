#!/usr/bin/env python3
"""
MLOps.dev — Silicon Digital Twin Simulation Engine
Simulates all 17 tier-1 edge hardware platforms with realistic silicon metrics,
temperatures, latency, model runtimes, and camera sensor payloads.
"""

import os
import sys
import time
import math
import random
import threading
import requests
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HARDWARE_PROFILES = {
    # ── 1. Embedded Edge AI Boards ────────────────────────────────────
    "jetson_agx_orin": {
        "device_id": "hw-jetson-agx-orin-01",
        "name": "NVIDIA Jetson AGX Orin (64GB)",
        "hw_class": "jetson_orin",
        "chipset": "12-core ARM Cortex-A78AE + 2048-core NVIDIA Ampere GPU",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["tensorrt", "onnx", "deepstream"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 2.8,
        "base_fps": 142.0,
        "base_ram_mb": 1850,
        "base_temp_c": 54.2,
        "base_cpu_pct": 32.5,
        "sensor": "Stereo 4K GMSL2 Cameras (60 FPS)",
        "use_case": "Multi-camera video analytics (16+ 4K streams)"
    },
    "jetson_orin_nano": {
        "device_id": "hw-jetson-orin-nano-02",
        "name": "NVIDIA Jetson Orin Nano (8GB)",
        "hw_class": "jetson_orin",
        "chipset": "6-core ARM Cortex-A78AE + 1024-core NVIDIA Ampere GPU",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["tensorrt", "onnx", "pytorch"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 6.4,
        "base_fps": 78.0,
        "base_ram_mb": 920,
        "base_temp_c": 48.0,
        "base_cpu_pct": 28.0,
        "sensor": "Sony IMX477 MIPI CSI-2 (12.3MP)",
        "use_case": "Autonomous Mobile Robots (AMRs), Factory QA"
    },
    "jetson_nano": {
        "device_id": "hw-jetson-nano-03",
        "name": "NVIDIA Jetson Nano (4GB)",
        "hw_class": "jetson_nano",
        "chipset": "Quad-core ARM Cortex-A57 + 128-core Maxwell GPU",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["tensorrt", "onnx"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 19.2,
        "base_fps": 28.0,
        "base_ram_mb": 480,
        "base_temp_c": 42.5,
        "base_cpu_pct": 45.0,
        "sensor": "Sony IMX219 CSI (8MP)",
        "use_case": "Low-cost entry-level smart inspection"
    },
    "rpi5": {
        "device_id": "hw-rpi5-edge-04",
        "name": "Raspberry Pi 5 (8GB ARM64)",
        "hw_class": "rpi5",
        "chipset": "Broadcom BCM2712 Quad Cortex-A76 @ 2.4GHz",
        "arch": "arm64",
        "os": "linux",
        "supported_runtimes": ["onnx", "tflite", "opencv"],
        "active_model": "defect-detector",
        "active_tag": "v0.9",
        "base_latency_ms": 32.0,
        "base_fps": 31.0,
        "base_ram_mb": 380,
        "base_temp_c": 43.8,
        "base_cpu_pct": 22.0,
        "sensor": "RPi Camera Module 3 (Sony IMX708 HDR Autofocus)",
        "use_case": "Smart gateways, automated sorting, logistics"
    },
    "rpi4": {
        "device_id": "hw-rpi4-telemetry-05",
        "name": "Raspberry Pi 4 Model B (4GB)",
        "hw_class": "rpi4",
        "chipset": "Broadcom BCM2711 Quad Cortex-A72 @ 1.8GHz",
        "arch": "arm64",
        "os": "linux",
        "supported_runtimes": ["tflite", "opencv", "pytorch_mobile"],
        "active_model": "defect-detector",
        "active_tag": "v0.9",
        "base_latency_ms": 54.0,
        "base_fps": 18.5,
        "base_ram_mb": 260,
        "base_temp_c": 49.0,
        "base_cpu_pct": 35.0,
        "sensor": "USB UVC 1080p Optical Sensor",
        "use_case": "IoT telemetry, retail shelf monitoring"
    },
    "rpi5_hailo": {
        "device_id": "hw-rpi5-hailo-ai-06",
        "name": "Raspberry Pi AI Kit (Hailo-8L 13 TOPS)",
        "hw_class": "rpi5_hailo",
        "chipset": "Broadcom BCM2712 + Hailo-8L 13 TOPS PCIe NPU",
        "arch": "arm64",
        "os": "linux",
        "supported_runtimes": ["hailort", "onnx"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 8.1,
        "base_fps": 90.0,
        "base_ram_mb": 320,
        "base_temp_c": 46.2,
        "base_cpu_pct": 12.0,
        "sensor": "RPi Global Shutter Camera (Sony IMX296)",
        "use_case": "High-speed real-time conveyor belt object detection (30+ FPS)"
    },
    "coral_dev_board": {
        "device_id": "hw-coral-dev-07",
        "name": "Google Coral Dev Board (Edge TPU)",
        "hw_class": "coral_tpu",
        "chipset": "NXP i.MX 8M SoC + Google Edge TPU (4 TOPS)",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["edgetpu", "tflite_int8"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 9.8,
        "base_fps": 85.0,
        "base_ram_mb": 180,
        "base_temp_c": 38.5,
        "base_cpu_pct": 14.0,
        "sensor": "OmniVision OV5645 MIPI Camera",
        "use_case": "Ultra-low power vision (sub-2W power envelope)"
    },
    "orangepi_5": {
        "device_id": "hw-orangepi5-plus-08",
        "name": "Orange Pi 5 Plus (RK3588)",
        "hw_class": "rk3588",
        "chipset": "Rockchip RK3588 (4x A76 + 4x A55) + 6 TOPS NPU",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["rknn", "onnx"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 12.4,
        "base_fps": 65.0,
        "base_ram_mb": 410,
        "base_temp_c": 44.0,
        "base_cpu_pct": 18.0,
        "sensor": "Dual MIPI CSI 4K Optical Sensors",
        "use_case": "Cost-effective edge surveillance gateways"
    },
    "khadas_vim4": {
        "device_id": "hw-khadas-vim4-09",
        "name": "Khadas VIM4 (A311D2)",
        "hw_class": "khadas_vim",
        "chipset": "Amlogic A311D2 (4x A73 + 4x A53) + 5.0 TOPS NPU",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["openvino", "tflite"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 14.5,
        "base_fps": 58.0,
        "base_ram_mb": 340,
        "base_temp_c": 41.0,
        "base_cpu_pct": 20.0,
        "sensor": "OS08A10 8MP MIPI Sensor",
        "use_case": "Drone payloads, smart displays, kiosks"
    },

    # ── 2. Plug-and-Play USB Accelerators ─────────────────────────────
    "coral_usb": {
        "device_id": "hw-coral-usb-node-10",
        "name": "Google Coral USB Accelerator Node",
        "hw_class": "coral_usb",
        "chipset": "Host x86/ARM + Google Edge TPU Coprocessor (USB 3.0)",
        "arch": "x86_64",
        "os": "linux",
        "supported_runtimes": ["edgetpu", "tflite_int8"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 10.2,
        "base_fps": 82.0,
        "base_ram_mb": 220,
        "base_temp_c": 36.5,
        "base_cpu_pct": 8.0,
        "sensor": "Logitech Brio 4K USB Pro",
        "use_case": "Dedicated INT8 neural processing via USB-C"
    },
    "oak_d": {
        "device_id": "hw-luxonis-oakd-11",
        "name": "Luxonis OAK-D Spatial AI Camera",
        "hw_class": "oak_d",
        "chipset": "Intel Myriad X VPU + Stereo Depth Sensors",
        "arch": "myriad_x",
        "os": "embedded",
        "supported_runtimes": ["depthai", "openvino"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 11.0,
        "base_fps": 60.0,
        "base_ram_mb": 150,
        "base_temp_c": 42.0,
        "base_cpu_pct": 5.0,
        "sensor": "Stereo 1280x800 Depth + 12MP Color Camera",
        "use_case": "Spatial coordinates, 3D object tracking directly on sensor"
    },
    "intel_ncs2": {
        "device_id": "hw-intel-ncs2-12",
        "name": "Intel Neural Compute Stick 2 (NCS2)",
        "hw_class": "intel_ncs2",
        "chipset": "Intel Movidius Myriad X VPU (USB 3.1 Gen1)",
        "arch": "x86_64",
        "os": "linux",
        "supported_runtimes": ["openvino"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 16.8,
        "base_fps": 45.0,
        "base_ram_mb": 290,
        "base_temp_c": 47.0,
        "base_cpu_pct": 10.0,
        "sensor": "Logitech C920 HD Pro (1080p)",
        "use_case": "Low-power VPU inference on existing PCs"
    },

    # ── 3. Industrial Gateways & x86 Mini PCs ──────────────────────────
    "intel_nuc13": {
        "device_id": "hw-intel-nuc13-pro-13",
        "name": "Intel NUC 13 Pro (Core i7 / Iris Xe)",
        "hw_class": "x86_64",
        "chipset": "14-core Intel Core i7-1360P + Intel Iris Xe Graphics",
        "arch": "x86_64",
        "os": "linux",
        "supported_runtimes": ["openvino", "onnx", "tensorrt_x86"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 4.5,
        "base_fps": 120.0,
        "base_ram_mb": 1450,
        "base_temp_c": 58.0,
        "base_cpu_pct": 25.0,
        "sensor": "Basler ace GigE Area Scan Camera",
        "use_case": "Hospital imaging, local clinic PACS AI processing"
    },
    "advantech_uno": {
        "device_id": "hw-advantech-uno-14",
        "name": "Advantech UNO-2271G Industrial Box PC",
        "hw_class": "advantech_ipc",
        "chipset": "Intel Celeron N3350 Dual Core (IP65 Fanless)",
        "arch": "x86_64",
        "os": "linux",
        "supported_runtimes": ["openvino", "tflite"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 38.0,
        "base_fps": 22.0,
        "base_ram_mb": 480,
        "base_temp_c": 61.5,
        "base_cpu_pct": 40.0,
        "sensor": "RS-485 / Industrial Basler GigE Camera",
        "use_case": "Factory floor conveyor belt defect inspection"
    },
    "siemens_iot2050": {
        "device_id": "hw-siemens-iot2050-15",
        "name": "Siemens SIMATIC IOT2050 Gateway",
        "hw_class": "siemens_ipc",
        "chipset": "TI AM6528 Dual Cortex-A53 (Industrial Grade)",
        "arch": "arm64",
        "os": "linux",
        "supported_runtimes": ["tflite", "onnx_micro"],
        "active_model": "defect-detector",
        "active_tag": "v0.9",
        "base_latency_ms": 65.0,
        "base_fps": 12.0,
        "base_ram_mb": 310,
        "base_temp_c": 55.0,
        "base_cpu_pct": 35.0,
        "sensor": "PROFINET / Modbus TCP PLC Vibration Sensor",
        "use_case": "Predictive maintenance, industrial telemetry collection"
    },
    "onlogic_karbon800": {
        "device_id": "hw-onlogic-karbon800-16",
        "name": "OnLogic Karbon 800 Rugged Edge Computer",
        "hw_class": "rugged_x86",
        "chipset": "Intel 12th Gen Core i9-12900E + NVIDIA RTX GPU",
        "arch": "x86_64",
        "os": "linux",
        "supported_runtimes": ["tensorrt", "openvino", "onnx"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 2.2,
        "base_fps": 165.0,
        "base_ram_mb": 2400,
        "base_temp_c": 64.0,
        "base_cpu_pct": 38.0,
        "sensor": "4x PoE+ GigE Machine Vision Cameras",
        "use_case": "Autonomous mining vehicles, railway track inspection"
    },

    # ── 4. Spatial Vision Sensor Node ─────────────────────────────────
    "realsense_d435i": {
        "device_id": "hw-realsense-d435i-17",
        "name": "Intel RealSense D435i Spatial Vision Node",
        "hw_class": "realsense_node",
        "chipset": "RealSense Vision D4 ASIC + Jetson Orin Host",
        "arch": "aarch64",
        "os": "linux",
        "supported_runtimes": ["tensorrt", "openvino_depth"],
        "active_model": "defect-detector",
        "active_tag": "v1.0",
        "base_latency_ms": 5.1,
        "base_fps": 90.0,
        "base_ram_mb": 850,
        "base_temp_c": 46.0,
        "base_cpu_pct": 26.0,
        "sensor": "Active IR Stereo Depth + RGB IMU (BMI055)",
        "use_case": "Pallet volume dimensioning, warehouse AGV obstacle avoidance"
    }
}

class SimulatedHardwareNode:
    def __init__(self, key: str, profile: dict, api_url: str, api_key: str):
        self.key = key
        self.profile = profile
        self.device_id = profile["device_id"]
        self.name = profile["name"]
        self.hw_class = profile["hw_class"]
        self.arch = profile["arch"]
        self.os_name = profile["os"]
        self.active_model = profile["active_model"]
        self.active_tag = profile["active_tag"]
        
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        # Dynamic telemetry
        self.drift_score = 0.02
        self.inference_count = 0
        self.is_offline = False
        self.offline_buffer: List[dict] = []
        
    def register(self):
        """Register the simulated hardware node with the control plane."""
        payload = {
            "device_id": self.device_id,
            "name": self.name,
            "hw_class": self.hw_class,
            "arch": self.arch,
            "os": self.os_name
        }
        try:
            res = self.session.post(f"{self.api_url}/agent/register", json=payload, timeout=5)
            if res.status_code in [200, 201]:
                print(f"  [REGISTERED] {self.name:42} ID={self.device_id} ({self.hw_class})")
                return True
            else:
                print(f"  [ERROR] {self.name} registration failed: {res.status_code} {res.text}")
                return False
        except Exception as e:
            print(f"  [ERROR] {self.name} connection failed: {e}")
            return False

    def heartbeat(self):
        """Send a single live telemetry heartbeat with physical fluctuations."""
        if self.is_offline:
            # Buffer telemetry locally
            self.offline_buffer.append({"ts": time.time(), "drift": self.drift_score})
            return None

        # Add realistic silicon noise
        jitter = random.uniform(-0.08, 0.08)
        ram = int(self.profile["base_ram_mb"] * (1.0 + jitter * 0.1))
        cpu = round(max(5.0, min(95.0, self.profile["base_cpu_pct"] * (1.0 + jitter))), 1)
        temp = round(max(30.0, self.profile["base_temp_c"] + jitter * 4.0), 1)
        latency = round(max(1.0, self.profile["base_latency_ms"] * (1.0 + jitter * 0.2)), 2)
        fps = round(max(5.0, self.profile["base_fps"] * (1.0 - jitter * 0.1)), 1)
        self.inference_count += int(fps * 2)

        payload = {
            "device_id": self.device_id,
            "ram_mb": ram,
            "cpu_pct": cpu,
            "temp_c": temp,
            "latency_ms": latency,
            "drift_score": round(self.drift_score, 3),
            "inferences_since_last": int(fps * 2),
            "model_name": self.active_model,
            "model_tag": self.active_tag
        }

        try:
            res = self.session.post(f"{self.api_url}/agent/heartbeat", json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                dep = data.get("deployment")
                if dep:
                    # Model rollout detected!
                    new_model = dep.get("model_name")
                    new_tag = dep.get("model_tag")
                    if new_model != self.active_model or new_tag != self.active_tag:
                        print(f"  [ROLLOUT ACCEPTED] {self.name} -> Updating: {new_model}:{new_tag}")
                        self.active_model = new_model
                        self.active_tag = new_tag
                return payload
        except Exception:
            pass
        return None

    def start_loop(self, interval_s: float = 3.0):
        self.running = True
        def _loop():
            while self.running:
                self.heartbeat()
                time.sleep(interval_s)
        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False


class SiliconFleetSimulator:
    def __init__(self, api_url: str = "http://localhost:8000/v1", api_key: str = "demo"):
        self.api_url = api_url
        self.api_key = api_key
        self.nodes: Dict[str, SimulatedHardwareNode] = {}
        for key, profile in HARDWARE_PROFILES.items():
            self.nodes[key] = SimulatedHardwareNode(key, profile, api_url, api_key)

    def boot_all(self):
        from concurrent.futures import ThreadPoolExecutor
        print("\n" + "=" * 70)
        print(f"  BOOTING ALL 17 SILICON DIGITAL TWINS (Target: {self.api_url})")
        print("=" * 70)
        def _init_node(node):
            try:
                if node.register():
                    node.heartbeat()
                    return 1
            except Exception:
                pass
            return 0
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(_init_node, self.nodes.values()))
        success_count = sum(results)
        print(f"\n[FLEET READY] {success_count} / {len(self.nodes)} Hardware Platforms Initialized.")
        return success_count

    def start_continuous_heartbeats(self, interval_s: float = 4.0):
        for node in self.nodes.values():
            node.start_loop(interval_s)
        print(f"[DAEMON] All 17 hardware devices streaming live telemetry every {interval_s}s.")

    def inject_drift(self, key: str, drift_score: float = 0.72):
        if key in self.nodes:
            self.nodes[key].drift_score = drift_score
            print(f"[DRIFT INJECTED] {self.nodes[key].name} drift score raised to {drift_score}!")
            self.nodes[key].heartbeat()

    def simulate_disconnect(self, key: str, disconnected: bool = True):
        if key in self.nodes:
            self.nodes[key].is_offline = disconnected
            status = "DISCONNECTED (Buffering locally)" if disconnected else "RECONNECTED (Draining buffer)"
            print(f"[NETWORK EVENT] {self.nodes[key].name} -> {status}")
            if not disconnected and len(self.nodes[key].offline_buffer) > 0:
                print(f"  Flushing {len(self.nodes[key].offline_buffer)} cached telemetry frames...")
                self.nodes[key].offline_buffer.clear()
                self.nodes[key].heartbeat()

if __name__ == "__main__":
    url = os.environ.get("MLOPS_API_URL", "http://localhost:8000/v1")
    key = os.environ.get("MLOPS_API_KEY", "demo")
    
    sim = SiliconFleetSimulator(api_url=url, api_key=key)
    count = sim.boot_all()
    
    # Run 1 round of heartbeats
    print("\nSending initial telemetry snapshot...")
    for n in sim.nodes.values():
        payload = n.heartbeat()
        if payload:
            print(f"  {n.name:42} | Temp: {payload['temp_c']}°C | CPU: {payload['cpu_pct']}% | RAM: {payload['ram_mb']}MB | Drift: {payload['drift_score']}")
            
    print("\n" + "=" * 70)
    print("  ALL 17 HARDWARE PLATFORMS ONLINE & MONITORED")
    print("=" * 70)
