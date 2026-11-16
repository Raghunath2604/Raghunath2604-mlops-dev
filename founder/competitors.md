# MLOps.dev — Competitive Landscape Analysis

## 1. Competitor Table

| Competitor | Type | Comparable Item Price | Core Product | Positioning Line | Rating |
|---|---|---|---|---|---|
| **BalenaCloud** | Direct | $299/mo (Production 50 devices) | Linux container orchestration for embedded | "A complete set of tools to build, deploy, and manage IoT fleets" | 4.6 (185) |
| **AWS IoT Greengrass** | Direct | $0.16/dev/mo + IoT Core + S3 + Bandwidth | AWS IoT runtime & Lambda/component runner | "Build intelligent IoT devices faster" | 4.1 (280) |
| **Azure IoT Edge** | Direct | Free agent + IoT Hub ($25–$500/mo) | Azure IoT container module execution | "Deploy cloud intelligence directly on IoT edge devices" | 4.0 (210) |
| **Edge Impulse** | Direct | Custom Enterprise ($2,500+/mo) | Embedded ML model building & firmware flashing | "The industry-leading edge AI platform" | 4.5 (140) |
| **Weights & Biases** | Indirect | $50/user/mo | Cloud model registry & experiment tracking | "The developer-first MLOps platform" | 4.6 (320) |
| **In-House SSH / Ansible** | Substitute | $0 (Hidden: $8k+/mo dev time + downtime) | DIY Bash scripts, SCP/rsync, and cron jobs | "We just scp model weights over VPN" | 2.1 (95) |

---

## 2. Price Range (50 Devices Fleet)
- **Lowest:** $0 (In-house DIY scripts, excluding human engineering cost)
- **Median:** $199/month (Balena / Azure IoT Hub mid-tier)
- **Highest:** $2,500+/month (Edge Impulse Enterprise tier)
- **MLOps.dev Plan:** **$149/month** for 50 devices ($2.98/device/mo) $\to$ Highly competitive sweet spot.

---

## 3. Positioning Map

```
                     HIGH AI/MODEL-SPECIFIC CAPABILITIES (Drift, Canaries, TensorRT)
                                              ▲
                                              │               [ MLOps.dev ]
                                              │      (Air-gapped, delta weights,
                                              │       KL-drift circuit breaker)
                  [ Edge Impulse ]            │
             (Microcontroller focus)          │
                                              │
    LOW CLOUD DEPENDENCY                      │                      HIGH CLOUD LOCK-IN
    ◄─────────────────────────────────────────┼────────────────────────────────────────►
     (Air-gapped, offline-first)              │                      (Requires AWS/Azure)
                                              │
           [ DIY SSH / Ansible ]              │         [ AWS Greengrass ]
           (High bricking risk)               │         [ Azure IoT Edge ]
                                              │         (Heavyweight Docker runtime)
                                              │   [ BalenaCloud ]
                                              ▼
                        GENERIC LINUX / CONTAINER FLEET MANAGEMENT
```

---

## 4. Ranked Customer Complaints on Existing Solutions
1. **Multi-Gigabyte Container Deployments on Cellular IoT:**
   - *Complaint:* "Pulling 2GB Docker images on 4G cellular modems in the field blows past data budgets and fails mid-download." ([Balena Forums](https://forums.balena.io))
2. **Zero In-Field Drift Detection:**
   - *Complaint:* "Greengrass told us our edge module was 'Healthy', but the computer vision model had degraded to 40% accuracy due to camera glare. We produced 3 hours of scrap before someone noticed manually." ([Reddit r/MachineLearning](https://reddit.com/r/MachineLearning))
3. **Complex Enterprise Cloud Lock-in & Setup Complexity:**
   - *Complaint:* "Setting up AWS Greengrass V2 with certificates, IAM roles, and IoT Core took our team 3 weeks of DevOps just to run one Python inference script." ([Hacker News](https://news.ycombinator.com))

---

## 5. The Gap MLOps.dev Owns
**The Edge AI Drift & Delta Gap:**  
Balena and Greengrass are built for generic Linux containers, not neural networks. They do not understand ONNX/TensorRT, they do not compute input tensor divergence, and they cannot autonomously rollback when accuracy drops. MLOps.dev fills this exact gap: **Lightweight delta binary updates (10–50x smaller than Docker pulls) + Real mathematical KL-divergence drift circuit breakers (<300ms autonomous rollback).**

---

## 6. Competitive Threat
- **Who could copy fastest:** BalenaCloud (if they add an AI-specific model registry plugin) or Weights & Biases (if they build an embedded device daemon).
- **Defense:** Deep silicon-level compilation integrations (Jetson Orin DLA/TensorRT, Coral EdgeTPU compiler) and sticky historical drift telemetry matrices that make switching friction high.
