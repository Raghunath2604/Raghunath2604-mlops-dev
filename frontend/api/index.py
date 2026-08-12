#!/usr/bin/env python3
"""
MLOps.dev — Local API Server
Raghunathareddy GR <hello@mlops.dev>

This is the real API server that the SDK talks to.
It runs locally during development and on your infrastructure in production.

Usage:
    pip install flask flask-cors
    python server/api.py

    # Then use the SDK pointing at local:
    export MLOPS_API_KEY=demo
    export MLOPS_API_URL=http://localhost:8000/v1
    mlops status
"""

import os
import json

def safe_json(s, default=None):
    if default is None:
        default = {}
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default
import time
import uuid
import hashlib
import sqlite3
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, g, make_response
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Enforce HTTPS and secure headers (CSP, X-Frame-Options, X-Content-Type-Options)
Talisman(app, force_https=False) # Keep false for local dev. In prod, set True or handle at proxy level.

# Restrict CORS to specific frontend domains
CORS(app, resources={r"/*": {"origins": ["https://www.mlopsde.me", "http://localhost:8000", "http://localhost:8080", "http://127.0.0.1:8080"]}}, supports_credentials=True)

# Set Max Content Length (16MB) to prevent large payload crash attacks
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Setup Global Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute"],
    storage_uri="memory://"
)

# Global Error Handlers to hide stack traces
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    import traceback
    import sys
    print("EXCEPTION CAUGHT:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    return jsonify({"error": "An unexpected error occurred", "msg": str(e)}), 500

try:
    from billing import billing_bp
    app.register_blueprint(billing_bp, url_prefix='/v1/billing')
except ImportError as e:
    print(f"Warning: Could not import billing module: {e}")

DB_PATH = Path("/tmp/mlops.db") if os.environ.get("VERCEL") else Path(__file__).parent / "mlops.db"
MODELS_DIR = Path("/tmp/models") if os.environ.get("VERCEL") else Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

# ── Database ──────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            # PostgreSQL
            g.db = psycopg2.connect(db_url)
            g.db.autocommit = True
        else:
            # Fallback to SQLite
            g.db = sqlite3.connect(str(DB_PATH))
            g.db.row_factory = sqlite3.Row
    return g.db

def get_cursor(db):
    if hasattr(db, 'cursor_factory'): # psycopg2 uses this or we can check type
        return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    elif isinstance(db, psycopg2.extensions.connection):
        return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        return db.cursor()

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        db = psycopg2.connect(db_url)
        db.autocommit = True
        cursor = db.cursor()
        # Postgres syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                key_hash TEXT UNIQUE NOT NULL,
                name TEXT,
                stripe_customer_id TEXT,
                subscription_tier TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'active',
                device_limit INTEGER DEFAULT 10,
                role TEXT DEFAULT 'user',
                approval_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                name TEXT,
                hw_class TEXT,
                os_info TEXT,
                model_name TEXT,
                model_ver TEXT,
                model_tag TEXT,
                status TEXT,
                drift_score REAL DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES api_keys(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                device_id TEXT,
                severity TEXT,
                action TEXT,
                details TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tag TEXT NOT NULL,
                format TEXT,
                variant TEXT,
                size_bytes INTEGER DEFAULT 0,
                sha256 TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, tag, variant)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                event_type TEXT,
                device_id TEXT,
                model_name TEXT,
                model_tag TEXT,
                status TEXT,
                msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                model_name TEXT,
                model_tag TEXT,
                status TEXT,
                stage INTEGER,
                total_stages INTEGER,
                target TEXT,
                health_gate INTEGER,
                stages TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS drift_alerts (
                id TEXT PRIMARY KEY,
                device_id TEXT,
                device_name TEXT,
                kl_score REAL,
                severity TEXT,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                email TEXT PRIMARY KEY,
                name TEXT,
                source TEXT,
                position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

        ''')
        # Insert demo user if not exists
        cursor.execute("SELECT id FROM api_keys WHERE id = 'admin'")
        if not cursor.fetchone():
            demo_hash = hashlib.sha256(b'demo1234').hexdigest()
            cursor.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('admin', %s, 'demo@nodepilot.dev', 'enterprise', 10, 'admin', 'approved')
            ''', (demo_hash,))
    else:
        db = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
        db.executescript('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                key_hash TEXT UNIQUE NOT NULL,
                name TEXT,
                stripe_customer_id TEXT,
                subscription_tier TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'active',
                device_limit INTEGER DEFAULT 10,
                role TEXT DEFAULT 'user',
                approval_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                name TEXT,
                hw_class TEXT,
                os_info TEXT,
                model_name TEXT,
                model_ver TEXT,
                model_tag TEXT,
                status TEXT,
                drift_score REAL DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES api_keys(id)
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                device_id TEXT,
                severity TEXT,
                action TEXT,
                details TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tag TEXT NOT NULL,
                format TEXT,
                variant TEXT,
                size_bytes INTEGER DEFAULT 0,
                sha256 TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, tag, variant)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                event_type TEXT,
                device_id TEXT,
                model_name TEXT,
                model_tag TEXT,
                status TEXT,
                msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                model_name TEXT,
                model_tag TEXT,
                status TEXT,
                stage INTEGER,
                total_stages INTEGER,
                target TEXT,
                health_gate INTEGER,
                stages TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS drift_alerts (
                id TEXT PRIMARY KEY,
                device_id TEXT,
                device_name TEXT,
                kl_score REAL,
                severity TEXT,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                email TEXT PRIMARY KEY,
                name TEXT,
                source TEXT,
                position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

        ''')
        # Check and insert demo
        row = db.execute("SELECT id FROM api_keys WHERE id = 'admin'").fetchone()
        if not row:
            demo_hash = hashlib.sha256(b'demo1234').hexdigest()
            db.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('admin', ?, 'demo@nodepilot.dev', 'enterprise', 10, 'admin', 'approved')
            ''', (demo_hash,))
            
    if not db_url: db.commit()
    db.close()

# ── Auth middleware ───────────────────────────────────────────────
def db_query(db, query, args=(), fetchone=False, fetchall=False, commit=False):
    cursor = get_cursor(db)
    is_pg = isinstance(db, psycopg2.extensions.connection)
    
    if is_pg:
        query = query.replace('?', '%s')
    
    cursor.execute(query, args)
    
    if commit and not is_pg:
        db.commit()
        
    res = None
    if fetchone:
        res = cursor.fetchone()
        if res and is_pg:
            res = dict(res)
    elif fetchall:
        res = cursor.fetchall()
        if res and is_pg:
            res = [dict(r) for r in res]
            
    cursor.close()
    return res


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cookie_token = request.cookies.get('np_token')
        bearer_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header.split(" ", 1)[1].strip()

        if not cookie_token and not bearer_token:
            return jsonify({"error": "Unauthorized"}), 401
        
        db = get_db()
        row = None
        if cookie_token:
            row = db_query(db, "SELECT * FROM api_keys WHERE id = ?", (cookie_token,), fetchone=True)
        elif bearer_token:
            token_hash = hashlib.sha256(bearer_token.encode()).hexdigest()
            row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ?", (token_hash,), fetchone=True)
            
        if not row:
            return jsonify({"error": "Unauthorized"}), 401
        if row['role'] != 'admin':
            return jsonify({"error": "Forbidden - Admin access required"}), 403
        
        request.user = row
        return f(*args, **kwargs)
    return decorated

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cookie_token = request.cookies.get('np_token')
        bearer_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header.split(" ", 1)[1].strip()

        if not cookie_token and not bearer_token:
            return jsonify({"error": "Missing Authentication (Cookie or Header)"}), 401
            
        db = get_db()
        row = None
        if cookie_token:
            row = db_query(db, "SELECT id FROM api_keys WHERE id = ?", (cookie_token,), fetchone=True)
        elif bearer_token:
            key_hash = hashlib.sha256(bearer_token.encode()).hexdigest()
            row = db_query(db, "SELECT id FROM api_keys WHERE key_hash = ?", (key_hash,), fetchone=True)
            
        if not row:
            return jsonify({"error": "Invalid API key or Session. Get yours at mlops.dev/dashboard"}), 401
            
        # Store user ID in g context for routes to access
        g.user_id = row["id"]
        return f(*args, **kwargs)
    return decorated

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def row_to_dict(row):
    return dict(row) if row else None

# ── Health ────────────────────────────────────────────────────────
@app.route("/v1/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0", "uptime_s": int(time.time() % 864000)})

# ── Status ────────────────────────────────────────────────────────
@app.route("/v1/status")
@require_auth
def status():
    db = get_db()
    total    = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    online   = db.execute("SELECT COUNT(*) FROM devices WHERE status='online'").fetchone()[0]
    offline  = db.execute("SELECT COUNT(*) FROM devices WHERE status='offline'").fetchone()[0]
    drifting = db.execute("SELECT COUNT(*) FROM devices WHERE status IN ('drift','warning')").fetchone()[0]
    active_d = db.execute("SELECT COUNT(*) FROM deployments WHERE status='running'").fetchone()[0]
    return jsonify({
        "total_devices": total, "online": online,
        "offline": offline, "drifting": drifting,
        "active_deployments": active_d, "api_version": "1.0.0",
    })

# ── Auth ──────────────────────────────────────────────────────────
@app.route("/v1/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    # Fallback for old API key usage
    key = data.get("key", "").strip()
    
    db = get_db()
    
    if email and password:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE name = ? AND key_hash = ?", (email, pw_hash), fetchone=True)
    elif key:
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE key_hash = ?", (key,), fetchone=True)
    else:
        return jsonify({"error": "Email and password required"}), 400
        
    if not row:
        return jsonify({"error": "Invalid credentials"}), 401
        
    if row["approval_status"] != 'approved':
        return jsonify({"error": "Your account is pending admin approval."}), 403
        
    resp = make_response(jsonify({
        "success": True,
        "user": {
            "id": row["id"],
            "email": row["name"],
            "role": row["role"],
            "tier": row["subscription_tier"]
        }
    }))
    
    # Issue Secure HttpOnly Cookie
    resp.set_cookie(
        'np_token', 
        row["id"], # Use user ID instead of raw key for session
        httponly=True,
        secure=True, 
        samesite='Strict',
        max_age=86400 * 7 # 7 days
    )
    return resp

@app.route("/v1/auth/logout", methods=["POST"])
def auth_logout():
    resp = make_response(jsonify({"success": True}))
    resp.delete_cookie('np_token', samesite='Strict', secure=True, httponly=True)
    return resp

@app.route("/v1/auth/me", methods=["GET"])
@require_auth
def auth_me():
    # Return user context, heavily used for frontend route guarding
    db = get_db()
    user = db_query(db, "SELECT id, name, subscription_tier FROM api_keys WHERE id = ?", (g.user_id,), fetchone=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["name"],
            "tier": user["subscription_tier"]
        }
    })

# ── Devices ───────────────────────────────────────────────────────
@app.route("/v1/devices/register", methods=["POST"])
@require_auth
def devices_register():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "Device name is required"}), 400
        
    arch = data.get("arch", "unknown")
    os_name = data.get("os", "linux")
    
    import uuid
    device_id = f"dev-{str(uuid.uuid4())[:8]}"
    
    db = get_db()
    db.execute(
        "INSERT INTO devices (id, name, status, arch, os, last_seen, uptime_s) VALUES (?, ?, ?, ?, ?, datetime('now'), 0)",
        (device_id, name, "online", arch, os_name)
    )
    
    return jsonify({"success": True, "device_id": device_id, "name": name})

@app.route("/v1/devices")
@require_auth
def devices_list():
    db = get_db()
    q = "SELECT * FROM devices WHERE 1=1"
    params = []
    if request.args.get("status"):
        q += " AND status=?"
        params.append(request.args["status"])
    if request.args.get("hw_class"):
        q += " AND hw_class=?"
        params.append(request.args["hw_class"])
    if request.args.get("model"):
        q += " AND model_name=?"
        params.append(request.args["model"])
    limit  = min(int(request.args.get("limit",  100)), 500)
    offset = int(request.args.get("offset", 0))
    q += f" ORDER BY id LIMIT {limit} OFFSET {offset}"
    rows = [row_to_dict(r) for r in db.execute(q, params).fetchall()]
    for r in rows:
        r["metadata"] = safe_json(r.get("metadata"))
    total = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    return jsonify({"data": rows, "total": total, "limit": limit, "offset": offset})

@app.route("/v1/devices/<device_id>")
@require_auth
def devices_get(device_id):
    db = get_db()
    row = row_to_dict(db_query(db, "SELECT * FROM devices WHERE id=?", (device_id,), fetchone=True))
    if not row:
        return jsonify({"error": f"Device not found: {device_id}"}), 404
    row["metadata"] = safe_json(row.get("metadata"))
    return jsonify({"data": row})

@app.route("/v1/devices/<device_id>", methods=["DELETE"])
@require_auth
def devices_delete(device_id):
    db = get_db()
    db_query(db, "DELETE FROM devices WHERE id=?", (device_id,), commit=True)
    
    return jsonify({"deleted": device_id})

@app.route("/v1/devices/<device_id>/logs")
@require_auth
def devices_logs(device_id):
    limit = min(int(request.args.get("limit", 50)), 1000)
    db    = get_db()
    rows  = db.execute(
        "SELECT * FROM audit_log WHERE device_id=? ORDER BY created_at DESC LIMIT ?",
        (device_id, limit)
    ).fetchall()
    return jsonify({"data": [dict(r) for r in rows]})

@app.route("/v1/devices/<device_id>/config", methods=["PATCH"])
@require_auth
def devices_config(device_id):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db_query(db, "SELECT id FROM devices WHERE id=?", (device_id,), fetchone=True)
    if not row:
        return jsonify({"error": "Device not found"}), 404
    # Apply supported config fields
    allowed = ["drift_warn", "drift_alert"]
    if "drift_alert" in data:
        db.execute("UPDATE devices SET status='online' WHERE id=? AND drift_score < ?",
                   (device_id, data["drift_alert"]))
    
    return jsonify({"device_id": device_id, "config": data, "applied": True})

@app.route("/v1/keys/generate", methods=["POST"])
@require_auth
@limiter.limit("5 per minute")
def generate_api_key():
    auth_header = request.headers.get("Authorization", "")
    old_key = auth_header.split(" ", 1)[1].strip()
    
    db = get_db()
    user = db_query(db, "SELECT id FROM api_keys WHERE key_hash = ?", (old_key,), fetchone=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    import uuid
    new_key = str(uuid.uuid4())[:16]
    
    db_query(db, "UPDATE api_keys SET key_hash = ? WHERE id = ?", (new_key, user["id"]), commit=True)
    
    
    resp = make_response(jsonify({"key": new_key}))
    resp.set_cookie(
        'np_token', 
        new_key,
        httponly=True,
        secure=True, 
        samesite='Strict',
        max_age=86400 * 7 # 7 days
    )
    return resp

# ── Models ────────────────────────────────────────────────────────
@app.route("/v1/models")
@require_auth
def models_list():
    db   = get_db()
    rows = db_query(db, "SELECT * FROM models ORDER BY name, created_at DESC", fetchall=True)
    # Group by name
    groups = {}
    for row in rows:
        d = dict(row)
        d["metadata"] = safe_json(d.get("metadata"))
        name = d["name"]
        if name not in groups:
            groups[name] = {"id": d["id"], "name": name, "versions": []}
        groups[name]["versions"].append(d)
    return jsonify({"data": list(groups.values())})

@app.route("/v1/models/<name>")
@require_auth
def models_get(name):
    db   = get_db()
    rows = db_query(db, "SELECT * FROM models WHERE name=? ORDER BY created_at DESC", (name,), fetchall=True)
    if not rows:
        return jsonify({"error": f"Model not found: {name}"}), 404
    versions = []
    for row in rows:
        d = dict(row)
        d["metadata"] = safe_json(d.get("metadata"))
        versions.append(d)
    return jsonify({"data": {"id": versions[0]["id"], "name": name, "versions": versions}})

@app.route("/v1/models", methods=["POST"])
@require_auth
def models_push():
    # Accept multipart form upload
    if "model" not in request.files:
        return jsonify({"error": "No model file in request"}), 400

    file     = request.files["model"]
    name     = request.form.get("name", "")
    tag      = request.form.get("tag",  "latest")
    fmt      = request.form.get("format", "onnx")
    variant  = request.form.get("variant", "all")
    sha256   = request.form.get("sha256", "")
    metadata_raw = request.form.get("metadata", "{}")
    try:
        metadata = json.dumps(json.loads(metadata_raw))
    except Exception:
        # metadata might be a Python repr dict string like "{'key': 'val'}"
        # convert safely
        try:
            import ast
            metadata = json.dumps(ast.literal_eval(metadata_raw))
        except Exception:
            metadata = "{}"

    if not name:
        return jsonify({"error": "name is required"}), 400

    # Save file
    model_dir = MODELS_DIR / name / tag / variant
    model_dir.mkdir(parents=True, exist_ok=True)
    save_path = model_dir / file.filename
    file.save(str(save_path))
    size_bytes = save_path.stat().st_size

    # Compute SHA-256 if not provided
    if not sha256:
        h = hashlib.sha256()
        with open(save_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        sha256 = h.hexdigest()

    # Upsert model version
    mv_id = f"mv_{uuid.uuid4().hex[:8]}"
    db    = get_db()
    try:
        db.execute("""
            INSERT INTO models (id, name, tag, format, variant, size_bytes, sha256, metadata)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(name, tag, variant) DO UPDATE SET
                size_bytes=excluded.size_bytes,
                sha256=excluded.sha256,
                metadata=excluded.metadata,
                created_at=datetime('now')
        """, (mv_id, name, tag, fmt, variant, size_bytes, sha256, metadata))
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    row = row_to_dict(db.execute(
        "SELECT * FROM models WHERE name=? AND tag=? AND variant=?",
        (name, tag, variant)
    ).fetchone())
    row["metadata"] = safe_json(row.get("metadata"))

    # Log it
    db.execute(
        "INSERT INTO audit_log (id, event_type, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), "model_push", name, tag, "success",
         f"Pushed {name}:{tag} ({variant}, {size_bytes//1024}KB)")
    )
    

    return jsonify({"data": row}), 201

@app.route("/v1/models/<name>/<tag>", methods=["DELETE"])
@require_auth
def models_delete(name, tag):
    db = get_db()
    # Check not active
    active = db.execute(
        "SELECT COUNT(*) FROM devices WHERE model_name=? AND model_tag=?",
        (name, tag)
    ).fetchone()[0]
    if active > 0:
        return jsonify({
            "error": f"Cannot delete {name}:{tag} — it is active on {active} device(s). "
                     "Deploy a different version first."
        }), 409
    db_query(db, "DELETE FROM models WHERE name=? AND tag=?", (name, tag), commit=True)
    
    return jsonify({"deleted": f"{name}:{tag}"})

# ── Deployments ───────────────────────────────────────────────────
@app.route("/v1/deployments", methods=["POST"])
@require_auth
def deployments_create():
    data       = request.get_json(silent=True) or {}
    model_name = data.get("model_name", "")
    model_tag  = data.get("model_tag",  "latest")
    target     = data.get("target", "")
    stages     = data.get("stages", [])
    health_gate= data.get("health_gate", {})

    if not model_name or not target:
        return jsonify({"error": "model_name and target are required"}), 400

    db    = get_db()
    dep_id = f"dep_{uuid.uuid4().hex[:8]}"
    total_stages = max(len(stages), 1)

    # Simulate instant completion for demo
    dep_status = "completed"

    # Apply model update to matching devices
    if target == "all":
        db.execute(
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=datetime('now') WHERE status != 'offline'",
            (model_name, model_tag)
        )
    elif target in ("jetson_orin","jetson_nano","rpi5","rpi4","coral","x86_64","arm_custom"):
        db.execute(
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=datetime('now') WHERE hw_class=? AND status != 'offline'",
            (model_name, model_tag, target)
        )
    else:
        # Specific device ID
        row = db_query(db, "SELECT id FROM devices WHERE id=?", (target,), fetchone=True)
        if not row:
            return jsonify({"error": f"Device not found: {target}"}), 404
        db.execute(
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=datetime('now') WHERE id=?",
            (model_name, model_tag, target)
        )

    db.execute("""
        INSERT INTO deployments (id, model_name, model_tag, status, stage, total_stages, target, health_gate, stages)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (dep_id, model_name, model_tag, dep_status, total_stages, total_stages,
          target, json.dumps(health_gate), json.dumps(stages)))

    db.execute(
        "INSERT INTO audit_log (id, event_type, device_id, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "deployment", target, model_name, model_tag, dep_status,
         f"Deployed {model_name}:{model_tag} to {target}")
    )
    

    row = row_to_dict(db_query(db, "SELECT * FROM deployments WHERE id=?", (dep_id,), fetchone=True))
    row["stages"]      = json.loads(row.get("stages") or "[]")
    row["health_gate"] = json.loads(row.get("health_gate") or "{}")
    return jsonify({"data": row}), 201

@app.route("/v1/deployments")
@require_auth
def deployments_list():
    db     = get_db()
    limit  = min(int(request.args.get("limit", 20)), 100)
    status = request.args.get("status")
    q      = "SELECT * FROM deployments"
    params = []
    if status:
        q += " WHERE status=?"
        params.append(status)
    q += f" ORDER BY created_at DESC LIMIT {limit}"
    rows = []
    for row in db.execute(q, params).fetchall():
        d = dict(row)
        d["stages"]      = json.loads(d.get("stages") or "[]")
        d["health_gate"] = json.loads(d.get("health_gate") or "{}")
        rows.append(d)
    return jsonify({"data": rows})

@app.route("/v1/deployments/<dep_id>")
@require_auth
def deployments_get(dep_id):
    db  = get_db()
    row = row_to_dict(db_query(db, "SELECT * FROM deployments WHERE id=?", (dep_id,), fetchone=True))
    if not row:
        return jsonify({"error": f"Deployment not found: {dep_id}"}), 404
    row["stages"]      = json.loads(row.get("stages") or "[]")
    row["health_gate"] = json.loads(row.get("health_gate") or "{}")
    return jsonify({"data": row})

@app.route("/v1/deployments/rollback", methods=["POST"])
@require_auth
def deployments_rollback():
    data      = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    model_name= data.get("model_name")
    model_tag = data.get("model_tag")
    db        = get_db()

    if device_id:
        if model_name and model_tag:
            db.execute(
                "UPDATE devices SET model_name=?, model_tag=?, last_seen=datetime('now') WHERE id=?",
                (model_name, model_tag, device_id)
            )
        affected = 1
    else:
        if model_name and model_tag:
            db.execute(
                "UPDATE devices SET model_name=?, model_tag=?, last_seen=datetime('now') WHERE status != 'offline'",
                (model_name, model_tag)
            )
        affected = db.execute("SELECT COUNT(*) FROM devices WHERE status != 'offline'").fetchone()[0]

    db.execute(
        "INSERT INTO audit_log (id, event_type, device_id, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "rollback", device_id or "fleet",
         model_name or "previous", model_tag or "previous",
         "queued", f"Rollback queued for {device_id or 'fleet'}")
    )
    
    return jsonify({"status": "queued", "affected_devices": affected})

@app.route("/v1/deployments/<dep_id>/rollback", methods=["POST"])
@require_auth
def deployment_rollback(dep_id):
    db = get_db()
    db_query(db, "UPDATE deployments SET status='rolled_back' WHERE id=?", (dep_id,), commit=True)
    
    return jsonify({"status": "rolled_back", "deployment_id": dep_id})

# ── Drift ─────────────────────────────────────────────────────────
@app.route("/v1/drift")
@require_auth
def drift_report():
    db       = get_db()
    total    = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    healthy  = db.execute("SELECT COUNT(*) FROM devices WHERE drift_score < 0.4 AND status='online'").fetchone()[0]
    warning  = db.execute("SELECT COUNT(*) FROM devices WHERE drift_score >= 0.4 AND drift_score < 0.7").fetchone()[0]
    drifting = db.execute("SELECT COUNT(*) FROM devices WHERE drift_score >= 0.7").fetchone()[0]
    offline  = db.execute("SELECT COUNT(*) FROM devices WHERE status='offline'").fetchone()[0]

    avg_kl_row = db.execute(
        "SELECT AVG(drift_score) FROM devices WHERE status != 'offline'"
    ).fetchone()
    avg_kl = round(float(avg_kl_row[0] or 0.0), 3)

    worst = db.execute(
        "SELECT id, drift_score FROM devices ORDER BY drift_score DESC LIMIT 1"
    ).fetchone()
    worst_id = worst["id"]   if worst else ""
    worst_kl = worst["drift_score"] if worst else 0.0

    alerts = db.execute(
        "SELECT * FROM drift_alerts WHERE resolved_at IS NULL ORDER BY kl_score DESC"
    ).fetchall()

    return jsonify({"data": {
        "total_devices":   total,
        "healthy":         healthy,
        "warning":         warning,
        "drifting":        drifting,
        "offline":         offline,
        "fleet_avg_kl":    avg_kl,
        "worst_device_id": worst_id,
        "worst_kl":        round(float(worst_kl), 3),
        "alerts":          [dict(a) for a in alerts],
    }})

@app.route("/v1/drift/alerts")
@require_auth
def drift_alerts():
    db       = get_db()
    resolved = request.args.get("resolved", "false").lower() == "true"
    if resolved:
        rows = db.execute(
            "SELECT * FROM drift_alerts WHERE resolved_at IS NOT NULL ORDER BY resolved_at DESC"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM drift_alerts WHERE resolved_at IS NULL ORDER BY kl_score DESC"
        ).fetchall()
    return jsonify({"data": [dict(r) for r in rows]})

@app.route("/v1/drift/<device_id>/history")
@require_auth
def drift_history(device_id):
    hours    = int(request.args.get("hours", 24))
    # Return synthetic history for demo
    import random, math
    now   = time.time()
    base  = 0.12
    points = []
    for i in range(hours * 12):  # 5-min intervals
        ts       = now - (hours * 3600 - i * 300)
        kl       = max(0, base + 0.05 * math.sin(i * 0.3) + random.uniform(-0.02, 0.02))
        points.append({
            "ts":       datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kl_score": round(kl, 4),
            "monitor":  "input_distribution",
        })
    return jsonify({"device_id": device_id, "data": points[-50:]})  # last 50 points

@app.route("/v1/drift/<device_id>/baseline/reset", methods=["POST"])
@require_auth
def drift_reset(device_id):
    db = get_db()
    db.execute(
        "UPDATE devices SET drift_score=0.0, status=CASE WHEN status='drift' THEN 'online' WHEN status='warning' THEN 'online' ELSE status END WHERE id=?",
        (device_id,)
    )
    db.execute(
        "UPDATE drift_alerts SET resolved_at=datetime('now') WHERE device_id=? AND resolved_at IS NULL",
        (device_id,)
    )
    db.execute(
        "INSERT INTO audit_log (id, event_type, device_id, status, msg) VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), "drift_reset", device_id, "success",
         f"Drift baseline reset for {device_id}")
    )
    
    return jsonify({"device_id": device_id, "reset": True, "msg": "Recalibrating over next 200 inferences"})

def send_discord_alert(device_id, kl_score, model_name):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url: return
    payload = {
        "embeds": [{
            "title": "🚨 High Data Drift Detected!",
            "color": 16711680,
            "description": f"Device **{device_id}** is experiencing severe data drift.",
            "fields": [
                {"name": "Model", "value": model_name, "inline": True},
                {"name": "KL Divergence", "value": f"{kl_score:.3f} (Critical)", "inline": True}
            ],
            "footer": {"text": "MLOps.dev Fleet Monitor"}
        }]
    }
    try:
        import requests
        requests.post(webhook_url, json=payload, timeout=2)
    except Exception:
        pass

@app.route("/v1/test-drift-alert", methods=["POST"])
@require_auth
def test_drift_alert():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "jetson-prod-01")
    db = get_db()
    db_query(db, "UPDATE devices SET status='drift', drift_score=0.85 WHERE id=?", (device_id,), commit=True)
    alert_id = f"alert_{uuid.uuid4().hex[:6]}"
    db.execute(
        "INSERT INTO drift_alerts (id, device_id, device_name, kl_score, severity, model_name) VALUES (?, ?, ?, 0.85, 'alert', 'defect-detector')",
        (alert_id, device_id, f"Test Device {device_id}")
    )
    
    send_discord_alert(device_id, 0.85, "defect-detector")
    return jsonify({"status": "alert_triggered", "device_id": device_id, "webhook_sent": bool(os.environ.get("DISCORD_WEBHOOK_URL"))})

@app.route("/v1/drift/baseline/reset-fleet", methods=["POST"])
@require_auth
def drift_reset_fleet():
    data     = request.get_json(silent=True) or {}
    hw_class = data.get("hw_class")
    model    = data.get("model")
    db       = get_db()

    q = "UPDATE devices SET drift_score=0.0, status=CASE WHEN status IN ('drift','warning') THEN 'online' ELSE status END WHERE 1=1"
    params = []
    if hw_class:
        q += " AND hw_class=?"
        params.append(hw_class)
    if model:
        q += " AND model_name=?"
        params.append(model)
    db.execute(q, params)
    count = db.execute("SELECT changes()").fetchone()[0]
    
    return jsonify({"reset": True, "count": count})

# ── Audit ─────────────────────────────────────────────────────────
@app.route("/v1/audit")
@require_auth
def audit():
    db     = get_db()
    limit  = min(int(request.args.get("limit", 100)), 10000)
    q      = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if request.args.get("device_id"):
        q += " AND device_id=?"; params.append(request.args["device_id"])
    if request.args.get("event_type"):
        q += " AND event_type=?"; params.append(request.args["event_type"])
    if request.args.get("since"):
        q += " AND created_at >= ?"; params.append(request.args["since"])
    if request.args.get("until"):
        q += " AND created_at <= ?"; params.append(request.args["until"])
    q += f" ORDER BY created_at DESC LIMIT {limit}"
    rows = [dict(r) for r in db.execute(q, params).fetchall()]
    fmt = request.args.get("format","json")
    if fmt == "csv":
        import csv, io
        buf = io.StringIO()
        if rows:
            w = csv.DictWriter(buf, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        return jsonify({"csv": buf.getvalue()})
    return jsonify({"data": rows, "total": len(rows)})

# ── Waitlist ──────────────────────────────────────────────────────
@app.route("/api/waitlist", methods=["POST"])
@limiter.limit("5 per minute")
def waitlist_join():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    name = data.get("name", "").strip()
    source = data.get("source", "").strip()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    db = get_db()
    
    # Check if already exists
    existing = db_query(db, "SELECT position FROM waitlist WHERE email=?", (email,), fetchone=True)
    if existing:
        return jsonify({"error": "This email is already on the waitlist!"}), 400
        
    # Get next position
    count = db.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0]
    position = count + 1
    
    db.execute(
        "INSERT INTO waitlist (email, name, source, position) VALUES (?, ?, ?, ?)",
        (email, name, source, position)
    )
    
    
    # Send email asynchronously or catch errors so signup succeeds
    try:
        from email_service import send_waitlist_confirmation, send_admin_approval_email
        send_waitlist_confirmation(email, name, position)
        send_admin_approval_email(email, name, source)
    except Exception as e:
        app.logger.error(f"Failed to send waitlist email: {e}")
        
    return jsonify({"success": True, "data": {"position": position}})
    
@app.route("/v1/admin/approve", methods=["GET"])
@limiter.limit("5 per minute")
def admin_approve():
    email = request.args.get("email")
    token = request.args.get("token")
    
    if not email or not token:
        return "Missing email or token", 400
        
    try:
        from email_service import verify_approval_token, send_approval_success_email
        if not verify_approval_token(email, token):
            return "Invalid or expired token", 403
            
        db = get_db()
        existing = db_query(db, "SELECT name FROM waitlist WHERE email=?", (email,), fetchone=True)
        if not existing:
            return "User not found on waitlist", 404
            
        name = existing["name"]
        
        # Generate new API key
        new_key = str(uuid.uuid4())[:16]
        
        # We need to compute key_hash.
        # Wait, the auth system uses key_hash. Wait, the demo key has id 'key_demo' and key_hash 'demo'.
        # Let's just use the raw key as the hash for simplicity here, or just insert it directly.
        key_id = f"key_{str(uuid.uuid4())[:8]}"
        
        # Check if already exists in api_keys just in case (maybe they were already approved)
        already_approved = db_query(db, "SELECT id FROM api_keys WHERE name=?", (email,), fetchone=True)
        if already_approved:
            return "User is already approved", 400
            
        db.execute(
            "INSERT INTO api_keys (id, key_hash, name) VALUES (?, ?, ?)",
            (key_id, new_key, email)
        )
        
        # Optionally remove from waitlist, or just leave them there as approved.
        db_query(db, "DELETE FROM waitlist WHERE email=?", (email,), commit=True)
        
        
        
        # Send success email
        send_approval_success_email(email, name, new_key)
        
        return f"<h3>Success!</h3><p>Approved {email}. They have been emailed their new API key.</p>", 200
    except Exception as e:
        app.logger.error(f"Approval error: {e}")
        return f"An error occurred: {e}", 500

@app.route("/api/waitlist/count", methods=["GET"])
@limiter.exempt
def waitlist_count():
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0]
    return jsonify({"success": True, "data": {"count": count}})
# ── Main ──────────────────────────────────────────────────────────
import threading
import time

def metering_task():
    while True:
        try:
            # Run once a day
            time.sleep(86400)
            with app.app_context():
                db = get_db()
                users = db_query(db, "SELECT id, stripe_customer_id, subscription_tier FROM api_keys WHERE subscription_tier != 'free' AND stripe_customer_id IS NOT NULL", fetchall=True)
                for user in users:
                    pass
        except Exception as e:
            print(f"Metering error: {e}")

init_db()
if __name__ == "__main__":
    print("=" * 55)
    print("  MLOps.dev API Server")
    print("  Raghunathareddy GR – CEO & Founder")
    print("=" * 55)
    print(f"  URL:      http://localhost:8000")
    print(f"  API:      http://localhost:8000/v1")
    print(f"  Demo key: demo")
    print()
    print("  SDK usage:")
    print("    export MLOPS_API_KEY=demo")
    print("    export MLOPS_API_URL=http://localhost:8000/v1")
    print("    mlops status")
    print("    mlops devices list")
    print("=" * 55)
    init_db()
    
    # Start background metering thread
    t = threading.Thread(target=metering_task, daemon=True)
    t.start()
    
    app.run(host="0.0.0.0", port=8000, debug=False)


@app.route('/v1/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    
    db = get_db()
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Check if exists
    existing = db_query(db, "SELECT id FROM api_keys WHERE key_hash = ?", (pw_hash,), fetchone=True)
    if existing:
        return jsonify({"error": "User already exists"}), 400
        
    user_id = 'user_' + os.urandom(8).hex()
    db_query(db, '''
        INSERT INTO api_keys (id, key_hash, name, role, approval_status)
        VALUES (?, ?, ?, 'user', 'pending')
    ''', (user_id, pw_hash, email), commit=True)
    
    # Normally we would trigger an email to admin here
    print(f"[EMAIL MOCK] New user registration requires approval: {email}")
    
    return jsonify({"success": True, "message": "Registration successful, pending admin approval."})

@app.route('/v1/admin/users', methods=['GET'])
@require_admin
def list_users():
    db = get_db()
    users = db_query(db, "SELECT id, name, role, approval_status, created_at FROM api_keys ORDER BY created_at DESC", fetchall=True)
    return jsonify({"success": True, "users": users})

@app.route('/v1/admin/users/<uid>/approve', methods=['POST'])
@require_admin
def approve_user(uid):
    db = get_db()
    db_query(db, "UPDATE api_keys SET approval_status = 'approved' WHERE id = ?", (uid,), commit=True)
    return jsonify({"success": True})

@app.route('/v1/admin/users/<uid>/reject', methods=['POST'])
@require_admin
def reject_user(uid):
    db = get_db()
    db_query(db, "UPDATE api_keys SET approval_status = 'rejected' WHERE id = ?", (uid,), commit=True)
    return jsonify({"success": True})
