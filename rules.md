# MLOps.dev — Engineering Standards & Operational Rules

**Document Version:** 2.4.0  
**Mandate Level:** STRICT / ZERO TOLERANCE  
**Applies To:** Core Maintainers, Contributors, Subagents, and Automation Workflows  

---

## 1. Zero-Slop Design & UI Directives

Any frontend changes submitted to MLOps.dev must strictly comply with our institutional **Obsidian & Electric Cobalt** design standard.

### Prohibited Anti-Patterns (The "AI-Slop" Checklist)
1. **NO Neon Gradients:** Never use purple-to-blue (`linear-gradient(135deg, #a855f7, #3b82f6)`) or rainbow borders.
2. **NO Emoji Headers:** Headings must read as professional engineering terminology (e.g. `Canary Rollout Orchestration`, NOT `🚀 Supercharge Your Rollouts! ✨`).
3. **NO Glassmorphism Traps:** Avoid muddy frosted glass overlays (`backdrop-filter: blur(20px)`) that degrade FPS and render illegibly on low-contrast monitors.
4. **NO Cursor Hijacking:** Never implement cursor-following glow beams, mouse trailers, or physics-based inertia scrolling.
5. **NO Unclosed HTML Tags:** Semantic HTML5 only. Every container (`div`, `section`, `main`) must be closed properly with no orphan nesting bugs.
6. **NO Landing Page Footers in Dashboard:** The dashboard shell is a full-viewport application workspace (`overflow: hidden; height: 100vh`). Never append 4-column marketing links inside the telemetry view.

### Approved Color Palette & Token System
```css
:root {
  --bg-base:        #06090e; /* Deepest Void Obsidian */
  --bg-surface:     #0b101b; /* Elevated Application Panels */
  --bg-card:        #0f172a; /* Data Grid Cards */
  --border:         #1a2438; /* Crisp 1px Separation */
  --border-subtle:  #141d2e;
  
  --cobalt-bright:  #3b82f6; /* Action Highlights */
  --cobalt-dim:     rgba(59, 130, 246, 0.12);
  --emerald:        #10b981; /* Healthy Edge Nodes / Online */
  --emerald-dim:    rgba(16, 185, 129, 0.12);
  --amber:          #f59e0b; /* Staged Rollout / Degradation */
  --amber-dim:      rgba(245, 158, 11, 0.12);
  --rose:           #ef4444; /* Drift Detected / Disconnected */
  --rose-dim:       rgba(239, 68, 68, 0.12);
  
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
}
```

---

## 2. Edge Hardware & Agent Constraints

1. **Memory Budget:** The edge daemon must never consume more than **30 MB RSS**. Test allocations using `tracemalloc` (Python) or `pprof` (Go).
2. **CPU Cap:** Background telemetry sampling must never exceed **1.5% CPU** on a single ARM Cortex-A53 core.
3. **Graceful Signal Handling:** All agents must intercept `SIGTERM` and `SIGINT`, flush the local SQLite buffer, and gracefully release device hardware locks within **500ms**.
4. **Offline First:** Network calls (`urllib`, `requests`, `net/http`) must have explicit timeouts ($\le 5\text{s}$). If a call fails, enqueue to local SQLite buffer; **never crash the daemon**.
5. **No Sudo inside Loops:** Root privileges are strictly reserved for initial installation (`systemd` unit setup). The background daemon must drop privileges or execute non-privileged telemetry reads.

---

## 3. Security, Secrets & Zero-Trust Policy

1. **Zero Hardcoded Credentials:** Never hardcode API keys, database passwords, or JWT secrets in client code, tests, or documentation.
2. **Environment Variable Precedence:**
   - Production secrets: Injected via Vercel Environment Variables.
   - Local development: `.env.local` (always gitignored via `.gitignore`).
3. **SQL Injection Elimination:** 
   - Every database query must use parameterized queries (`?` in SQLite, `%s` in PostgreSQL).
   - Dynamic table names or column names must be checked against hardcoded whitelists.
4. **Rate Limiting & Abuse Defense:**
   - Authentication routes (`/v1/auth/login`, `/v1/auth/register`) capped at **5 requests per minute**.
   - Cloudflare Turnstile CAPTCHA mandatory on production public registration endpoints.
5. **Token Storage:**
   - Session cookies must specify: `HttpOnly; Secure; SameSite=Lax; Max-Age=604800`.
   - API keys stored exclusively as SHA-256 digests (`key_hash`). Plaintext keys are never stored in the database.

---

## 4. Cross-Engine Database Schema Rules

Because MLOps.dev supports both **PostgreSQL** (production cloud) and **SQLite** (local development and air-gapped appliances), SQL statements must adhere to ANSI-standard compatibility:

1. **Standard Timestamps:**
   - **CORRECT:** `CURRENT_TIMESTAMP`
   - **PROHIBITED:** `datetime('now')` (SQLite only) or `NOW()` (PostgreSQL only).
2. **Idempotent Column Migrations:**
   - Every column addition must specify `ALTER TABLE [table] ADD COLUMN IF NOT EXISTS [column] [type] DEFAULT [val];`.
3. **Primary Keys:**
   - All primary keys must be deterministic strings (e.g. `dev_...`, `dep_...`, `m_...`, `usr_...`). Auto-increment integers are strictly prohibited across distributed nodes.
4. **Transaction Integrity:**
   - Operations touching both device state and audit logs must execute within an explicit transaction context (`commit=True`).

---

## 5. CI/CD & Deployment Directives

1. **Local Pre-Flight Checks:** Run test suite (`python test_login.py`, `python test_rbac.py`) before pushing code.
2. **Vercel Sandbox Bypass:** On Windows host environments, commands executing Node.js binaries (`npx vercel --prod`) must specify `BypassSandbox: true` due to Windows AppContainer ACL boundaries.
3. **Smoke Testing Post-Deploy:** Every production promotion must execute an automated curl health check (`curl -s https://www.mlopsde.me/v1/health`) before declaring complete.
