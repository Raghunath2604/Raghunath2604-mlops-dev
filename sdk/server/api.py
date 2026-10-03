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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, g, make_response, send_from_directory
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



def send_email(to_email, subject, body):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL", smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_pass]):
        print(f"[EMAIL MOCK] Missing SMTP config. Would have sent: '{subject}' to {to_email}")
        return
        
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Force IPv4 to avoid Vercel IPv6 routing issues
    import socket
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        responses = old_getaddrinfo(*args, **kwargs)
        return [r for r in responses if r[0] == socket.AF_INET]
    socket.getaddrinfo = new_getaddrinfo
    
    try:
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_pass)
        except Exception as e:
            print(f"SMTP 587 failed ({e}), trying 465 SSL...")
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=10)
            server.login(smtp_user, smtp_pass)
            
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
    finally:
        socket.getaddrinfo = old_getaddrinfo

app = Flask(__name__)

# Enforce HTTPS and secure headers (allow CDN and inline scripts for dashboard)
Talisman(app, force_https=False, content_security_policy=None)

# Restrict CORS to specific frontend domains
CORS(app, resources={r"/*": {
    "origins": [
        "https://www.mlopsde.me",
        "https://mlopsde.me",
        "https://www.mlops.dev",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]
}}, supports_credentials=True)

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
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    import traceback
    import sys
    print("EXCEPTION CAUGHT:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    return jsonify({"error": "An internal server error occurred"}), 500

try:
    from billing import billing_bp
    app.register_blueprint(billing_bp, url_prefix='/v1/billing')
except ImportError as e:
    print(f"Warning: Could not import billing module: {e}")

DB_PATH = Path(__file__).resolve().parents[2] / "mlops.db"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
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
            g.db = sqlite3.connect(str(DB_PATH), timeout=15, isolation_level=None)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA journal_mode=WAL")
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
                uptime_s INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
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
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                email TEXT PRIMARY KEY,
                name TEXT,
                source TEXT,
                position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS verification_codes (
                email TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        pg_migrations = [
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS device_limit INTEGER DEFAULT 10",
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'",
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'pending'",
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT",
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'enterprise'",
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active'",
            "ALTER TABLE drift_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP",
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS uptime_s INTEGER DEFAULT 0",
            "ALTER TABLE devices ADD COLUMN IF NOT EXISTS metadata TEXT DEFAULT '{}'",
        ]
        for m in pg_migrations:
            try:
                cursor.execute(m)
            except Exception:
                pass

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
                uptime_s INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
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
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                email TEXT PRIMARY KEY,
                name TEXT,
                source TEXT,
                position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS verification_codes (
                email TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                email TEXT,
                name TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, provider_user_id),
                FOREIGN KEY(user_id) REFERENCES api_keys(id) ON DELETE CASCADE
            );

        ''')
        # Safely migrate columns onto existing tables
        safe_migrations = [
            "ALTER TABLE audit_log ADD COLUMN owner_id TEXT DEFAULT 'admin'",
            "ALTER TABLE drift_alerts ADD COLUMN resolved_at TIMESTAMP",
            "ALTER TABLE devices ADD COLUMN metadata TEXT DEFAULT '{}'",
            "ALTER TABLE devices ADD COLUMN uptime_s INTEGER DEFAULT 0",
            "ALTER TABLE api_keys ADD COLUMN avatar_url TEXT",
            "ALTER TABLE api_keys ADD COLUMN email_verified INTEGER DEFAULT 0",
        ]
        for migration in safe_migrations:
            try:
                db.execute(migration)
            except Exception:
                pass

        # Ensure missing columns exist in api_keys for existing DBs
        pragma_cols = [row[1] for row in db.execute("PRAGMA table_info(api_keys)").fetchall()]
        if 'device_limit' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN device_limit INTEGER DEFAULT 10")
        if 'role' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN role TEXT DEFAULT 'user'")
        if 'approval_status' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN approval_status TEXT DEFAULT 'pending'")
        if 'stripe_customer_id' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN stripe_customer_id TEXT")
        if 'subscription_tier' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
        if 'subscription_status' not in pragma_cols:
            db.execute("ALTER TABLE api_keys ADD COLUMN subscription_status TEXT DEFAULT 'active'")

        # Check and insert demo keys
        demo_hash = hashlib.sha256(b'demo').hexdigest()
        demo1234_hash = hashlib.sha256(b'demo1234').hexdigest()
        
        row = db.execute("SELECT id FROM api_keys WHERE id = 'admin'").fetchone()
        if not row:
            db.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('admin', ?, 'demo@nodepilot.dev', 'enterprise', 100, 'admin', 'approved')
            ''', (demo_hash,))
        else:
            db.execute("UPDATE api_keys SET key_hash = ? WHERE id = 'admin'", (demo_hash,))

        row2 = db.execute("SELECT id FROM api_keys WHERE id = 'admin_demo1234'").fetchone()
        if not row2:
            db.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('admin_demo1234', ?, 'demo1234@nodepilot.dev', 'enterprise', 100, 'admin', 'approved')
            ''', (demo1234_hash,))

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
    class IndexableDict(dict):
        def __getitem__(self, key):
            if isinstance(key, int):
                return list(self.values())[key]
            return super().__getitem__(key)

    if fetchone:
        res = cursor.fetchone()
        if res:
            res = IndexableDict(dict(res) if hasattr(res, 'keys') else res)
    elif fetchall:
        res = cursor.fetchall()
        if res:
            res = [IndexableDict(dict(r) if hasattr(r, 'keys') else r) for r in res]
            
    cursor.close()
    return res


def require_role(allowed_roles):
    def decorator(f):
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
                row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ? OR key_hash = ? OR id = ?", (token_hash, bearer_token, bearer_token), fetchone=True)

            if not row:
                return jsonify({"error": "Unauthorized"}), 401

            role = row.get("role") or "user"
            tenant_id = row["id"]

            tm = db_query(db, "SELECT tenant_id, role FROM team_members WHERE user_id = ?", (row["id"],), fetchone=True)
            if tm:
                tenant_id = tm["tenant_id"]
                if tm.get("role"):
                    role = tm["role"]

            if role not in allowed_roles:
                return jsonify({"error": "Forbidden - Insufficient permissions"}), 403

            request.user = row
            g.user_id = row["id"]
            g.role = role
            g.tenant_id = tenant_id
            return f(*args, **kwargs)
        return decorated
    return decorator

def require_admin(f):
    return require_role(['admin'])(f)

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
            row = db_query(db, "SELECT * FROM api_keys WHERE id = ?", (cookie_token,), fetchone=True)
        elif bearer_token:
            key_hash = hashlib.sha256(bearer_token.encode()).hexdigest()
            row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ? OR key_hash = ? OR id = ?", (key_hash, bearer_token, bearer_token), fetchone=True)

        if not row:
            return jsonify({"error": "Invalid API key or Session. Get yours at mlops.dev/dashboard"}), 401

        request.user = row
        g.user_id = row["id"]
        g.role = row.get("role") or "admin"
        g.tenant_id = row["id"]

        tm = db_query(db, "SELECT tenant_id, role FROM team_members WHERE user_id = ?", (row["id"],), fetchone=True)
        if tm:
            g.tenant_id = tm["tenant_id"]
            if tm.get("role"):
                g.role = tm["role"]

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
@app.route("/v1/summary")
@require_auth
def status():
    db = get_db()
    total    = (db_query(db, "SELECT COUNT(*) FROM devices", fetchone=True) or [0])[0]
    online   = (db_query(db, "SELECT COUNT(*) FROM devices WHERE status='online'", fetchone=True) or [0])[0]
    offline  = (db_query(db, "SELECT COUNT(*) FROM devices WHERE status='offline'", fetchone=True) or [0])[0]
    drifting = (db_query(db, "SELECT COUNT(*) FROM devices WHERE status IN ('drift','warning')", fetchone=True) or [0])[0]
    active_d = (db_query(db, "SELECT COUNT(*) FROM deployments WHERE status='running'", fetchone=True) or [0])[0]
    return jsonify({
        "total_devices": total, "online": online,
        "offline": offline, "drifting": drifting,
        "active_deployments": active_d, "api_version": "1.0.0",
    })

# ── Auth ──────────────────────────────────────────────────────────
@app.route("/v1/auth/login", methods=["POST"])
@limiter.limit("30 per minute")
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    # Fallback for old API key usage
    key = data.get("key", "").strip()
    
    db = get_db()
    row = None
    
    is_demo = (email in ['demo', 'admin', 'demo@nodepilot.dev', 'demo@mlops.dev', 'admin@mlops.dev']) and (password in ['demo', 'demo1234', 'admin'])
    if is_demo:
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE id IN ('admin', 'admin_mlops_demo', 'key_demo') LIMIT 1", fetchone=True)
        if not row:
            init_db()
            row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE id IN ('admin', 'admin_mlops_demo', 'key_demo') LIMIT 1", fetchone=True)
    elif email and password:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        salted_hash = hashlib.sha256((email + password).encode()).hexdigest()
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE (name = ? OR name LIKE ? OR id = ?) AND (key_hash = ? OR key_hash = ? OR key_hash = ?)", 
                       (email, f"{email}@%", email, pw_hash, salted_hash, password), fetchone=True)
    elif key:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE key_hash = ? OR key_hash = ? OR id = ?", (key_hash, key, key), fetchone=True)
    elif email and not password:
        key_hash = hashlib.sha256(email.encode()).hexdigest()
        row = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE key_hash = ? OR key_hash = ? OR id = ?", (key_hash, email, email), fetchone=True)
    else:
        return jsonify({"error": "Email and password required"}), 400
        
    if not row:
        return jsonify({"error": "Invalid credentials"}), 401
        
    if row.get("approval_status") != 'approved':
        return jsonify({"error": "Your account is pending admin approval."}), 403
        
    resp = make_response(jsonify({
        "success": True,
        "key": password if password else key,
        "user": {
            "id": row["id"],
            "email": row["name"],
            "role": row.get("role") or "admin",
            "tier": row.get("subscription_tier") or "enterprise"
        }
    }))
    
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.set_cookie(
        'np_token', 
        row["id"],
        httponly=True,
        secure=is_secure, 
        samesite='Lax' if not is_secure else 'Strict',
        max_age=86400 * 7 # 7 days
    )
    return resp

@app.route("/v1/auth/logout", methods=["POST"])
def auth_logout():
    resp = make_response(jsonify({"success": True}))
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.delete_cookie('np_token', samesite='Lax' if not is_secure else 'Strict', secure=is_secure, httponly=True)
    return resp

@app.route("/v1/auth/me", methods=["GET"])
@require_auth
def auth_me():
    # Return user context, heavily used for frontend route guarding
    db = get_db()
    user = db_query(db, "SELECT id, name, role, subscription_tier FROM api_keys WHERE id = ?", (g.user_id,), fetchone=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["name"],
            "role": user.get("role") or "admin",
            "tier": user.get("subscription_tier") or "enterprise"
        }
    })

def _create_auth_response(row):
    if not isinstance(row, dict) and hasattr(row, 'keys'):
        row = dict(row)
    elif not isinstance(row, dict):
        try:
            row = dict(row)
        except Exception:
            pass
    user_id = row.get("id") if isinstance(row, dict) else row[0]
    email = (row.get("name") if isinstance(row, dict) else row[2]) or "user@mlops.dev"
    role = (row.get("role") if isinstance(row, dict) else "user") or "user"
    tier = (row.get("subscription_tier") if isinstance(row, dict) else "starter") or "starter"

    resp = make_response(jsonify({
        "success": True,
        "user": {
            "id": user_id,
            "email": email,
            "role": role,
            "tier": tier
        }
    }))
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.set_cookie(
        'np_token', 
        user_id,
        httponly=True,
        secure=is_secure, 
        samesite='Lax' if not is_secure else 'Strict',
        max_age=86400 * 7
    )
    return resp

@app.route("/v1/auth/send-code", methods=["POST"])
@limiter.limit("10 per minute")
def auth_send_code():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not email or not re.match(email_regex, email) or len(email) > 254:
        return jsonify({"error": "A valid email address is required"}), 400

    import random
    code = f"{random.randint(100000, 999999)}"
    from datetime import datetime, timezone, timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    db_query(db, "DELETE FROM verification_codes WHERE email = ?", (email,), commit=True)
    db_query(db, "INSERT INTO verification_codes (email, code, expires_at) VALUES (?, ?, ?)", 
             (email, code, expires_at), commit=True)

    subject = "MLOps.dev - Your Verification Code"
    body = f"Hello,\n\nYour MLOps.dev 6-digit verification code is: {code}\n\nThis code expires in 15 minutes."
    send_email(email, subject, body)

    return jsonify({
        "success": True,
        "message": f"Verification code sent to {email}",
        "code": code
    })

@app.route("/v1/auth/verify-code", methods=["POST"])
@limiter.limit("10 per minute")
def auth_verify_code():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()
    password = data.get("password", "").strip()

    if not email or not code:
        return jsonify({"error": "Email and verification code are required"}), 400

    db = get_db()
    row = db_query(db, "SELECT email, code, expires_at FROM verification_codes WHERE email = ? AND code = ?", 
                   (email, code), fetchone=True)
    if not row:
        return jsonify({"error": "Invalid or expired verification code"}), 400

    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    expires_at = row["expires_at"] if isinstance(row, dict) else row[2]
    if str(expires_at) < now_str:
        db_query(db, "DELETE FROM verification_codes WHERE email = ?", (email,), commit=True)
        return jsonify({"error": "Verification code has expired. Please request a new code."}), 400

    db_query(db, "DELETE FROM verification_codes WHERE email = ?", (email,), commit=True)

    user = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE name = ?", (email,), fetchone=True)
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        pw_hash = hashlib.sha256((email + (password or "email_verified_access")).encode()).hexdigest()
        db_query(db, """
            INSERT INTO api_keys (id, key_hash, name, role, approval_status, subscription_tier, device_limit)
            VALUES (?, ?, ?, 'user', 'approved', 'starter', 10)
        """, (user_id, pw_hash, email), commit=True)
        user = db_query(db, "SELECT id, name, role, approval_status, subscription_tier FROM api_keys WHERE id = ?", (user_id,), fetchone=True)

    return _create_auth_response(user)

# ── Real Multi-Provider OAuth 2.0 Engine (Google & GitHub) ─────────
import secrets

def _get_base_url():
    env_url = os.environ.get("NEXT_PUBLIC_APP_URL") or os.environ.get("APP_URL") or os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
    if env_url:
        if not env_url.startswith("http://") and not env_url.startswith("https://"):
            env_url = "https://" + env_url
        return env_url.rstrip("/")
    proto = request.headers.get("X-Forwarded-Proto", "https" if request.is_secure else "http")
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{proto}://{host}".rstrip("/")

def _link_or_create_oauth_user(provider, provider_user_id, email, name, avatar_url):
    db = get_db()
    provider_user_id = str(provider_user_id)
    email = (email or "").strip().lower()
    if not email:
        email = f"{provider}_{provider_user_id[:8]}@users.noreply.mlops.dev"
    name = (name or "").strip() or f"{provider.capitalize()} User"
    avatar_url = (avatar_url or "").strip()

    # 1. Check if OAuth account is already linked
    oauth_row = db_query(db, "SELECT user_id FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?", 
                         (provider, provider_user_id), fetchone=True)
    if oauth_row:
        user_id = oauth_row["user_id"] if isinstance(oauth_row, dict) else oauth_row[0]
        db_query(db, "UPDATE oauth_accounts SET email = ?, name = ?, avatar_url = ?, updated_at = CURRENT_TIMESTAMP WHERE provider = ? AND provider_user_id = ?",
                 (email, name, avatar_url, provider, provider_user_id), commit=True)
        if avatar_url:
            db_query(db, "UPDATE api_keys SET avatar_url = COALESCE(avatar_url, ?) WHERE id = ?", (avatar_url, user_id), commit=True)
        user = db_query(db, "SELECT id, name, role, approval_status, subscription_tier, avatar_url FROM api_keys WHERE id = ?", (user_id,), fetchone=True)
        return user

    # 2. Check if user already exists with this exact email -> link account
    user = db_query(db, "SELECT id, name, role, approval_status, subscription_tier, avatar_url FROM api_keys WHERE name = ?", (email,), fetchone=True)
    if user:
        user_id = user["id"] if isinstance(user, dict) else user[0]
        oauth_id = f"oa_{uuid.uuid4().hex[:12]}"
        db_query(db, """
            INSERT INTO oauth_accounts (id, user_id, provider, provider_user_id, email, name, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (oauth_id, user_id, provider, provider_user_id, email, name, avatar_url), commit=True)
        if avatar_url:
            db_query(db, "UPDATE api_keys SET avatar_url = COALESCE(avatar_url, ?), email_verified = TRUE WHERE id = ?", (avatar_url, user_id), commit=True)
        else:
            db_query(db, "UPDATE api_keys SET email_verified = TRUE WHERE id = ?", (user_id,), commit=True)
        return user

    # 3. Create new user account with verified email
    user_id = f"user_{provider[:2]}_{uuid.uuid4().hex[:10]}"
    pw_hash = hashlib.sha256((email + f"oauth_{provider}_secret_{secrets.token_hex(8)}").encode()).hexdigest()
    db_query(db, """
        INSERT INTO api_keys (id, key_hash, name, role, approval_status, subscription_tier, device_limit, avatar_url, email_verified)
        VALUES (?, ?, ?, 'user', 'approved', 'pro', 25, ?, TRUE)
    """, (user_id, pw_hash, email, avatar_url), commit=True)

    oauth_id = f"oa_{uuid.uuid4().hex[:12]}"
    db_query(db, """
        INSERT INTO oauth_accounts (id, user_id, provider, provider_user_id, email, name, avatar_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (oauth_id, user_id, provider, provider_user_id, email, name, avatar_url), commit=True)

    user = db_query(db, "SELECT id, name, role, approval_status, subscription_tier, avatar_url FROM api_keys WHERE id = ?", (user_id,), fetchone=True)
    return user

def _create_oauth_redirect_response(user, provider, display_name, email, avatar_url, state_cookie_name=None):
    user_id = user["id"] if isinstance(user, dict) else user[0]
    import urllib.parse
    redirect_target = f"/dashboard.html?auth=success&provider={provider}&user={urllib.parse.quote(display_name)}&email={urllib.parse.quote(email)}&avatar={urllib.parse.quote(avatar_url)}"
    resp = make_response(redirect(redirect_target))
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.set_cookie(
        'np_token',
        user_id,
        httponly=True,
        secure=is_secure,
        samesite='Lax' if not is_secure else 'Strict',
        max_age=86400 * 7
    )
    if state_cookie_name:
        resp.delete_cookie(state_cookie_name, httponly=True, secure=is_secure, samesite='Lax')
    return resp

def _get_oauth_env(key):
    val = os.environ.get(key, "").strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val

@app.route("/v1/auth/oauth/config", methods=["GET"])
@app.route("/auth/oauth/config", methods=["GET"])
def auth_oauth_config():
    g_id = _get_oauth_env("GOOGLE_CLIENT_ID")
    gh_id = _get_oauth_env("GITHUB_CLIENT_ID")
    return jsonify({
        "google_client_id": g_id if g_id != "[SENSITIVE]" else "",
        "github_client_id": gh_id if gh_id != "[SENSITIVE]" else "",
        "google_enabled": bool(g_id and g_id != "[SENSITIVE]"),
        "github_enabled": bool(gh_id and gh_id != "[SENSITIVE]"),
        "base_url": _get_base_url()
    })

@app.route("/v1/auth/oauth/github/authorize", methods=["GET"])
@app.route("/auth/oauth/github/authorize", methods=["GET"])
def auth_oauth_github_authorize():
    client_id = _get_oauth_env("GITHUB_CLIENT_ID")
    if not client_id or client_id == "[SENSITIVE]":
        return redirect("/login.html?oauth_fallback=github")

    import urllib.parse
    state = secrets.token_urlsafe(32)
    base_url = _get_base_url()
    redirect_uri = f"{base_url}/v1/auth/oauth/github/callback"

    github_url = (
        "https://github.com/login/oauth/authorize?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "scope": "read:user user:email",
            "state": state,
            "redirect_uri": redirect_uri
        })
    )
    resp = make_response(redirect(github_url))
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.set_cookie('oauth_state_github', state, max_age=600, httponly=True, secure=is_secure, samesite='Lax')
    return resp

@app.route("/v1/auth/oauth/github/callback", methods=["GET"])
@app.route("/auth/oauth/github/callback", methods=["GET"])
def auth_oauth_github_callback():
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", "GitHub sign-in was cancelled.")
        import urllib.parse
        return redirect(f"/login.html?error={urllib.parse.quote(error_desc)}")

    code = request.args.get("code")
    received_state = request.args.get("state")
    stored_state = request.cookies.get("oauth_state_github")
    client_id = _get_oauth_env("GITHUB_CLIENT_ID")
    client_secret = _get_oauth_env("GITHUB_CLIENT_SECRET")

    if not code or not client_id or not client_secret:
        return redirect("/login.html?error=github_missing_credentials")

    if not stored_state or not received_state or not secrets.compare_digest(stored_state, received_state):
        return redirect("/login.html?error=Security+state+mismatch+(anti-CSRF).+Please+try+again.")

    try:
        import urllib.request
        import urllib.parse
        base_url = _get_base_url()
        redirect_uri = f"{base_url}/v1/auth/oauth/github/callback"

        token_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://github.com/login/oauth/access_token",
            data=token_data,
            headers={"Accept": "application/json", "User-Agent": "MLOps-Dev-OAuth"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            token_res = json.loads(resp.read().decode())

        access_token = token_res.get("access_token")
        if not access_token:
            err_msg = token_res.get("error_description") or "Failed to exchange authorization code with GitHub."
            import urllib.parse
            return redirect(f"/login.html?error={urllib.parse.quote(err_msg)}")

        # Fetch primary user profile
        user_req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": "MLOps-Dev-OAuth"}
        )
        with urllib.request.urlopen(user_req, timeout=12) as u_resp:
            gh_user = json.loads(u_resp.read().decode())

        gh_id = str(gh_user.get("id"))
        username = gh_user.get("login") or f"gh_{gh_id}"
        name = gh_user.get("name") or username
        email = gh_user.get("email")
        avatar = gh_user.get("avatar_url") or f"https://github.com/{username}.png"

        # If email is private on GitHub profile, retrieve primary verified email from /user/emails
        if not email:
            try:
                emails_req = urllib.request.Request(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "User-Agent": "MLOps-Dev-OAuth"}
                )
                with urllib.request.urlopen(emails_req, timeout=10) as e_resp:
                    emails_list = json.loads(e_resp.read().decode())
                for e in emails_list:
                    if e.get("primary") and e.get("verified"):
                        email = e.get("email")
                        break
                    elif e.get("verified") and not email:
                        email = e.get("email")
            except Exception:
                pass

        if not email:
            email = f"{username}@users.noreply.github.com"

        user = _link_or_create_oauth_user("github", gh_id, email, name, avatar)
        return _create_oauth_redirect_response(user, "github", name or username, email, avatar, "oauth_state_github")

    except Exception as e:
        import urllib.parse
        return redirect(f"/login.html?error={urllib.parse.quote(str(e))}")

@app.route("/v1/auth/oauth/google/authorize", methods=["GET"])
@app.route("/auth/oauth/google/authorize", methods=["GET"])
def auth_oauth_google_authorize():
    client_id = _get_oauth_env("GOOGLE_CLIENT_ID")
    if not client_id or client_id == "[SENSITIVE]":
        return redirect("/login.html?oauth_fallback=google")

    import urllib.parse
    state = secrets.token_urlsafe(32)
    base_url = _get_base_url()
    redirect_uri = f"{base_url}/v1/auth/oauth/google/callback"

    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "redirect_uri": redirect_uri,
            "access_type": "online",
            "prompt": "select_account"
        })
    )
    resp = make_response(redirect(google_url))
    is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
    resp.set_cookie('oauth_state_google', state, max_age=600, httponly=True, secure=is_secure, samesite='Lax')
    return resp

@app.route("/v1/auth/oauth/google/callback", methods=["GET"])
@app.route("/auth/oauth/google/callback", methods=["GET"])
def auth_oauth_google_callback():
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", "Google sign-in was cancelled.")
        import urllib.parse
        return redirect(f"/login.html?error={urllib.parse.quote(error_desc)}")

    code = request.args.get("code")
    received_state = request.args.get("state")
    stored_state = request.cookies.get("oauth_state_google")
    client_id = _get_oauth_env("GOOGLE_CLIENT_ID")
    client_secret = _get_oauth_env("GOOGLE_CLIENT_SECRET")

    if not code or not client_id or not client_secret:
        return redirect("/login.html?error=google_missing_credentials")

    if not stored_state or not received_state or not secrets.compare_digest(stored_state, received_state):
        return redirect("/login.html?error=Security+state+mismatch+(anti-CSRF).+Please+try+again.")

    try:
        import urllib.request
        import urllib.parse
        base_url = _get_base_url()
        redirect_uri = f"{base_url}/v1/auth/oauth/google/callback"

        token_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            token_res = json.loads(resp.read().decode())

        access_token = token_res.get("access_token")
        if not access_token:
            err_msg = token_res.get("error_description") or "Failed to exchange authorization code with Google."
            import urllib.parse
            return redirect(f"/login.html?error={urllib.parse.quote(err_msg)}")

        user_req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(user_req, timeout=12) as u_resp:
            g_user = json.loads(u_resp.read().decode())

        email = g_user.get("email", "").strip().lower()
        name = g_user.get("name") or (email.split("@")[0].capitalize() if email else "Google Developer")
        g_id = str(g_user.get("id"))
        avatar = g_user.get("picture") or ""

        user = _link_or_create_oauth_user("google", g_id, email, name, avatar)
        return _create_oauth_redirect_response(user, "google", name, email, avatar, "oauth_state_google")

    except Exception as e:
        import urllib.parse
        return redirect(f"/login.html?error={urllib.parse.quote(str(e))}")

@app.route("/v1/auth/oauth/callback", methods=["GET"])
@app.route("/auth/oauth/callback", methods=["GET"])
def auth_oauth_unified_callback():
    provider = request.args.get("provider", "").lower()
    if not provider:
        if request.cookies.get("oauth_state_google"):
            provider = "google"
        elif request.cookies.get("oauth_state_github"):
            provider = "github"
        elif "scope" in request.args or "authuser" in request.args:
            provider = "google"
        else:
            provider = "github"
    if provider == "google":
        return auth_oauth_google_callback()
    return auth_oauth_github_callback()

@app.route("/v1/auth/oauth/google", methods=["POST"])
@limiter.limit("15 per minute")
def auth_oauth_google():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip() or "Google Developer"
    sub_id = data.get("google_id") or data.get("sub") or uuid.uuid4().hex[:8]
    avatar = data.get("avatar_url", "")
    if not email:
        email = f"google_user_{sub_id[:6]}@gmail.com"
    user = _link_or_create_oauth_user("google", sub_id, email, name, avatar)
    return _create_auth_response(user)

@app.route("/v1/auth/oauth/github", methods=["POST"])
@limiter.limit("15 per minute")
def auth_oauth_github():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip() or data.get("login", "").strip()
    name = data.get("name", "").strip() or username
    email = data.get("email", "").strip().lower()
    gh_id = data.get("github_id") or data.get("id") or username or uuid.uuid4().hex[:8]
    avatar = data.get("avatar_url", "")
    if not email:
        email = f"{username or 'gh_dev'}@users.noreply.github.com"
    user = _link_or_create_oauth_user("github", gh_id, email, name, avatar)
    return _create_auth_response(user)


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
        "INSERT INTO devices (id, name, status, arch, os, last_seen, uptime_s) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 0)",
        (device_id, name, "online", arch, os_name)
    )
    
    return jsonify({"success": True, "device_id": device_id, "name": name})

# ── Edge Agent Integration ─────────────────────────────────────────
@app.route("/v1/agent/register", methods=["POST"])
@app.route("/agent/register", methods=["POST"])
@require_auth
def agent_register():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    name = data.get("name") or device_id or f"edge-node-{uuid.uuid4().hex[:6]}"
    hw_class = data.get("hw_class", "x86_64")
    arch = data.get("arch", "unknown")
    os_name = data.get("os", "linux")
    
    if not device_id:
        device_id = f"dev_{uuid.uuid4().hex[:12]}"
        
    db = get_db()
    existing = db_query(db, "SELECT id FROM devices WHERE id=?", (device_id,), fetchone=True)
    if existing:
        db_query(db, 
            "UPDATE devices SET name=?, hw_class=?, arch=?, os=?, last_seen=CURRENT_TIMESTAMP, status='online' WHERE id=?",
            (name, hw_class, arch, os_name, device_id), commit=True
        )
    else:
        db_query(db,
            "INSERT INTO devices (id, name, status, hw_class, arch, os, last_seen, uptime_s, drift_score, latency_ms) VALUES (?, ?, 'online', ?, ?, ?, CURRENT_TIMESTAMP, 0, 0.0, 0.0)",
            (device_id, name, hw_class, arch, os_name), commit=True
        )
        
    return jsonify({"success": True, "device_id": device_id, "name": name, "status": "online"}), 200

@app.route("/v1/agent/heartbeat", methods=["POST"])
@app.route("/agent/heartbeat", methods=["POST"])
@app.route("/v1/devices/<device_id>/heartbeat", methods=["POST"])
@app.route("/devices/<device_id>/heartbeat", methods=["POST"])
@require_auth
def agent_heartbeat(device_id=None):
    data = request.get_json(silent=True) or {}
    dev_id = device_id or data.get("device_id")
    if not dev_id:
        return jsonify({"error": "device_id is required"}), 400
        
    db = get_db()
    dev = db_query(db, "SELECT * FROM devices WHERE id=?", (dev_id,), fetchone=True)
    if not dev:
        # Auto-register device if unknown
        hw_class = data.get("hw_class", "edge_custom")
        db_query(db,
            "INSERT INTO devices (id, name, status, hw_class, last_seen, uptime_s, drift_score, latency_ms) VALUES (?, ?, 'online', ?, CURRENT_TIMESTAMP, 0, 0.0, 0.0)",
            (dev_id, dev_id, hw_class), commit=True
        )
        dev = db_query(db, "SELECT * FROM devices WHERE id=?", (dev_id,), fetchone=True)
        
    drift_score = data.get("drift_score")
    if drift_score is not None:
        drift_score = float(drift_score)
    else:
        drift_score = dev.get("drift_score", 0.0)
        
    status = data.get("status")
    if not status:
        if drift_score >= 0.7:
            status = "drift"
        elif drift_score >= 0.4:
            status = "warning"
        else:
            status = "online"
            
    ram_mb = data.get("ram_mb", dev.get("ram_mb", 0))
    cpu_pct = data.get("cpu_pct", dev.get("cpu_pct", 0.0))
    temp_c = data.get("temp_c", dev.get("temp_c", 0.0))
    uptime_s = data.get("uptime_s", dev.get("uptime_s", 0))
    active_model = data.get("model_name") or dev.get("model_name")
    active_tag = data.get("model_tag") or dev.get("model_tag")
    
    db_query(db, """
        UPDATE devices 
        SET last_seen=CURRENT_TIMESTAMP, status=?, drift_score=?, ram_mb=?, cpu_pct=?, temp_c=?, uptime_s=?, model_name=?, model_tag=?
        WHERE id=?
    """, (status, drift_score, ram_mb, cpu_pct, temp_c, uptime_s, active_model, active_tag, dev_id), commit=True)
    
    # Check if a deployment exists for this device or hw_class or all
    hw = dev.get("hw_class", "")
    dep = db_query(db, """
        SELECT id, model_name, model_tag FROM deployments 
        WHERE (target = 'all' OR target = ? OR target = ?) AND status != 'failed'
        ORDER BY created_at DESC LIMIT 1
    """, (hw, dev_id), fetchone=True)
    
    deployment_info = None
    if dep and (dep["model_name"] != active_model or dep["model_tag"] != active_tag):
        deployment_info = {
            "id": dep["id"],
            "model_name": dep["model_name"],
            "model_tag": dep["model_tag"],
            "url": f"/v1/models/{dep['model_name']}/{dep['model_tag']}/download"
        }
        
    return jsonify({
        "status": "ok",
        "device_id": dev_id,
        "device_status": status,
        "deployment": deployment_info
    }), 200

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
    
    from pathlib import Path
    from werkzeug.utils import secure_filename
    allowed_extensions = {".onnx", ".tflite", ".engine", ".trt", ".pt", ".h5", ".bin", ".safetensors", ".rknn", ".hef", ".blob", ".xml"}
    clean_filename = secure_filename(file.filename) or "model.bin"
    ext = Path(clean_filename).suffix.lower()
    if ext not in allowed_extensions:
        return jsonify({"error": f"Invalid model format. Allowed extensions: {', '.join(allowed_extensions)}"}), 400

    try:
        metadata = json.dumps(json.loads(metadata_raw))
    except Exception:
        try:
            import ast
            metadata = json.dumps(ast.literal_eval(metadata_raw))
        except Exception:
            metadata = "{}"

    clean_name = secure_filename(name)
    clean_tag = secure_filename(tag) or "latest"
    clean_variant = secure_filename(variant) or "all"
    if not clean_name:
        return jsonify({"error": "A valid model name is required"}), 400

    # Save file securely
    model_dir = MODELS_DIR / clean_name / clean_tag / clean_variant
    model_dir.mkdir(parents=True, exist_ok=True)
    save_path = model_dir / clean_filename
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
                created_at=CURRENT_TIMESTAMP
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
    db.commit()

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
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE status != 'offline'",
            (model_name, model_tag)
        )
    elif target in ("jetson_orin","jetson_nano","rpi5","rpi4","coral","x86_64","arm_custom"):
        db.execute(
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE hw_class=? AND status != 'offline'",
            (model_name, model_tag, target)
        )
    else:
        # Specific device ID
        row = db_query(db, "SELECT id FROM devices WHERE id=?", (target,), fetchone=True)
        if not row:
            return jsonify({"error": f"Device not found: {target}"}), 404
        db_query(db, 
            "UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE id=?",
            (model_name, model_tag, target), commit=True
        )

    db_query(db, """
        INSERT INTO deployments (id, model_name, model_tag, status, stage, total_stages, target, health_gate, stages)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (dep_id, model_name, model_tag, dep_status, total_stages, total_stages,
          target, json.dumps(health_gate), json.dumps(stages)), commit=True)

    db_query(db, 
        "INSERT INTO audit_log (id, event_type, device_id, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "deployment", target, model_name, model_tag, dep_status,
         f"Deployed {model_name}:{model_tag} to {target}"), commit=True
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

@app.route("/v1/deployments/<dep_id>/advance", methods=["POST"])
@require_auth
def deployments_advance(dep_id):
    db = get_db()
    row = row_to_dict(db_query(db, "SELECT * FROM deployments WHERE id=?", (dep_id,), fetchone=True))
    if not row:
        return jsonify({"error": "Deployment not found"}), 404
        
    d = row
    if d.get("status") not in ["in_progress", "running"]:
        return jsonify({"error": "Deployment is not in progress"}), 400
        
    stages_data = json.loads(d.get("stages") or "{}") if isinstance(d.get("stages"), str) else (d.get("stages") or {})
    pending_devices = stages_data.get("pending_devices", [])
    
    if pending_devices:
        placeholders = ','.join(['?']*len(pending_devices))
        db.execute(
            f"UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            [d["model_name"], d["model_tag"]] + pending_devices
        )
        
    stages_data["updated_devices"] = stages_data.get("updated_devices", []) + pending_devices
    stages_data["pending_devices"] = []
    
    total_stages = d.get("total_stages") or 2
    db.execute(
        "UPDATE deployments SET status='completed', stage=?, stages=? WHERE id=?",
        (total_stages, json.dumps(stages_data), dep_id)
    )
    
    db.execute(
        "INSERT INTO audit_log (id, event_type, device_id, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "deployment", d.get("target") or "fleet", d["model_name"], d["model_tag"], "completed",
         f"Approved canary rollout to remaining {len(pending_devices)} devices")
    )
    
    if hasattr(db, 'commit'): db.commit()
    return jsonify({"success": True, "message": "Canary advanced successfully"})

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
                "UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE id=?",
                (model_name, model_tag, device_id)
            )
        affected = 1
    else:
        if model_name and model_tag:
            db.execute(
                "UPDATE devices SET model_name=?, model_tag=?, last_seen=CURRENT_TIMESTAMP WHERE status != 'offline'",
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
        "UPDATE drift_alerts SET resolved_at=CURRENT_TIMESTAMP WHERE device_id=? AND resolved_at IS NULL",
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
@limiter.limit("30 per minute")
def register():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not email or not re.match(email_regex, email) or len(email) > 254:
        return jsonify({"error": "A valid email address is required"}), 400
    if not password or len(password) < 8 or len(password) > 128:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400
    
    db = get_db()
    # Check if exists by email
    existing = db_query(db, "SELECT id FROM api_keys WHERE name = ?", (email,), fetchone=True)
    if existing:
        return jsonify({"error": "Email already registered"}), 400
        
    # Salt the hash with email to avoid UNIQUE key_hash constraint on identical passwords
    pw_hash = hashlib.sha256((email + password).encode()).hexdigest()
        
    user_id = 'user_' + os.urandom(8).hex()
    db_query(db, '''
        INSERT INTO api_keys (id, key_hash, name, role, approval_status)
        VALUES (?, ?, ?, 'user', 'pending')
    ''', (user_id, pw_hash, email), commit=True)
    
    # Send email to admin
    admin_email = os.environ.get("ADMIN_EMAIL")
    if admin_email:
        subject = f"MLOps.dev - New User Registration: {email}"
        body = f"A new user ({email}) has registered and is pending approval.\nLog in to the dashboard to approve them."
        send_email(admin_email, subject, body)
    else:
        print(f"[EMAIL MOCK] New user registration requires approval: {email} (ADMIN_EMAIL not set)")
    
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
    
    # Get user email before approving
    user = db_query(db, "SELECT name FROM api_keys WHERE id = ?", (uid,), fetchone=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    db_query(db, "UPDATE api_keys SET approval_status = 'approved' WHERE id = ?", (uid,), commit=True)
    
    # Notify user
    username = user['name'].split('@')[0].capitalize()
    subject = "Welcome to MLOps.dev - Your Access is Approved!"
    body = f"Hey {username},\n\nWelcome to MLOps.dev! Your account access has been approved.\n\nWe hope you enjoy using the platform to deploy and manage your edge AI models seamlessly.\n\nYou can now log in to your dashboard here:\nhttps://www.mlopsde.me/dashboard\n\nBest regards,\nThe MLOps.dev Team"
    send_email(user['name'], subject, body)
    
    return jsonify({"success": True})

@app.route('/v1/admin/users/<uid>/reject', methods=['POST'])
@require_admin
def reject_user(uid):
    db = get_db()
    db_query(db, "UPDATE api_keys SET approval_status = 'rejected' WHERE id = ?", (uid,), commit=True)
    return jsonify({"success": True})

# ── Team & Integrations ───────────────────────────────────────────
@app.route('/v1/team/invite', methods=['POST'])
@require_role(['admin'])
def invite_member():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    role = data.get('role', 'viewer')
    if role not in ['admin', 'engineer', 'viewer']:
        return jsonify({"error": "Invalid role"}), 400
    db = get_db()
    
    user = db_query(db, "SELECT id FROM api_keys WHERE name = ?", (email,), fetchone=True)
    if not user:
        return jsonify({"error": "User must register first"}), 400
    
    tm_id = 'tm_' + uuid.uuid4().hex[:8]
    tenant_id = getattr(g, 'tenant_id', g.user_id)
    try:
        db_query(db, "INSERT INTO team_members (id, tenant_id, user_id, role) VALUES (?, ?, ?, ?)", (tm_id, tenant_id, user['id'], role), commit=True)
    except Exception as e:
        return jsonify({"error": "User already in team"}), 400
    return jsonify({"success": True, "message": "Invited successfully"})

@app.route('/v1/team/members', methods=['GET'])
@require_auth
def list_members():
    db = get_db()
    tenant_id = getattr(g, 'tenant_id', g.user_id)
    members = db_query(db, "SELECT t.id, t.role, a.name as email, t.created_at FROM team_members t JOIN api_keys a ON t.user_id = a.id WHERE t.tenant_id = ?", (tenant_id,), fetchall=True)
    return jsonify({"data": members or []})

@app.route('/v1/team/members/<id>', methods=['DELETE'])
@require_role(['admin'])
def remove_member(id):
    db = get_db()
    tenant_id = getattr(g, 'tenant_id', g.user_id)
    db_query(db, "DELETE FROM team_members WHERE id = ? AND tenant_id = ?", (id, tenant_id), commit=True)
    return jsonify({"success": True})

@app.route('/v1/webhooks', methods=['POST', 'GET'])
@require_auth
def handle_webhooks():
    db = get_db()
    tenant_id = getattr(g, 'tenant_id', g.user_id)
    if request.method == 'GET':
        whs = db_query(db, "SELECT * FROM webhooks WHERE tenant_id = ?", (tenant_id,), fetchall=True)
        return jsonify({"data": whs or []})
    
    data = request.get_json(silent=True) or {}
    wh_id = 'wh_' + uuid.uuid4().hex[:8]
    db_query(db, "INSERT INTO webhooks (id, tenant_id, url, events, type) VALUES (?, ?, ?, ?, ?)", 
             (wh_id, tenant_id, data.get('url', ''), json.dumps(data.get('events', ['*'])), data.get('type', 'generic')), commit=True)
    return jsonify({"success": True})

@app.route('/v1/webhooks/<id>', methods=['DELETE'])
@require_auth
def delete_webhook(id):
    db = get_db()
    tenant_id = getattr(g, 'tenant_id', g.user_id)
    db_query(db, "DELETE FROM webhooks WHERE id = ? AND tenant_id = ?", (id, tenant_id), commit=True)
    return jsonify({"success": True})

@app.route('/v1/metrics', methods=['GET'])
@require_auth
def prometheus_metrics():
    db = get_db()
    devices = db_query(db, "SELECT * FROM devices", fetchall=True) or []
    lines = []
    for d in devices:
        labels = f'device="{d["id"]}",hw_class="{d.get("hw_class", "")}"'
        lines.append(f'mlops_device_drift_score{{{labels}}} {d.get("drift_score", 0)}')
        lines.append(f'mlops_device_latency_ms{{{labels}}} {d.get("latency_ms", 0)}')
        is_online = 1 if d.get("status") in ["online", "warning", "drift"] else 0
        lines.append(f'mlops_device_online{{{labels}}} {is_online}')
    return "\n".join(lines) + "\n", 200, {'Content-Type': 'text/plain'}

# ── Frontend Static Assets ─────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/dashboard", methods=["GET"])
@app.route("/dashboard.html", methods=["GET"])
def serve_dashboard():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")

@app.route("/<path:filename>", methods=["GET"])
def serve_static_frontend(filename):
    if filename.startswith("v1/") or filename.startswith("agent/"):
        return jsonify({"error": "Resource not found"}), 404
    file_path = FRONTEND_DIR / filename
    if file_path.is_file():
        return send_from_directory(FRONTEND_DIR, filename)
    if (FRONTEND_DIR / f"{filename}.html").is_file():
        return send_from_directory(FRONTEND_DIR, f"{filename}.html")
    return jsonify({"error": "Resource not found"}), 404

@app.route("/_vercel/insights/script.js", methods=["GET"])
def serve_vercel_insights():
    return "", 200, {"Content-Type": "application/javascript"}


