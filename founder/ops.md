# MLOps.dev — Operations, Systems & Risk Register

## 1. Daily Operating Routines
1. **08:00 UTC — Synthetic Fleet Health Check:** Automated GitHub Actions cron (`health-probe.yml`) executes end-to-end probes against production API endpoints (`/v1/health`, `/v1/status`, `/v1/summary`) and sends alerts if latency exceeds 500ms.
2. **12:00 UTC — Model Registry & Storage Audit:** Verify database integrity and verify that temporary build artifacts are cleaned up.
3. **16:00 UTC — User Onboarding Review:** Check new Starter tier registrations, review access requests in `/admin.html`, and dispatch onboarding assistance.

---

## 2. Infrastructure Suppliers & Stack
- **Edge CDN & WAF:** Cloudflare Enterprise Edge (DDoS protection, SSL/TLS termination, zero-egress R2 artifact caching).
- **Backend Application Cluster:** Render Gunicorn WSGI Python 3.12 cluster with automatic zero-downtime rolling deploys.
- **Relational & Telemetry Database:** PostgreSQL 16 with automatic connection pooling and local SQLite air-gapped device store.
- **Email & Notification Service:** Resend API integration for one-time verification tokens and drift incident dispatches.

---

## 3. Operational Risk Register

| Risk | Severity | Probability | Mitigation Strategy |
|---|:---:|:---:|---|
| **Intermittent Edge Disconnects** | High | High | Agent uses SQLite local append-only journal; buffers telemetry offline and flushes idempotently on reconnection. |
| **Cellular OTA Download Failure** | High | Medium | Chunked HTTP downloads with SHA-256 block verification; agent verifies full file before executing model swap. |
| **Silent Model Performance Degradation** | High | High | Mathematical KL-divergence drift engine detects shift in input tensor distribution and trips autonomous rollback in $<300$ms. |
| **Multi-Tenant Data Bleed** | Critical | Low | Strict server-side RBAC enforced at the database query layer (`WHERE owner_id = g.user_id`). |
| **Cloud Control Plane Outage** | Medium | Low | Edge agent is completely autonomous; existing deployed models continue running locally without cloud dependence. |
