# MLOps.dev — Launch Strategy & Run Sheet

## 1. Cheap Real-World Test First (Proof-of-Concept Pilot)
Before spending on paid developer acquisition, execute a 5-device pilot test with an industrial automation partner:
- **Pilot Hardware:** 5 NVIDIA Jetson Orin Nano camera nodes deployed across a logistics sorting facility.
- **Test Metric:** Deploy updated YOLOv8 defect detector model via `client.deploy()`. Artificially inject camera glare to induce drift.
- **Pass Criteria:**
  1. Delta model binary update completes in under 30 seconds over 4G LTE.
  2. Injected glare triggers KL-divergence alert within 3 inference batches.
  3. Agent autonomously reverts to baseline checkpoint in under 300ms without manual intervention.

---

## 2. Launch Countdown (T-14 Days to T-0)
- **T-14 Days:** Finalize and freeze PyPI SDK release (`mlops-dev v0.7.0`). Run 100% green verification suites (6 Pillars, SDK 16/16, Playwright 6/6).
- **T-7 Days:** Pre-launch outreach to 25 edge AI engineers in personal network for early feedback on the 17 Silicon Twins simulator.
- **T-3 Days:** Stage Product Hunt launch kit, YouTube walkthrough video, and Show HN draft post.
- **T-1 Day:** Execute end-to-end dry run: register user account $\to$ generate API key $\to$ curl install on hardware node $\to$ verify telemetry stream.
- **T-0 (Launch Day):**
  - 07:01 UTC: Publish Show HN: *"Show HN: MLOps.dev — We built an edge AI control plane with mathematical drift rollback circuit breakers"*.
  - 08:00 UTC: Launch on Product Hunt.
  - 09:00 UTC: Post technical breakdown on r/MachineLearning and r/embedded.
  - Throughout Day: Founder active in comments addressing technical questions.

---

## 3. First 30 Days Milestones
- **User Registrations:** 250 developers on Starter tier.
- **Connected Edge Silicon:** 500+ physical hardware nodes sending heartbeats.
- **Paid Conversions:** 15 teams converting to $149/mo Team tier ($2,235 MRR).
- **Zero Bricked Hardware:** 100% success rate on automated OTA updates and canaries.
