# MLOps.dev — Application Flow & User Flow Specification

**Document Version:** 2.4.0  
**Target:** Product Managers, Frontend Engineers, System Operators, Solutions Architects  
**Scope:** Complete End-to-End Operational Workflows  

---

## 1. Primary User Journeys

```
[Journey A: The ML Engineer] ──> Pushes Model ──> Differential Patch ──> Canary Rollout
[Journey B: The Hardware Tech] ──> Boots SBC ────> Runs 1-Line Curl ──> Node Appears on Map
[Journey C: The Site Reliability Lead] ──> Monitors KL Drift ──> Auto-Rollback on Hazard
```

---

## 2. Flow 1: Zero-Touch Physical Hardware Provisioning

How a real physical board (e.g. NVIDIA Jetson, Raspberry Pi 5, Intel NUC) connects to the control plane in under 60 seconds:

```mermaid
sequenceDiagram
    autonumber
    actor Tech as Field Technician
    participant Edge as Physical Edge Node
    participant Installer as install.sh Script
    participant API as MLOps.dev Control Plane (/v1)
    participant UI as Fleet Dashboard UI

    Tech->>Edge: Boots device, connects Ethernet or Cellular SIM
    Tech->>Edge: Runs: curl -fsSL https://www.mlopsde.me/install.sh | sudo bash -s -- --token demo
    
    Edge->>Installer: Executes setup script as root
    Installer->>Installer: Inspects /proc/cpuinfo, /proc/meminfo, /sys/class/thermal
    Installer->>Installer: Detects Architecture: aarch64, OS: Linux
    
    Installer->>API: POST /v1/devices/register (Device Name, Arch, OS)
    API-->>Installer: Returns assigned Device ID (e.g. dev-7f8a12bc)
    
    Installer->>Installer: Writes /opt/mlops-agent/agent.py & config.json
    Installer->>Installer: Registers /etc/systemd/system/mlops-agent.service
    Installer->>Installer: Runs: systemctl enable --now mlops-agent.service
    
    Installer->>API: POST /v1/agent/heartbeat (Initial status: online, drift: 0.00)
    API->>UI: SSE Event: fleet_update
    UI-->>Tech: Node appears immediately on Leaflet Map with green indicator pip!
```

---

## 3. Flow 2: Staged Canary Rollout & Health Gating

How an updated computer vision model is staged across 10,000 edge nodes with zero downtime risk:

```mermaid
sequenceDiagram
    autonumber
    actor MLE as Machine Learning Engineer
    participant UI as Control Plane Dashboard
    participant API as Vercel API Gateway
    participant Registry as Model Registry
    participant Fleet20 as 20% Canary Edge Nodes
    participant Fleet80 as 80% Remaining Fleet

    MLE->>UI: Selects "Deploy Model" modal
    UI->>MLE: Displays 17 Silicon Targets (e.g. jetson_orin, rpi5, all)
    MLE->>UI: Enters defect-detector:v1.1, Target: jetson_orin, Strategy: Canary (20%)
    
    UI->>API: POST /v1/deployments
    API->>Registry: Looks up active defect-detector:v1.0 vs v1.1
    API->>API: Randomly selects 20% sample of active nodes
    API->>API: Updates deployment state: stage=1, total_stages=2, status="in_progress"
    
    Fleet20->>API: Periodic 30s Heartbeat
    API-->>Fleet20: Deployment notification received: {model: v1.1, url: /models/v1.1/download}
    Fleet20->>Fleet20: Downloads delta patch, verifies SHA-256
    Fleet20->>Fleet20: Swaps execution slot, runs inference
    
    loop 5-Minute Telemetry Evaluation
        Fleet20->>API: POST /v1/agent/heartbeat (latency: 6.4ms, KL divergence: 0.03, temp: 48°C)
        API->>API: Verifies KL < 0.20 AND error_rate == 0%
    end
    
    API->>API: Health Gate Passed! Promotes to Stage 2 (Remaining 80%)
    Fleet80->>API: Heartbeat pulls model v1.1
    Fleet80->>Fleet80: Swaps to v1.1
    API->>UI: Rollout complete! Status: "completed"
```

---

## 4. Flow 3: Autonomous Drift Incident Rollback

How the system reacts when physical factors (e.g. camera smudged with oil in factory) cause prediction quality degradation:

```mermaid
flowchart TD
    A["Normal Production Inference (Defect Detection)"] --> B["Camera Sensor Degrades / Lighting Shifts"]
    B --> C["Edge Node Collects 1,000 Prediction Confidences"]
    C --> D["On-Device KL Divergence Engine Calculates D_KL(P || Q)"]
    
    D --> E{"D_KL >= 0.50 Threshold?"}
    E -- "No (KL < 0.20)" --> A
    E -- "Warning (0.20 <= KL < 0.50)" --> F["Transmit Drift Warning to Cloud Dashboard"]
    
    E -- "Yes (Hazard Detected!)" --> G["Trip Autonomous Circuit Breaker"]
    G --> H["Immediate Rollback to Prior Stable Model (v1.0) in 300ms"]
    H --> I["Agent reports critical event to /v1/agent/heartbeat (Status: 'drift')"]
    I --> J["Cloud triggers Webhook to Slack / PagerDuty"]
    I --> K["Dashboard highlights node with Red Pulsing Indicator"]
    J --> L["Engineering team inspects camera lens without factory downtime"]
```

---

## 5. Flow 4: Air-Gapped & Intermittent Connectivity Sync

```mermaid
sequenceDiagram
    autonumber
    participant HW as Edge Vision Hardware
    participant Spooler as SQLite Offline Buffer
    participant WAN as Wide Area Network (Cellular)
    participant Cloud as Cloud Control Plane

    HW->>Spooler: Records 1,420 inference telemetry records
    Note over HW,WAN: Factory cellular connection drops completely
    HW->>WAN: Attempts heartbeat (Connection Refused)
    HW->>Spooler: Appends heartbeat payload to queue with UTC timestamp
    Note over HW,WAN: 4 hours later: Cellular link restores
    HW->>WAN: Heartbeat handshake succeeds
    Spooler->>Cloud: Flushes all 1,420 spooled telemetry entries in single gzip batch
    Cloud-->>HW: Acknowledges sync
    Spooler->>Spooler: Clears local buffer
```
