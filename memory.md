# MLOps.dev — Engineering Context & Project Memory

**Document Version:** 2.4.0  
**Purpose:** Living knowledge base, Architecture Decision Records (ADRs), and critical operational gotchas for AI co-partners and human maintainers.  

---

## 1. Production Deployment Inventory

- **Production Domain:** `https://www.mlopsde.me` & `https://mlopsde.me`
- **Dashboard Interface:** `https://www.mlopsde.me/dashboard`
- **Edge Installer:** `https://www.mlopsde.me/install.sh` (or `https://get.mlopsde.me`)
- **API Base URL:** `https://www.mlopsde.me/v1`
- **Vercel Project:** `raghunathareddygr94-9147s-projects/mlops-dev`
- **Active Production Deployment ID:** `dpl_AwBLUcBJh958U8vWir3FCy7PbhPH`

---

## 2. Default Demo Credentials & Seed State

- **Control Plane Email:** `demo@nodepilot.dev` (or `demo@mlops.dev`)
- **Control Plane Password:** `demo1234`
- **API Key Token:** `demo` (SHA-256: `2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea`)
- **Initial Fleet Count:** 17 physical edge hardware devices registered and reporting online status.
- **Initial Models:** `defect-detector:v1.0` in ONNX (7.4MB), TensorRT (12.8MB), and TFLite (4.2MB).

---

## 3. Architecture Decision Records (ADRs)

### ADR-001: ANSI `CURRENT_TIMESTAMP` over SQLite `datetime('now')`
- **Context:** Production runs against managed PostgreSQL, while local development runs against SQLite. SQLite supports `datetime('now')`, but PostgreSQL throws `psycopg2.errors.UndefinedFunction: function datetime(unknown) does not exist`.
- **Decision:** All SQL statements across the codebase use ANSI SQL standard `CURRENT_TIMESTAMP`. This executes natively on both PostgreSQL and SQLite without runtime conversion.

### ADR-002: Dual-Mode Auth (Cookies + Bearer Token)
- **Context:** Browser UI clients require secure HTTP-only cookies (`np_token`) to prevent XSS attacks. Embedded Linux edge agents (curl, Go daemons, Python scripts) require standard `Authorization: Bearer <API_KEY>` headers.
- **Decision:** Middleware `require_auth` in `frontend/api/index.py` inspects both `request.cookies.get('np_token')` and `request.headers.get('Authorization')`. Both grant identical access rights.

### ADR-003: Idempotent Column Migrations in Serverless Handlers
- **Context:** Serverless containers (Vercel) execute without traditional long-running migration workers (e.g. Alembic/Flyway). Schema drift can cause runtime failures when new columns are introduced.
- **Decision:** Database initialization executes `ALTER TABLE [table] ADD COLUMN IF NOT EXISTS ...` on first invocation, guaranteeing backward and forward schema compatibility across deployments.

### ADR-004: Windows AppContainer Sandbox Bypass for Vercel CLI
- **Context:** On Windows development hosts, running commands with `BypassSandbox: false` blocks external binaries (`node.exe`, `npm`, `npx`) due to Windows AppContainer ACL boundaries (`0xC0000022` Access Denied).
- **Decision:** Vercel deployment commands (`npx vercel --prod --yes`) must execute with `BypassSandbox: true`.

---

## 4. Hardware ID & Profiles Reference

| Silicon Profile Key | Device ID | Hardware Class | Default Chipset |
| :--- | :--- | :--- | :--- |
| `jetson_agx_orin` | `hw-jetson-agx-orin-01` | `jetson_orin` | 12-core ARM Cortex-A78AE + 2048-core Ampere |
| `jetson_orin_nano`| `hw-jetson-orin-nano-02`| `jetson_orin` | 6-core ARM Cortex-A78AE + 1024-core Ampere |
| `jetson_nano`     | `hw-jetson-nano-03`     | `jetson_nano` | Quad-core ARM Cortex-A57 + 128-core Maxwell |
| `rpi5`            | `hw-rpi5-edge-04`       | `rpi5`        | Broadcom BCM2712 Quad Cortex-A76 @ 2.4GHz |
| `rpi4`            | `hw-rpi4-telemetry-05`  | `rpi4`        | Broadcom BCM2711 Quad Cortex-A72 @ 1.8GHz |
| `rpi5_hailo`      | `hw-rpi5-hailo-ai-06`   | `rpi5_hailo`  | Broadcom BCM2712 + Hailo-8L 13 TOPS NPU |
| `coral_dev`       | `hw-coral-dev-07`       | `coral`       | NXP i.MX 8M SoC + Google Edge TPU (4 TOPS) |
| `orangepi_5`      | `hw-orangepi5-plus-08`  | `rk3588`      | Rockchip RK3588 (8-core) + 6 TOPS NPU |
| `khadas_vim4`     | `hw-khadas-vim4-09`     | `khadas_vim`  | Amlogic A311D2 + 5.0 TOPS NPU |
| `coral_usb`       | `hw-coral-usb-node-10`  | `coral_usb`   | Google Edge TPU Coprocessor (USB 3.0) |
| `luxonis_oakd`    | `hw-luxonis-oakd-11`    | `luxonis_vpu` | Intel Movidius Myriad X 4 TOPS VPU |
| `intel_ncs2`      | `hw-intel-ncs2-12`      | `intel_ncs2`  | Intel Movidius Myriad X USB VPU |
| `intel_nuc13`     | `hw-intel-nuc13-pro-13` | `intel_nuc`   | Intel Core i7-1360P + Iris Xe Graphics |
| `advantech_uno`   | `hw-advantech-uno-14`   | `advantech`   | Intel Celeron J1900 Fanless DIN-Rail PC |
| `siemens_iot2050` | `hw-siemens-iot2050-15` | `siemens_iot` | Texas Instruments AM6528 Sitara ARM Gateway |
| `onlogic_karbon`  | `hw-onlogic-karbon800-16`|`onlogic`     | Intel 12th Gen Alder Lake Rugged Edge |
| `realsense_d435i` | `hw-realsense-d435i-17` | `realsense`   | Intel RealSense D435i Spatial Vision Node |
