# MLOps.dev — Technical Requirements Document (TRD)

**Document Version:** 2.4.0  
**Compliance Target:** Enterprise Edge Infrastructure / Industrial Grade SLA  
**Classification:** Deep Tech Engineering Specification  

---

## 1. Edge System Requirements & Prerequisites

Every physical edge node enrolled in MLOps.dev must satisfy the following minimum hardware and operating system constraints:

### 1.1 Minimum Compute & Memory Envelope
- **CPU Architecture:** `aarch64` (ARM64), `armv7l` (ARM32 - telemetry only), or `x86_64` (AMD64).
- **Minimum RAM:** 512 MB physical RAM (minimum 128 MB free memory allocated to ML inference).
- **Persistent Storage:** 2 GB available flash storage (eMMC, NVMe, or Class 10 U3 microSD).
- **Operating System:** Linux Kernel $\ge 5.4$ (Ubuntu 20.04/22.04/24.04 LTS, Debian 11/12, Raspberry Pi OS 64-bit, NVIDIA JetPack 5.x/6.x, Yocto Project LTS).
- **Init System:** `systemd` (required for service auto-supervision and cgroup resource containment).

### 1.2 Network Requirements & Bandwidth Budget
- **Outbound Connectivity:** HTTPS (TCP 443) outbound to `https://www.mlopsde.me`.
- **Inbound Ports:** **ZERO inbound ports required**. The edge node uses an outbound polling/heartbeat model with Server-Sent Events (SSE) or HTTP/2 multiplexing. Nodes can sit behind enterprise NAT, cellular CGNAT, or strict firewalls.
- **Heartbeat Bandwidth Footprint:** Average telemetry payload size is **420 bytes**. At a 30-second heartbeat interval, monthly telemetry consumption is **$< 38 \text{ MB/device/month}$** (critical for industrial satellite and 4G/LTE data plans).

---

## 2. Silicon Platform Specifications & Acceleration Matrix

| Hardware Tier | Core Architecture | Acceleration Runtime | Precision | Target Latency (ms) | Target FPS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NVIDIA Jetson AGX Orin** | 12x Cortex-A78AE + 2048-core Ampere | TensorRT 10.0 / DeepStream | FP16 / INT8 | 2.8 ms | 140+ FPS |
| **NVIDIA Jetson Orin Nano**| 6x Cortex-A78AE + 1024-core Ampere  | TensorRT 10.0 / PyTorch    | FP16 / INT8 | 6.4 ms | 75+ FPS |
| **NVIDIA Jetson Nano**     | 4x Cortex-A57 + 128-core Maxwell    | TensorRT 8.2 / ONNX        | FP16        | 19.2 ms| 28 FPS |
| **Raspberry Pi 5 + Hailo** | 4x Cortex-A76 + Hailo-8L 13 TOPS    | HailoRT (HEF binary)       | INT8        | 4.1 ms | 90+ FPS |
| **Raspberry Pi 5 Standalone**| 4x Cortex-A76 @ 2.4GHz             | ONNX Runtime / XNNPACK     | FP32 / FP16 | 32.0 ms| 31 FPS |
| **Google Coral Dev / USB** | Google Edge TPU Coprocessor (4 TOPS)| Edge TPU Runtime (libedgetpu)| INT8      | 10.2 ms| 55 FPS |
| **Orange Pi 5 Plus (RK3588)**| 4x A76 + 4x A55 + 6 TOPS NPU      | RKNN-Toolkit2 Runtime      | INT8 / FP16 | 12.4 ms| 65 FPS |
| **Khadas VIM4 (A311D2)**   | 4x A73 + 4x A53 + 5.0 TOPS NPU      | OpenVINO / TFLite          | INT8        | 14.5 ms| 58 FPS |
| **Luxonis OAK-D Spatial**  | Intel Movidius Myriad X (4 TOPS)    | DepthAI VPU Pipeline       | FP16        | 16.0 ms| 30 FPS |
| **Intel NUC 13 Pro**       | Intel Core i7-1360P + Iris Xe 96 EU | Intel OpenVINO 2024.1      | FP16 / INT8 | 8.2 ms | 85 FPS |
| **OnLogic Karbon 800**     | Intel 12th Gen Core i9 + PCIe Accel | OpenVINO / ONNX / TensorRT | FP16 / INT8 | 5.5 ms | 110 FPS |

---

## 3. Cryptographic & Security Verification Specifications

### 3.1 Transport Layer Security
- **Enforced Protocol:** TLS 1.3 (RFC 8446) with TLS 1.2 fallback.
- **Mandatory Cipher Suites:**
  - `TLS_AES_256_GCM_SHA384`
  - `TLS_CHACHA20_POLY1305_SHA256`
  - `TLS_AES_128_GCM_SHA256`

### 3.2 Model Checksum & Integrity Gate
Every binary model weight package (`.engine`, `.bin`, `.onnx`, `.hef`) uploaded to the registry must include an authentic SHA-256 digest:
$$\text{Digest} = \text{SHA256}(\text{ModelBytes})$$
Upon download at the edge, the agent computes the local hash before swapping runtime execution handles. If:
$$\text{ComputedDigest} \neq \text{ManifestDigest}$$
The payload is immediately deleted, the failure is reported to `/v1/audit`, and the node continues running the prior stable model.

---

## 4. Control Plane Infrastructure Specifications

- **Serverless Compute:** Python 3.12 managed runtime on Vercel Edge / AWS Lambda.
- **Relational Database:** PostgreSQL 15+ with `pg_stat_statements` and SSL mode required (`sslmode=require`).
- **Maximum API Latency Budget:**
  - `/v1/health`: $\le 25\text{ms}$
  - `/v1/status`: $\le 60\text{ms}$
  - `/v1/devices`: $\le 120\text{ms}$ (for 500 nodes)
  - `/v1/agent/heartbeat`: $\le 45\text{ms}$
- **Database Connection Pooling:** Managed pooler (`pgbouncer`) with max 100 pooled connections.
