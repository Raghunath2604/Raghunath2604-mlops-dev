# MLOps.dev — System Architecture Specification

**Document Version:** 2.4.0  
**Target Audience:** Staff Software Engineers, Distributed Systems Architects, Investor Due Diligence  
**Architecture Classification:** Distributed Edge-to-Cloud Orchestration & Zero-Trust Control Plane  

---

## 1. High-Level System Architecture

MLOps.dev decouples the cloud control plane from the distributed edge execution plane. Edge nodes operate with high autonomy, maintaining offline inference continuity even during extended wide-area network (WAN) partition events.

```mermaid
flowchart TD
    subgraph CloudControlPlane ["Cloud Control Plane (Vercel / Multi-Region Serverless)"]
        API["REST & SSE API Gateway (/v1)"]
        AUTH["Auth & RBAC Guard (JWT / Cookie / Key Hash)"]
        ORCH["Rollout & Canary Orchestrator"]
        REGISTRY["Edge Model Registry & Diff Engine (bsdiff4)"]
        DB[("Managed Cloud PostgreSQL / Neon / RDS")]
        AUDIT["Immutable Audit Trail & Webhook Dispatcher"]
        
        API --> AUTH
        AUTH --> ORCH
        AUTH --> REGISTRY
        ORCH --> DB
        REGISTRY --> DB
        API --> AUDIT
        AUDIT --> DB
    end

    subgraph PresentationTier ["User & Management Presentation"]
        DASH["Obsidian Fleet Dashboard (HTML5 / Vanilla CSS)"]
        CHARTS["24h Drift KL Canvas Visualizer"]
        LEAFLET["Leaflet Geographic Fleet Topology Map"]
        CLI["MLOps Python & Go CLI SDK"]
        
        DASH --> API
        CLI --> API
        API -. SSE Stream (3s) .-> DASH
        DASH --> CHARTS
        DASH --> LEAFLET
    end

    subgraph EdgeFleetTier ["Physical Edge Fleet (17 Silicon Tiers)"]
        subgraph NodeA ["NVIDIA Jetson AGX Orin"]
            AG_A["MLOps Edge Agent Daemon"]
            TRT["TensorRT 10.0 Inference Engine"]
            DR_A["On-Device KL Drift Engine"]
            CAM_A["Stereo 4K GMSL2 Cameras"]
            CAM_A --> TRT
            TRT --> DR_A
            DR_A --> AG_A
        end

        subgraph NodeB ["Raspberry Pi 5 + Hailo-8L NPU"]
            AG_B["MLOps Edge Agent Daemon"]
            HEF["HailoRT 13 TOPS Runtime"]
            DR_B["TFLite / PSI Drift Tracker"]
            CAM_B["Sony IMX708 Camera Module 3"]
            CAM_B --> HEF
            HEF --> DR_B
            DR_B --> AG_B
        end

        subgraph NodeC ["Google Coral USB / Industrial Gateway"]
            AG_C["MLOps Edge Agent Daemon"]
            TPU["Edge TPU INT8 Runtime"]
            DR_C["Quantized Drift Analyzer"]
            AG_C --> TPU
        end
        
        AG_A == "mTLS 1.3 / Heartbeat (30s)" ==> API
        AG_B == "mTLS 1.3 / Heartbeat (30s)" ==> API
        AG_C == "mTLS 1.3 / Heartbeat (30s)" ==> API
    end
```

---

## 2. Edge Agent Subsystem Architecture

The edge agent runs as a native background daemon managed via systemd (`mlops-agent.service`). It is built in Go for maximum runtime efficiency with a Python fallback runtime for zero-dependency universal installation.

### 2.1 Component Structure

```
/opt/mlops-agent/
├── agent.py                 # Core polling & execution daemon
├── mlops-agent              # Compiled native Go binary (optional)
├── config.json              # Local device configuration & token
├── buffer.db                # SQLite zero-data-loss telemetry queue
└── models/                  # Active and staged binary weights
    ├── defect-detector_v1.0.bin
    └── staged_v1.1.patch
```

### 2.2 Offline Resilience & Zero-Data-Loss Spooling
When network connectivity is severed (e.g. factory outage or mobile AMR tunnel loss):
1. The edge agent continues executing local model inference at full line rate.
2. Inference telemetry, latency metrics, and computed drift scores are written directly to local SQLite `buffer.db`.
3. An exponential backoff retry loop (`10s`, `20s`, `40s`, max `300s`) monitors WAN health.
4. Upon link restoration, all spooled telemetry is batched and flushed to `/v1/agent/heartbeat` in chronological order.

### 2.3 On-Device Hardware HAL (Hardware Abstraction Layer)

The agent dynamically interrogates sysfs and procfs to extract authentic silicon metrics without third-party dependencies:

| Metric | Source Path / Subsystem | Sampling Rate |
| :--- | :--- | :--- |
| **CPU Utilization** | `/proc/loadavg` & `/proc/stat` delta | Every 30s |
| **Memory Footprint** | `/proc/meminfo` (MemTotal - MemAvailable) | Every 30s |
| **Silicon Core Temperature** | `/sys/class/thermal/thermal_zone0/temp` | Every 30s |
| **Jetson GPU Telemetry** | `/sys/devices/gpu.0/load` & Tegra sysfs | Every 30s |
| **NPU Core Utilization** | HailoRT driver / `/dev/hailo0` or Edge TPU libusb | On inference cycle |

---

## 3. Cloud Control Plane & Storage Architecture

### 3.1 Serverless Application Shell (`frontend/api/index.py`)
Built on Flask with production-hardened middleware:
- **Talisman Security Headers:** Strict CSP, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`.
- **CORS Whitelist:** Explicit cross-origin boundary restricted to `https://www.mlopsde.me` and `https://mlopsde.me`.
- **Flask-Limiter:** Global rate limiting (100 req/min default, 5 req/min on `/v1/auth/login` and `/v1/auth/register`).
- **Payload Sanitization:** Hard 16MB maximum payload cutoff to defeat buffer overload and decompression bomb attacks.

### 3.2 Dual-Engine Database Abstraction (PostgreSQL + SQLite)

MLOps.dev features an adaptive database wrapper (`DBWrapper`):
- **Cloud Production:** Connects to PostgreSQL (`DATABASE_URL`) with autocommit, transaction pooling, and `RealDictCursor`.
- **Local Dev / Air-Gapped:** Falls back automatically to SQLite (`mlops.db`) with identical query syntax translation (`?` converted dynamically to `%s`).

#### Relational Schema Architecture

```sql
-- Edge Devices Matrix
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES api_keys(id),
    name TEXT NOT NULL,
    hw_class TEXT NOT NULL,
    os_info TEXT,
    model_name TEXT,
    model_ver TEXT,
    model_tag TEXT,
    status TEXT DEFAULT 'online',
    drift_score REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edge Model Registry
CREATE TABLE models (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES api_keys(id),
    name TEXT NOT NULL,
    tag TEXT NOT NULL,
    format TEXT NOT NULL,        -- 'onnx', 'tensorrt', 'tflite', 'rknn', 'hef'
    variant TEXT DEFAULT 'all',  -- 'jetson_orin', 'coral', 'rpi5', etc.
    size_bytes INTEGER DEFAULT 0,
    sha256 TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, tag, variant)
);

-- Progressive Canary Deployments
CREATE TABLE deployments (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES api_keys(id),
    model_name TEXT NOT NULL,
    model_tag TEXT NOT NULL,
    status TEXT NOT NULL,         -- 'pending', 'in_progress', 'completed', 'aborted'
    stage INTEGER DEFAULT 1,
    total_stages INTEGER DEFAULT 2,
    target TEXT NOT NULL,         -- 'all', 'jetson_orin', or specific device ID
    health_gate TEXT DEFAULT '{}',
    stages TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Model Delivery & Binary Patching Architecture

Pushing full weights (e.g. 100MB–1GB) over industrial cellular networks causes deployment failures. MLOps.dev employs differential binary diffing via **bsdiff4**:

```mermaid
sequenceDiagram
    autonumber
    actor Dev as ML Engineer
    participant Reg as Cloud Model Registry
    participant Diff as Binary Diff Engine
    participant Agent as Edge Agent Daemon
    participant Engine as Local Runtime (TensorRT)

    Dev->>Reg: POST /v1/models (Upload Model v1.1, 85MB)
    Reg->>Diff: Compute Delta(v1.0, v1.1)
    Diff-->>Reg: Generated patch: 3.8MB (95.5% reduction)
    Dev->>Reg: POST /v1/deployments (Target: Jetson Orin, Strategy: Canary 20%)
    
    Reg->>Agent: Heartbeat response triggers rollout notice
    Agent->>Reg: GET /v1/models/.../download?from_tag=v1.0
    Reg-->>Agent: Streams 3.8MB differential delta
    
    Agent->>Agent: Reconstruct v1.1 = bspatch(v1.0, patch)
    Agent->>Agent: Verify SHA-256 Checksum
    Agent->>Engine: Swap model into standby execution slot
    Agent->>Engine: Run test inference & verify latency < 15ms
    Agent->>Reg: POST /v1/agent/heartbeat (Status: online, Model: v1.1)
```

---

## 5. Statistical Drift Detection Math

Edge nodes capture streaming prediction confidence scores $P$ and compare them against the training baseline distribution $Q$ partitioned into $K = 10$ probability quantiles.

$$\mathcal{D}_{\text{KL}}(P \parallel Q) = \sum_{k=1}^{K} P(k) \ln\left(\frac{P(k)}{Q(k)}\right)$$

To ensure numerical stability when a quantile contains zero counts, epsilon smoothing is applied:

$$P'(k) = \frac{P(k) + \epsilon}{\sum_{j} (P(j) + \epsilon)}, \quad \epsilon = 10^{-6}$$

### Canary Circuit Breaker State Machine

```mermaid
stateDiagram-v2
    [*] --> CanaryPhase1: Initiate Rollout (20% Fleet)
    CanaryPhase1 --> EvaluatingHealth: Telemetry Window (5m)
    
    EvaluatingHealth --> PromotedPhase2: KL < 0.20 AND Latency <= SLA
    EvaluatingHealth --> HaltedCanary: 0.20 <= KL < 0.50 (Warn)
    EvaluatingHealth --> AutoRollback: KL >= 0.50 OR Crash Detected
    
    PromotedPhase2 --> FleetActive: Promote to 100% Fleet
    AutoRollback --> PriorStableModel: Rollback in 300ms & Alert Admin
    PriorStableModel --> [*]
    FleetActive --> [*]
```
