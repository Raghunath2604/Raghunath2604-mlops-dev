# MLOps.dev — UI/UX Design System Specification

**Document Version:** 2.4.0  
**Design Standard:** Obsidian & Electric Cobalt Precision Engineering  
**Classification:** Enterprise Design System & Component Library  

---

## 1. Design Philosophy & Aesthetic Identity

The MLOps.dev user interface is purpose-built for **deep-tech infrastructure engineers, site reliability leaders, and edge AI operators**. It rejects consumer web clichés and generic "AI-slop" in favor of:

1. **Information Density:** High data density without visual clutter. Metrics, telemetry graphs, and hardware matrix rows must be immediately scannable on 1080p, 1440p, and 4K displays.
2. **Obsidian Contrast:** Deep black and near-black surfaces (`#06090e`, `#0b101b`) that eliminate eye strain during 24/7 industrial NOC monitoring and produce pure zero-emission black on OLED displays.
3. **Electric Cobalt Functional Accent:** Cobalt blue (`#2563eb`, `#3b82f6`) is reserved strictly for interactive states, primary actions, and deployment progress indicators.
4. **Hardware-First Feedback:** Every device status indicator mirrors physical hardware states (steady green for nominal, pulsing amber for staged rollout, red for drift/disconnect).

---

## 2. Design Tokens & Color Architecture

```css
:root {
  /* ── Background Tiers ── */
  --bg-base:          #06090e; /* Deepest Void Canvas */
  --bg-surface:       #0b101b; /* Elevated App Containers & Sidebar */
  --bg-card:          #0f172a; /* Grid Panels & Data Cards */
  --bg-card-hover:    #131c33; /* Interactive Hover Lift */
  
  /* ── Borders & Separators ── */
  --border:           #1a2438; /* Crisp 1px Separation */
  --border-subtle:    #141d2e; /* Internal Table Row Separator */
  --border-focus:     #3b82f6; /* High-Visibility Keyboard Focus Ring */
  
  /* ── Typography Levels ── */
  --text-main:        #f1f5f9; /* Slate 100 — Primary Headers & Values */
  --text-muted:       #94a3b8; /* Slate 400 — Body & Table Content */
  --text-dim:         #64748b; /* Slate 500 — Captions & Metadata */
  
  /* ── Functional Brand & Status Accents ── */
  --cobalt:           #2563eb; /* Primary Interactive */
  --cobalt-bright:    #3b82f6; /* Action Highlights & Chart Stroke */
  --cobalt-dim:       rgba(59, 130, 246, 0.12);
  
  --emerald:          #10b981; /* Nominal Fleet Operation / Online */
  --emerald-dim:      rgba(16, 185, 129, 0.12);
  
  --amber:            #f59e0b; /* Staged Rollout / Degradation / Warning */
  --amber-dim:        rgba(245, 158, 11, 0.12);
  
  --rose:             #ef4444; /* Drift Anomaly / Disconnected Node */
  --rose-dim:         rgba(239, 68, 68, 0.12);
  
  /* ── Typography Families ── */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;

  /* ── Geometry ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

---

## 3. Typography Scale & Hierarchy

All headings enforce negative letter-tracking for a modern, architectural feel:

| Level | Size (rem / px) | Weight | Line Height | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display Hero** | `2.25rem` (36px) | 800 | 1.15 | `-0.03em` | Landing Page Value Proposition |
| **Page Title** | `1.25rem` (20px) | 700 | 1.25 | `-0.02em` | Active Workspace Title (`page-title`) |
| **Section Header** | `0.88rem` (14px) | 700 | 1.35 | `-0.01em` | Panel Card Headers (`panel-title`) |
| **Body Primary** | `0.84rem` (13.5px) | 400 | 1.50 | `normal` | General Telemetry Descriptions |
| **Data Monospace** | `0.78rem` (12.5px) | 500 | 1.40 | `0.02em` | Model Hashes, UUIDs, Latency (ms) |
| **Micro Caption** | `0.70rem` (11px) | 600 | 1.30 | `0.04em` | Column Headers (`th`), Status Badges |

---

## 4. Spacing System & 8px Layout Grid

MLOps.dev enforces an **8px base rhythm** (with 4px half-steps for compact badges):

- `0.25rem` (4px): Chip padding, status dot spacing.
- `0.50rem` (8px): Button icon gaps, card tag gutters.
- `0.75rem` (12px): Table cell padding, sidebar item gaps.
- `1.00rem` (16px): Card internal padding, modal gutter.
- `1.50rem` (24px): Grid column gap, section margin.
- `2.00rem` (32px): Workspace padding on desktop monitors.

---

## 5. Core UI Component Specifications

### 5.1 KPI Metric Card Strip
Located at the top of the dashboard to provide an immediate 3-second fleet health overview:

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ TOTAL FLEET     │ ONLINE NODES    │ DRIFTING / WARN │ OFFLINE / DISCON│
│ 18              │ 18              │ 0               │ 0               │
│ 100% available  │ 1 active canary │ Normal bounds   │ Zero packet loss│
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```
- **Live Pulse Pip:** High-contrast `5px` colored dot with an expanding CSS keyframe wave on active nodes.
- **Micro-Metric Tag:** Monospace status readout indicating cluster availability percentage.

### 5.2 Silicon Platform Pills (`silicon-chip`)
Used across hardware tables and modal selectors to identify edge silicon architectures:
- **Background:** `var(--bg-card)`
- **Border:** `1px solid var(--border)`
- **Font:** `var(--font-mono)`, `font-size: 0.72rem`, `font-weight: 600`
- **Variants:**
  - `Ampere / Jetson`: Crisp white accent (`#ffffff`).
  - `Hailo-8L / RKNN`: Electric Cobalt accent (`#3b82f6`).
  - `Edge TPU`: Emerald accent (`#10b981`).

### 5.3 24-Hour Model Drift Chart (`driftChart`)
Canvas-rendered interactive time-series tracker:
- **Stroke Color:** `#3b82f6` (Electric Cobalt), `borderWidth: 2`
- **Fill Gradient:** `rgba(59, 130, 246, 0.08)` to transparent base.
- **Grid Lines:** `rgba(255, 255, 255, 0.05)` (non-distracting grid).
- **Y-Axis:** Fixed bounds ($0.00$ to $0.60$ KL divergence) with reference safety threshold line at $\tau = 0.20$ and hazard line at $\tau = 0.50$.

### 5.4 Leaflet Geographic Topology Map (`fleetMap`)
Renders the real-world physical locations of enrolled edge nodes:
- **Map Base Layer:** Carto Dark Matter (`dark_all/{z}/{x}/{y}{r}.png`) with zero street clutter.
- **Marker Styling:** SVG `circleMarker` with `radius: 6`, `fillOpacity: 0.85`, colored by node status (Emerald for online, Amber for updating, Rose for offline).
- **Interactive Tooltip:** Dark surface tooltip displaying Node Name, Silicon Architecture, and Active Model on hover/click.

### 5.5 Staged Canary Rollout Modal
Modal dialog allowing engineers to orchestrate staged deployments:
- **Backdrop:** `rgba(0, 0, 0, 0.75)` with `backdrop-filter: blur(8px)`.
- **Silicon Target Grouping:** Select dropdown logically partitioned by:
  - *All Fleets (`all`)*
  - *NVIDIA Jetson Cluster (AGX Orin, Orin Nano, Maxwell)*
  - *Raspberry Pi Fleet (Pi 5, Pi 4, Hailo AI Kit)*
  - *Google Coral Family (Dev Board, USB)*
  - *Rockchip & Amlogic (RK3588, VIM4)*
  - *Industrial PCs (Intel NUC, Advantech, Siemens, OnLogic)*

---

## 6. Responsive Breakpoint Strategy

| Breakpoint | Target Viewports | Layout Adjustments |
| :--- | :--- | :--- |
| **`desktop-xl`** ($\ge 1440\text{px}$) | 4K & Ultrawide Displays | Full 2-column overview (2fr telemetry / 1fr activity feed), Leaflet map expanded to 340px height. |
| **`desktop-md`** ($1024\text{px} - 1439\text{px}$) | Standard Laptops | 2-column grid maintained, horizontal scroll on 8-column hardware tables. |
| **`tablet`** ($768\text{px} - 1023\text{px}$) | iPads & Tablets | Sidebar collapses to icon rail, KPI strip switches to 2x2 grid, map renders full width. |
| **`mobile`** ($< 768\text{px}$) | Mobile Handsets | Single column vertical stack, sticky navigation bar, full-screen overlay modals. |

---

## 7. Accessibility & WCAG 2.1 AA Compliance

1. **Contrast Ratios:** All text elements (`--text-main`, `--text-muted`) maintain a minimum contrast ratio of **6.2:1** against `--bg-base`, surpassing the WCAG AA requirement of 4.5:1.
2. **Keyboard Navigation:** Every button, input, and table row is reachable via standard `Tab` / `Shift+Tab` with a high-contrast focus ring (`outline: 2px solid var(--border-focus)`).
3. **Modal Focus Trap:** Opening a modal automatically focuses the first input field; pressing `Escape` closes the modal and returns focus to the trigger button.
