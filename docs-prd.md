# MLOps.dev — Product Requirements Document (PRD)

**Document Version:** 2.4.0  
**Status:** Approved for Investment & Enterprise Evaluation (YC / Seed Round)  
**Author:** Raghunathareddy GR & Engineering Team  
**Confidentiality:** Enterprise Tier / Investor Deck Reference  

---

## 1. Executive Summary & Vision

**MLOps.dev** is the world’s first purpose-built, zero-trust edge AI orchestration and continuous model delivery platform. While hyperscalers (AWS SageMaker, Google Vertex AI) dominate cloud training, they fundamentally fail at the physical edge: intermittent connectivity, heterogeneous silicon (NVIDIA Ampere, ARM Cortex, Edge TPU, RKNN, Hailo NPU), strict thermal boundaries (sub-15W), and air-gapped security policies.

MLOps.dev bridges this multi-billion dollar gap by delivering:
1. **Sub-second edge model rollouts** with differential binary patching (bsdiff4 reducing 100MB models to 4MB deltas).
2. **Zero-downtime canary deployments** gated by real-time hardware telemetry and health checks.
3. **On-device statistical drift detection** via Kullback-Leibler (KL) divergence and Population Stability Index (PSI) computed directly on the edge node.
4. **Universal silicon support across 17 tier-1 edge platforms** spanning embedded SBCs, USB AI accelerators, industrial box PCs, and spatial AI cameras.

---

## 2. Market Problem & Opportunity

| Enterprise Pain Point | Current Workarounds | MLOps.dev Solution |
| :--- | :--- | :--- |
| **Silicon Fragmentation** | Engineers write custom Dockerfiles & compile script variants for every chip. | **Unified Hardware Abstraction Layer (HAL)**: Automatic runtime routing (.engine for Jetson, .rknn for Rockchip, .hef for Hailo, .tflite for Coral). |
| **Bandwidth & Connectivity** | Pushing full 500MB weights over cellular (4G/LTE) fails or incurs massive roaming costs. | **Differential Binary Sync**: Byte-level delta compression pushes only modified layers (92% bandwidth reduction). |
| **Silent Edge Failure** | Models drift due to factory lighting shifts, camera lens smudges, or domain drift with zero alerts. | **Edge-Side KL Drift Gate**: Instant rollbacks triggered within 300ms if prediction distribution diverges beyond threshold ($\tau \ge 0.4$). |
| **Zero-Trust & Compliance** | Edge devices on factory floors are physically accessible and easily compromised. | **Hardware Fingerprinting & Ephemeral JWTs**: TLS 1.3 mTLS, AES-256 encrypted model weights at rest, and tamper-evident audit logs. |

---

## 3. User Personas

### Persona A: The Edge AI Tech Lead (Enterprise Customer)
- **Role:** Leads computer vision deployment across 5,000 smart factory cameras.
- **Goal:** Deploy new defect detection models weekly without sending field technicians to physically re-flash SD cards.
- **Needs:** Canary rollout percentage controls, automated rollback if inference latency exceeds 25ms, SOC2 audit trail.

### Persona B: Autonomous Robotics Engineer (Robotics / AMRs)
- **Role:** Builds vision-guided warehouse mobile robots powered by NVIDIA Jetson Orin.
- **Goal:** Prevent robot crashes caused by camera sensor degradation or out-of-distribution obstacles.
- **Needs:** On-chip drift monitoring with sub-10ms latency overhead and zero cloud dependency during active warehouse missions.

### Persona C: Venture Capital Partner / YC Assessor
- **Role:** Evaluating infrastructure software scalability, defensibility, and developer adoption.
- **Goal:** Confirm technical feasibility, customer friction elimination (1-line install), and clear enterprise gross margins (>80%).

---

## 4. Supported Silicon Hardware Matrix (17 Platforms)

MLOps.dev features native binary toolchains and telemetry agents for:

1. **NVIDIA Jetson AGX Orin (64GB)** — 2048-core Ampere GPU, TensorRT 10.0, DeepStream
2. **NVIDIA Jetson Orin Nano (8GB)** — 1024-core Ampere GPU, sub-15W industrial AMR standard
3. **NVIDIA Jetson Nano (4GB/2GB)** — Quad-core A57 + 128-core Maxwell GPU
4. **Raspberry Pi 5 (8GB ARM64)** — Broadcom BCM2712 Quad Cortex-A76, ONNX Runtime
5. **Raspberry Pi 4 Model B (4GB)** — Broadcom BCM2711, TFLite Edge Runtime
6. **Raspberry Pi AI Kit** — Raspberry Pi 5 + Hailo-8L 13 TOPS M.2 NPU
7. **Google Coral Dev Board** — NXP i.MX 8M SoC + Google Edge TPU (4 TOPS INT8)
8. **Google Coral USB Accelerator** — Coprocessor via USB 3.0 on x86/ARM host
9. **Orange Pi 5 Plus** — Rockchip RK3588 (8-core) + 6 TOPS triple-core RKNN NPU
10. **Khadas VIM4** — Amlogic A311D2 + 5.0 TOPS NPU with OpenVINO / TFLite
11. **Luxonis OAK-D Spatial AI Camera** — Intel Myriad X VPU + Stereo Depth Vision
12. **Intel Neural Compute Stick 2 (NCS2)** — Intel Movidius Myriad X USB VPU
13. **Intel NUC 13 Pro** — Intel Core i7-1360P + Iris Xe Graphics (OpenVINO)
14. **Advantech UNO-2271G** — DIN-Rail Industrial Fanless Box PC
15. **Siemens SIMATIC IOT2050** — Dual-core ARM TI Sitara AM6528 Gateway
16. **OnLogic Karbon 800** — Intel 12th Gen Alder Lake Heavy Rugged Edge Server
17. **Intel RealSense D435i** — Spatial Stereo Depth & Active IR Vision Node

---

## 5. Key Functional Modules

### 5.1 Zero-Touch Edge Provisioning
- **One-Line Bootstrap:** `curl -fsSL https://www.mlopsde.me/install.sh | sudo bash -s -- --token <API_KEY>`
- **Automatic Daemon Setup:** Configures `/etc/systemd/system/mlops-agent.service` with automatic restart, backoff retry, and log rotation.
- **Hardware Telemetry Extraction:** Reads directly from `/sys/class/thermal`, `/proc/meminfo`, `/proc/loadavg`, and GPU sysfs (e.g. Tegra sysfs on Jetson).

### 5.2 Dynamic Canary Delivery Engine
- **Target Selection:** Global (`all`), silicon architecture (`hw_class`), or specific cluster tag.
- **Staged Rollout Strategies:**
  - `Canary (20% -> 100%)`: Deploys to a random 20% sample of nodes, monitors inference latency and error rates for 5 minutes, then automatically promotes to remaining 80%.
  - `Blue/Green`: Parallel deployment on dual runtime slots with instant traffic switch.
  - `Direct (100%)`: Immediate parallel rollout for critical safety patches.
- **Health Gating:** Rollback triggered automatically if device temperature > 75°C, latency > SLA, or crash loop detected.

### 5.3 Edge Model Registry
- **Multi-Format Storage:** Models cataloged with checksums (SHA-256), size bytes, parameter counts, and compiled engine artifacts (`.engine`, `.onnx`, `.tflite`, `.hef`, `.rknn`).
- **Differential Patch Generation:** Compares version $N$ and $N+1$ using binary diffing; downloads only delta patches onto active devices.

### 5.4 Statistical Drift Telemetry
- **On-Device Divergence Calculator:** Calculates $D_{KL}(P \parallel Q) = \sum_{x \in \mathcal{X}} P(x) \log\left(\frac{P(x)}{Q(x)}\right)$ over sliding windows of 1,000 inferences.
- **Three-Tier Alerting:**
  - `OK` ($KL < 0.20$): Nominal operation.
  - `WARNING` ($0.20 \le KL < 0.50$): Notification dispatched to dashboard and audit log.
  - `DANGER / DRIFT` ($KL \ge 0.50$): Canary halted, automatic rollback initiated, webhook fired.

### 5.5 Enterprise Security & RBAC
- **Token Hierarchy:** Root Admin, Team Member, Edge Node Device Token.
- **Secure Transport:** TLS 1.3, strict CORS whitelisting, HTTP-only secure cookies (`Lax`/`Strict`), rate limiting via Redis/in-memory limiter.
- **Immutable Audit Trail:** Every configuration change, model promotion, device retirement, and security event logged with UTC timestamp.

---

## 6. Success Metrics & Key Performance Indicators (KPIs)

| Metric | Target | Measurement Method |
| :--- | :--- | :--- |
| **Agent Binary Size** | $< 12 \text{ MB}$ (Go) / Sub-100KB (Python installer) | `ls -lh /opt/mlops-agent` |
| **Agent CPU Overhead** | $< 1.5\%$ on single ARM Cortex-A53 | Monitored via top/systemd cgroups |
| **Agent RAM Footprint** | $< 25 \text{ MB}$ RSS | Monitored via `/proc/[pid]/status` |
| **Heartbeat Interval** | 30s heartbeat, 3s SSE dashboard push | API server logs & WebSocket/SSE telemetry |
| **Rollout Propagation** | $< 5\text{s}$ to trigger download across 10,000 nodes | Telemetry audit events |
| **Uptime SLA** | 99.95% Availability | Vercel Serverless + Multi-Region Managed DB |

---

## 7. Go-To-Market & Monetization

1. **Free / Developer Tier:** Up to 5 devices, community Discord support, public model registry.
2. **Pro Tier ($49/month):** Up to 25 devices, automated canary deployments, 7-day telemetry retention.
3. **Enterprise Tier ($499+/month + $5/node):** Unlimited devices, SLA 99.95%, on-prem air-gapped control plane options, custom NPU compiler integration, SOC2 type II compliance.
