import uuid
import datetime
from flask import Blueprint, request, jsonify
from index import get_db, now_iso

agent_bp = Blueprint('agent', __name__)

def check_auth(req):
    key = None
    if 'np_token' in req.cookies:
        key = req.cookies.get('np_token')
    else:
        auth = req.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth.split(" ", 1)[1].strip()
    if not key:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key,)).fetchone()
    return user

@agent_bp.route("/register", methods=["POST"])
def register_device():
    user = check_auth(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    name = data.get("name", "Unknown Device")
    hw_class = data.get("hw_class", "unknown")
    arch = data.get("arch", "unknown")
    os_name = data.get("os", "unknown")
    
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
        
    db = get_db()
    existing = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if existing:
        db.execute(
            "UPDATE devices SET last_seen = ? WHERE id = ?", 
            (now_iso(), device_id)
        )
    else:
        db.execute(
            "INSERT INTO devices (id, user_id, name, status, hw_class, arch, os, agent_version, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (device_id, user["id"], name, "online", hw_class, arch, os_name, "1.0.0", now_iso())
        )
    if hasattr(db, 'commit'): db.commit()
    return jsonify({"status": "registered", "device_id": device_id})

@agent_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    user = check_auth(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
        
    ram_mb = data.get("ram_mb", 0)
    cpu_pct = data.get("cpu_pct", 0)
    temp_c = data.get("temp_c", -1.0)
    drift_score = data.get("drift_score", 0.0)
    
    model_name = data.get("model_name", "")
    model_tag = data.get("model_tag", "")
    
    status = "online"
    if drift_score >= 0.7:
        status = "drift"
    elif drift_score >= 0.4:
        status = "warning"
        
    db = get_db()
    
    db.execute(
        "UPDATE devices SET status=?, ram_mb=?, cpu_pct=?, temp_c=?, drift_score=?, last_seen=?, model_name=?, model_tag=? WHERE id=?",
        (status, ram_mb, cpu_pct, temp_c, drift_score, now_iso(), model_name, model_tag, device_id)
    )
    
    # Log event if drift increased significantly (simplified)
    # Check for active deployments targeting this device's hw_class
    device = db.execute("SELECT hw_class FROM devices WHERE id = ?", (device_id,)).fetchone()
    hw_class = device["hw_class"] if device else "all"
    
    active_dep = db.execute(
        "SELECT model_name, model_tag FROM deployments WHERE target IN (?, 'all') AND status = 'active' ORDER BY created_at DESC LIMIT 1",
        (hw_class,)
    ).fetchone()
    
    deployment_info = None
    if active_dep:
        deployment_info = {
            "model_name": active_dep["model_name"],
            "model_tag": active_dep["model_tag"],
            "url": f"https://api.mlopsde.me/v1/models/download/{active_dep['model_name']}/{active_dep['model_tag']}"
        }
    
    if hasattr(db, 'commit'): db.commit()
    
    return jsonify({
        "status": "ack",
        "deployment": deployment_info
    })
