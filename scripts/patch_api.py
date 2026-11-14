import shutil
import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Alias @app.route("/v1/devices", methods=["POST"])
    target1 = '@app.route("/v1/devices/register", methods=["POST"])\n@app.route("/devices/register", methods=["POST"])\n@require_auth\ndef devices_register():'
    replacement1 = '@app.route("/v1/devices/register", methods=["POST"])\n@app.route("/devices/register", methods=["POST"])\n@app.route("/v1/devices", methods=["POST"])\n@require_auth\ndef devices_register():'
    if target1 in content:
        content = content.replace(target1, replacement1, 1)
        print("Patched target1: devices_register route alias")
    else:
        print("Warning: target1 not found")

    # 2. Support JSON metadata in models_push
    target2 = '''@app.route("/v1/models", methods=["POST"])
@require_auth
def models_push():
    # Accept multipart form upload
    if "model" not in request.files:
        return jsonify({"error": "No model file in request"}), 400'''

    replacement2 = '''@app.route("/v1/models", methods=["POST"])
@require_auth
def models_push():
    # Support JSON metadata registration
    if request.is_json:
        data = request.get_json(silent=True) or {}
        name = data.get("name") or data.get("model_name") or ""
        tag = data.get("tag") or data.get("model_tag") or data.get("model_ver") or "latest"
        fmt = data.get("format", "onnx")
        variant = data.get("variant", "all")
        sha256 = data.get("sha256") or hashlib.sha256(f"{name}:{tag}:{variant}".encode()).hexdigest()
        size_bytes = int(data.get("size_bytes") or data.get("file_size") or 7400000)
        metadata = json.dumps(data.get("metadata", {}))

        from werkzeug.utils import secure_filename
        clean_name = secure_filename(name) or name
        clean_tag = secure_filename(tag) or tag
        clean_variant = secure_filename(variant) or variant
        if not clean_name:
            return jsonify({"error": "A valid model name is required"}), 400

        db = get_db()
        mv_id = f"mv_{uuid.uuid4().hex[:8]}"
        try:
            db_query(db, """
                INSERT INTO models (id, owner_id, name, tag, format, variant, size_bytes, sha256, metadata)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(name, tag, variant) DO UPDATE SET
                    size_bytes=excluded.size_bytes,
                    sha256=excluded.sha256,
                    metadata=excluded.metadata,
                    created_at=CURRENT_TIMESTAMP
            """, (mv_id, g.user_id, name, tag, fmt, variant, size_bytes, sha256, metadata), commit=True)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        db_query(db, 
            "INSERT INTO audit_log (id, owner_id, event_type, model_name, model_tag, status, msg) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), g.user_id, "model_push", name, tag, "success", f"Registered model {name}:{tag} ({variant}, {size_bytes//1024}KB)"), commit=True
        )

        return jsonify({
            "success": True,
            "data": {
                "id": mv_id,
                "name": name,
                "tag": tag,
                "format": fmt,
                "variant": variant,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "metadata": json.loads(metadata)
            }
        }), 201

    # Accept multipart form upload
    if "model" not in request.files:
        return jsonify({"error": "No model file in request"}), 400'''

    if target2 in content:
        content = content.replace(target2, replacement2, 1)
        print("Patched target2: models_push JSON support")
    else:
        print("Warning: target2 not found")

    # 3. Robust defaults in deployments_create
    target3 = '''@app.route("/v1/deployments", methods=["POST"])
@require_auth
def deployments_create():
    data        = request.get_json(silent=True) or {}
    model_name  = data.get("model_name", "")
    model_tag   = data.get("model_tag",  "latest")
    target      = data.get("target", "")
    stages_in   = data.get("stages", [])
    health_gate = data.get("health_gate", {})

    if not model_name or not target:
        return jsonify({"error": "model_name and target are required"}), 400'''

    replacement3 = '''@app.route("/v1/deployments", methods=["POST"])
@require_auth
def deployments_create():
    data        = request.get_json(silent=True) or {}
    model_name  = data.get("model_name", "")
    model_tag   = data.get("model_tag") or data.get("model_ver") or "latest"
    target      = data.get("target") or "all"
    stages_in   = data.get("stages", [])
    health_gate = data.get("health_gate", {})

    if not model_name:
        return jsonify({"error": "model_name is required"}), 400'''

    if target3 in content:
        content = content.replace(target3, replacement3, 1)
        print("Patched target3: deployments_create robust defaults")
    else:
        print("Warning: target3 not found")

    # 4. Update seed user email demo@nodepilot.dev to admin@mlopsde.me
    content = content.replace("'demo@nodepilot.dev'", "'admin@mlopsde.me'")
    print("Patched target4: updated seed email to admin@mlopsde.me")

    # 5. Add admin@mlopsde.me and demo@mlopsde.me to is_demo check
    old_demo_check = "is_demo = (email in ['demo', 'demo@nodepilot.dev', 'admin', 'demo@mlops.dev', 'admin@mlops.dev'])"
    new_demo_check = "is_demo = (email in ['demo', 'demo@nodepilot.dev', 'admin', 'demo@mlops.dev', 'admin@mlops.dev', 'admin@mlopsde.me', 'demo@mlopsde.me'])"
    if old_demo_check in content:
        content = content.replace(old_demo_check, new_demo_check)
        print("Patched target5: is_demo check updated")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully saved {filepath}")

if __name__ == '__main__':
    patch_file('frontend/api/index.py')
    print("Syncing to sdk/server/api.py...")
    shutil.copyfile('frontend/api/index.py', 'sdk/server/api.py')
    print("Sync complete!")
