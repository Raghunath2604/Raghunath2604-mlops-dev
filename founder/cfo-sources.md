# MLOps.dev — CFO Sources & Cost Assumptions

Every input in `founder/numbers.json` is traced to a verifiable quote or benchmark:

## Variable Unit Costs (per active Team subscription / month)
1. **Cloudflare & Edge Bandwidth ($4.50):** Cloudflare Workers Paid Plan ($5/mo baseline + $0.30 per million requests). Covers API edge caching and CDN delivery for 50 devices sending 1-minute telemetry heartbeats.
2. **Managed PostgreSQL & Redis ($6.20):** Render PostgreSQL ($7/mo standard tier pro-rated across active tenants) and Upstash Serverless Redis for real-time drift pub/sub caching.
3. **Stripe Payment Processing ($4.62):** 2.9% + $0.30 standard transaction fee on $149/mo = $4.621.
4. **Telemetry & Log Storage ($3.50):** Cloudflare R2 object storage ($0.015/GB-month, zero egress fees) for historical model binary artifacts and telemetry drift matrices.

## Fixed Monthly Costs
1. **WSGI Backend Infrastructure ($120.00):** Render 2x Starter / Standard instance running Gunicorn Flask application cluster with auto-restart.
2. **Logging & Monitoring ($60.00):** Sentry performance monitoring and BetterStack uptime synthetic probes.
3. **DNS, Domains & Certificates ($25.00):** Cloudflare Pro DNS zone and dedicated SSL/TLS edge certificates.
4. **Tooling & Security Automation ($95.00):** GitHub Team / Actions CI/CD runner compute minutes and automated dependency scanning.

## Startup Capital ($750.00 Total)
- Initial staging environment provisioning: $250.00
- Domain acquisition & trademark filings: $180.00
- Playwright E2E testing runner setup: $120.00
- Launch assets & ProductHunt kit: $200.00
