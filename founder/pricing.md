# MLOps.dev — Van Westendorp Pricing Sensitivity Analysis

## 1. Quantitative Price Sensitivity Meter (PSM)

Based on 20 panel respondent price sensitivity responses:

| Metric | Computed Value | Strategic Meaning |
|---|---|---|
| **Point of Marginal Cheapness (PMC)** | **$50.78** | Below this, enterprise buyers suspect low quality or lack of security. |
| **Optimal Price Point (OPP)** | **$50.78** | Equal proportion of "too cheap" vs "too expensive". |
| **Indifference Price Point (IPP)** | **$150.00** | Equal proportion of "bargain" vs "expensive" — highest volume equilibrium. |
| **Point of Marginal Expensiveness (PME)** | **$399.26** | Above this, resistance accelerates sharply for mid-market teams. |

- **Acceptable Price Band:** **$50.78 — $399.26 / month**
- **Median Answers:** Too cheap: $39.00 · Bargain: $120.00 · Getting expensive: $299.00 · Too expensive: $599.00.

---

## 2. Pricing Architecture & Recommendation

The planned **$149.00/month** for the Team tier sits almost exactly on the **Indifference Price Point ($150.00)**, capturing the sweet spot where buyers perceive high commercial value without triggering procurement friction:

1. **Starter ($0/mo):** Free for up to 10 edge nodes. Drives self-serve bottom-up adoption.
2. **Team / Pro ($149/mo):** Up to 50 edge nodes ($2.98/node/mo). Includes automated canary deployments, KL-divergence drift circuit breakers, and Slack/webhook alerts.
3. **Enterprise ($999/mo or $12,000/yr):** Unlimited fleet nodes, air-gapped on-premise control plane, private VPC, 99.9% uptime SLA, and dedicated engineering onboarding. (Directly flips the 3 panel "no" votes who required strict air-gapped on-premise execution).
