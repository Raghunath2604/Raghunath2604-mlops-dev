"""
mlops — command-line interface for MLOps.dev

Installation:
    pip install mlops-dev
    mlops --help

Authentication:
    export MLOPS_API_KEY=mlops_live_xxxx
    # or: mlops login

Commands:
    mlops status                       Fleet health summary
    mlops devices list                 List all devices
    mlops devices get <id>             Get one device
    mlops devices logs <id>            Stream device event log
    mlops devices config <id> [opts]   Update device agent config
    mlops models list                  List registered models
    mlops models push <file> [opts]    Push a model to the registry
    mlops models delete <name> <tag>   Delete a model version
    mlops deploy <model:tag> [opts]    Deploy model to fleet
    mlops rollback [opts]              Roll back fleet or device
    mlops drift report                 Fleet-wide drift summary
    mlops drift alerts                 Active drift alerts
    mlops drift reset <device_id>      Reset drift baseline
    mlops audit [opts]                 Export audit log
    mlops health                       API health check
"""

import os
import sys
import json
import argparse
from typing import Optional


def get_client(api_key: Optional[str] = None, base_url: Optional[str] = None):
    """Build a Client from CLI args or env."""
    from mlops_dev import Client
    from mlops_dev.http import DEFAULT_BASE
    return Client(
        api_key=api_key or os.environ.get("MLOPS_API_KEY", ""),
        base_url=base_url or os.environ.get("MLOPS_API_URL", DEFAULT_BASE),
    )


def fmt_json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def ok(msg: str):
    print(f"\033[32m✓\033[0m  {msg}")


def err(msg: str):
    print(f"\033[31m✗\033[0m  {msg}", file=sys.stderr)


def warn(msg: str):
    print(f"\033[33m!\033[0m  {msg}")


def table(headers, rows, widths=None):
    """Print a simple fixed-width table."""
    if widths is None:
        widths = [max(len(str(r[i])) for r in ([headers] + list(rows)))
                  for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    sep = "  ".join("─" * w for w in widths)
    print("  " + fmt.format(*headers))
    print("  " + sep)
    for row in rows:
        print("  " + fmt.format(*[str(x) for x in row]))


# ── COMMANDS ──────────────────────────────────────────────────────

def cmd_status(args):
    client = get_client(args.api_key, args.url)
    s = client.status()
    print("\n  MLOps.dev Fleet Status")
    print("  " + "─"*40)
    print(f"  Total devices:       {s.get('total_devices', '—')}")
    print(f"  Online:              {s.get('online', '—')}")
    print(f"  Offline:             {s.get('offline', '—')}")
    print(f"  Drifting:            {s.get('drifting', '—')}")
    print(f"  Active deployments:  {s.get('active_deployments', '—')}")
    print(f"  API version:         {s.get('api_version', '—')}")
    print()


def cmd_devices_list(args):
    client = get_client(args.api_key, args.url)
    devices = client.devices.list(
        status=getattr(args, 'status', None),
        hw_class=getattr(args, 'hw_class', None),
        limit=getattr(args, 'limit', 100),
    )
    if not devices:
        warn("No devices found.")
        return
    rows = []
    for d in devices:
        drift_col = f"{d.drift_score:.3f}"
        if d.drift_score >= 0.7:
            drift_col = f"\033[31m{drift_col}\033[0m"
        elif d.drift_score >= 0.4:
            drift_col = f"\033[33m{drift_col}\033[0m"
        status_col = d.status.value
        if d.status.value == "online":
            status_col = f"\033[32m{status_col}\033[0m"
        elif d.status.value in ("drift", "error"):
            status_col = f"\033[31m{status_col}\033[0m"
        rows.append([d.id, status_col, d.hw_class, d.model_ref, drift_col, f"{d.latency_ms:.1f}ms"])
    print()
    table(
        ["ID", "STATUS", "HW CLASS", "MODEL", "DRIFT", "LATENCY"],
        rows,
        [24, 10, 14, 24, 8, 10],
    )
    print(f"\n  {len(devices)} device(s)\n")


def cmd_devices_get(args):
    client = get_client(args.api_key, args.url)
    d = client.devices.get(args.device_id)
    print(f"\n  Device: {d.id}")
    print("  " + "─" * 40)
    print(f"  Name:           {d.name}")
    print(f"  Status:         {d.status.value}")
    print(f"  Hardware:       {d.hw_class}  ({d.arch})")
    print(f"  OS:             {d.os}")
    print(f"  RAM:            {d.ram_mb}MB")
    print(f"  CPU:            {d.cpu_pct:.1f}%")
    print(f"  Temp:           {d.temp_c:.1f}°C")
    print(f"  Active model:   {d.model_ref}  ({d.model_format})")
    print(f"  Drift score:    {d.drift_score:.3f}  ({d.drift_level})")
    print(f"  Latency:        {d.latency_ms:.1f}ms")
    print(f"  Agent version:  {d.agent_version}")
    print(f"  Last seen:      {d.last_seen}")
    print(f"  Uptime:         {d.uptime_s}s")
    if d.metadata:
        print(f"  Metadata:")
        for k, v in d.metadata.items():
            print(f"    {k}: {v}")
    print()


def cmd_devices_logs(args):
    client = get_client(args.api_key, args.url)
    logs = client.devices.logs(
        args.device_id,
        limit=getattr(args, 'limit', 50),
        level=getattr(args, 'level', None),
    )
    if not logs:
        warn(f"No logs found for {args.device_id}")
        return
    print(f"\n  Logs for {args.device_id}\n")
    for entry in logs:
        lvl = entry.get('level', 'info').upper()
        col = {"INFO": "\033[36m", "WARN": "\033[33m", "ERROR": "\033[31m"}.get(lvl, "")
        reset = "\033[0m" if col else ""
        print(f"  {entry.get('ts','')}  {col}[{lvl}]{reset}  {entry.get('msg','')}")
    print()


def cmd_models_list(args):
    client = get_client(args.api_key, args.url)
    models = client.models.list()
    if not models:
        warn("No models in registry.")
        return
    rows = []
    for m in models:
        for v in m.versions:
            rows.append([m.name, v.tag, v.format, v.variant, f"{v.size_mb}MB", str(v.active_devices)])
    print()
    table(
        ["NAME", "TAG", "FORMAT", "VARIANT", "SIZE", "ACTIVE DEVICES"],
        rows,
        [20, 10, 10, 14, 8, 14],
    )
    print(f"\n  {sum(len(m.versions) for m in models)} version(s) across {len(models)} model(s)\n")


def cmd_models_push(args):
    client = get_client(args.api_key, args.url)
    print(f"  Pushing {args.file} → {args.name}:{args.tag} ...")

    meta = {}
    if hasattr(args, 'metadata') and args.metadata:
        for kv in args.metadata:
            if "=" in kv:
                k, v = kv.split("=", 1)
                meta[k.strip()] = v.strip()

    v = client.models.push(
        path=args.file,
        name=args.name,
        tag=args.tag,
        format=getattr(args, 'format', None),
        variant=getattr(args, 'variant', None),
        metadata=meta if meta else None,
    )
    ok(f"Pushed  {v.name}:{v.tag}  {v.format}  {v.size_mb}MB")
    print(f"     SHA-256:  {v.sha256[:16]}...")
    print(f"     ID:       {v.id}")
    print()


def cmd_models_delete(args):
    client = get_client(args.api_key, args.url)
    if not getattr(args, 'yes', False):
        confirm = input(f"  Delete {args.name}:{args.tag}? [y/N] ").strip().lower()
        if confirm != "y":
            print("  Cancelled.")
            return
    client.models.delete(args.name, args.tag)
    ok(f"Deleted {args.name}:{args.tag}")
    print()


def cmd_deploy(args):
    import time
    client = get_client(args.api_key, args.url)

    stages = None
    if hasattr(args, 'stages') and args.stages:
        stages = []
        for s in args.stages:
            parts = dict(p.split("=") for p in s.split(","))
            if "count" in parts: parts["count"] = int(parts["count"])
            if "pct"   in parts: parts["pct"]   = int(parts["pct"])
            stages.append(parts)

    health_gate = None
    if hasattr(args, 'health_gate') and args.health_gate:
        health_gate = {}
        for hg in args.health_gate:
            k, v = hg.split("=")
            health_gate[k.strip()] = float(v.strip())

    print(f"\n  Deploying {args.model} → {args.target} ...")
    dep = client.deploy(
        model=args.model,
        target=args.target,
        stages=stages,
        health_gate=health_gate,
        stage_interval=getattr(args, 'stage_interval', None),
    )
    print(f"  Deployment {dep.id}  (stage 1/{dep.total_stages})")

    if getattr(args, 'wait', False) or not getattr(args, 'no_wait', False):
        def on_stage(stage, status, d):
            icon = "✓" if status == "passed" else "→" if status == "running" else "✗"
            print(f"  {icon}  Stage {stage}/{d.total_stages}: {status}")

        try:
            dep.wait(
                poll_interval=float(getattr(args, 'poll', 5)),
                timeout=float(getattr(args, 'timeout', 600)),
                on_stage=on_stage,
            )
        except TimeoutError as e:
            err(str(e))
            sys.exit(1)

        if dep.status == "completed":
            ok(f"Deployment completed  ({dep.model_ref}  →  {dep.target})")
        elif dep.status == "failed":
            err(f"Deployment failed at stage {dep.stage}/{dep.total_stages}")
            print("     Run: mlops rollback to revert affected devices")
            sys.exit(1)
        elif dep.status == "rolled_back":
            warn(f"Deployment rolled back automatically (health gate)")
    else:
        print(f"  Running in background. Check: mlops deployments get {dep.id}")
    print()


def cmd_rollback(args):
    client = get_client(args.api_key, args.url)
    device_id = getattr(args, 'device', None)
    to_version = getattr(args, 'to', None)

    if device_id:
        print(f"\n  Rolling back {device_id}{' → ' + to_version if to_version else ''} ...")
    else:
        print(f"\n  Rolling back entire fleet{' → ' + to_version if to_version else ''} ...")

    result = client.rollback(device_id=device_id, to=to_version)
    ok(f"Rollback queued — {result.get('affected_devices', '?')} device(s)")
    print()


def cmd_drift_report(args):
    client = get_client(args.api_key, args.url)
    r = client.drift.report()
    print(f"\n  Drift Report")
    print("  " + "─" * 40)
    print(f"  Total devices:  {r.total_devices}")
    print(f"  Healthy:        {r.healthy}  ({r.pct_healthy}%)")
    print(f"  Warning:        {r.warning}")
    print(f"  Drifting:       {r.drifting}")
    print(f"  Offline:        {r.offline}")
    print(f"  Fleet avg KL:   {r.fleet_avg_kl:.3f}")
    print(f"  Worst device:   {r.worst_device_id}  KL={r.worst_kl:.3f}")
    if r.alerts:
        print(f"\n  Active alerts ({len(r.alerts)}):")
        for a in r.alerts:
            sev_col = "\033[31m" if a.severity == "alert" else "\033[33m"
            print(f"    {sev_col}[{a.severity.upper()}]\033[0m  {a.device_id}  "
                  f"KL={a.kl_score:.3f}  {a.monitor}")
    print()


def cmd_drift_alerts(args):
    client = get_client(args.api_key, args.url)
    resolved = getattr(args, 'resolved', False)
    alerts = client.drift.alerts(resolved=resolved)
    if not alerts:
        ok("No active drift alerts." if not resolved else "No resolved alerts.")
        print()
        return
    print(f"\n  {'Resolved' if resolved else 'Active'} Drift Alerts  ({len(alerts)})\n")
    for a in alerts:
        sev_col = "\033[31m" if a.severity == "alert" else "\033[33m"
        print(f"  {sev_col}[{a.severity.upper()}]\033[0m  {a.device_id}")
        print(f"     KL score:  {a.kl_score:.3f}")
        print(f"     Monitor:   {a.monitor}")
        print(f"     Model:     {a.model_ref}")
        print(f"     Since:     {a.detected_at}")
        if a.resolved_at:
            print(f"     Resolved:  {a.resolved_at}")
        print()


def cmd_drift_reset(args):
    client = get_client(args.api_key, args.url)
    if hasattr(args, 'fleet') and args.fleet:
        result = client.drift.reset_baseline_fleet(
            hw_class=getattr(args, 'hw_class', None),
            model=getattr(args, 'model', None),
        )
        ok(f"Baseline reset on {result.get('count','?')} devices")
    else:
        client.drift.reset_baseline(args.device_id)
        ok(f"Baseline reset on {args.device_id}")
        print("     Recalibrating over next 200 inferences")
    print()


def cmd_health(args):
    client = get_client(args.api_key, args.url)
    alive = client.health()
    if alive:
        ok("API is reachable and key is valid")
    else:
        err("API unreachable — check https://www.mlops.dev/status")
        sys.exit(1)
    print()


# ── MAIN ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="mlops",
        description="MLOps.dev CLI — deploy and monitor ML models on edge devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mlops status
  mlops devices list --status drift
  mlops models push ./model.onnx --name defect-detector --tag v1.0
  mlops deploy defect-detector:v1.0 --target jetson-prod-01
  mlops deploy defect-detector:v2.0 --target all \\
    --stage hw_class=jetson_orin,count=1 \\
    --stage hw_class=all,pct=100 \\
    --health-gate accuracy_delta=-0.03
  mlops rollback --to defect-detector:v1.0
  mlops drift report
  mlops drift reset jetson-prod-01

Docs:    https://docs.mlops.dev/api
Discord: https://discord.gg/Tb47N9NaPk
        """,
    )
    parser.add_argument("--api-key", metavar="KEY", help="API key (or set MLOPS_API_KEY)")
    parser.add_argument("--url", metavar="URL", help="API base URL (or set MLOPS_API_URL)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Fleet health summary")

    # health
    sub.add_parser("health", help="API health check")

    # devices
    dev = sub.add_parser("devices", help="Manage edge devices")
    dev_sub = dev.add_subparsers(dest="subcommand")

    dl = dev_sub.add_parser("list", help="List all devices")
    dl.add_argument("--status",   help="Filter: online|offline|drift|warning|error")
    dl.add_argument("--hw-class", dest="hw_class", help="Filter by hardware class")
    dl.add_argument("--limit",    type=int, default=100)

    dg = dev_sub.add_parser("get", help="Get one device")
    dg.add_argument("device_id")

    dlg = dev_sub.add_parser("logs", help="Device event log")
    dlg.add_argument("device_id")
    dlg.add_argument("--limit", type=int, default=50)
    dlg.add_argument("--level", help="info|warn|error")

    # models
    mod = sub.add_parser("models", help="Manage model registry")
    mod_sub = mod.add_subparsers(dest="subcommand")

    mod_sub.add_parser("list", help="List all models")

    mp = mod_sub.add_parser("push", help="Push a model file")
    mp.add_argument("file")
    mp.add_argument("--name",     required=True, help="Model name")
    mp.add_argument("--tag",      default="latest", help="Version tag")
    mp.add_argument("--format",   help="onnx|tflite|tensorrt")
    mp.add_argument("--variant",  help="jetson_orin|jetson_nano|rpi5|all")
    mp.add_argument("--metadata", nargs="*", metavar="key=value")

    md = mod_sub.add_parser("delete", help="Delete a model version")
    md.add_argument("name")
    md.add_argument("tag")
    md.add_argument("--yes", "-y", action="store_true")

    # deploy
    dp = sub.add_parser("deploy", help="Deploy a model to devices")
    dp.add_argument("model", help="name:tag e.g. defect-detector:v1.0")
    dp.add_argument("--target",         required=True, help="Device ID, hw_class, or all")
    dp.add_argument("--stage",          dest="stages", action="append", metavar="hw_class=X,count=N")
    dp.add_argument("--health-gate",    dest="health_gate", action="append", metavar="metric=value")
    dp.add_argument("--stage-interval", dest="stage_interval")
    dp.add_argument("--no-wait",        dest="no_wait", action="store_true")
    dp.add_argument("--poll",           type=float, default=5.0)
    dp.add_argument("--timeout",        type=float, default=600.0)

    # rollback
    rb = sub.add_parser("rollback", help="Roll back fleet or device")
    rb.add_argument("--device",  help="Device ID (omit for fleet-wide)")
    rb.add_argument("--to",      help="Model version e.g. defect-detector:v1.0")

    # drift
    dr = sub.add_parser("drift", help="Drift monitoring")
    dr_sub = dr.add_subparsers(dest="subcommand")
    dr_sub.add_parser("report", help="Fleet-wide drift report")
    dra = dr_sub.add_parser("alerts", help="Active drift alerts")
    dra.add_argument("--resolved", action="store_true")
    drr = dr_sub.add_parser("reset", help="Reset drift baseline")
    drr.add_argument("device_id", nargs="?")
    drr.add_argument("--fleet",    action="store_true")
    drr.add_argument("--hw-class", dest="hw_class")
    drr.add_argument("--model")

    # audit
    au = sub.add_parser("audit", help="Export audit log")
    au.add_argument("--device",     dest="device_id")
    au.add_argument("--event-type", dest="event_type")
    au.add_argument("--since")
    au.add_argument("--until")
    au.add_argument("--format",     default="json")
    au.add_argument("--limit",      type=int, default=100)
    au.add_argument("--output",     "-o", help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        dispatch = {
            "status":   cmd_status,
            "health":   cmd_health,
        }
        if args.command in dispatch:
            dispatch[args.command](args)
        elif args.command == "devices":
            {"list": cmd_devices_list, "get": cmd_devices_get,
             "logs": cmd_devices_logs}.get(args.subcommand, lambda a: dev.print_help())(args)
        elif args.command == "models":
            {"list": cmd_models_list, "push": cmd_models_push,
             "delete": cmd_models_delete}.get(args.subcommand, lambda a: mod.print_help())(args)
        elif args.command == "deploy":
            cmd_deploy(args)
        elif args.command == "rollback":
            cmd_rollback(args)
        elif args.command == "drift":
            {"report": cmd_drift_report, "alerts": cmd_drift_alerts,
             "reset": cmd_drift_reset}.get(args.subcommand, lambda a: dr.print_help())(args)
        elif args.command == "audit":
            client = get_client(args.api_key, args.url)
            result = client.audit(
                device_id=getattr(args, 'device_id', None),
                event_type=getattr(args, 'event_type', None),
                since=getattr(args, 'since', None),
                until=getattr(args, 'until', None),
                format=getattr(args, 'format', 'json'),
                limit=getattr(args, 'limit', 100),
            )
            output = json.dumps(result, indent=2)
            if getattr(args, 'output', None):
                with open(args.output, 'w') as f:
                    f.write(output)
                ok(f"Audit log saved to {args.output}")
            else:
                print(output)
    except KeyboardInterrupt:
        print("\n  Cancelled.")
    except Exception as e:
        err(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
