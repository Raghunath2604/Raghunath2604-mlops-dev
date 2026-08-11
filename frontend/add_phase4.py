import re

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/sdk/server/api.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update init_db schema
new_schema = """
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
"""
content = re.sub(r'CREATE TABLE IF NOT EXISTS api_keys \([\s\S]*?created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\s*\);', new_schema.strip(), content)

# Update demo insert
demo_insert_pg = """
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('key_demo', %s, 'Demo Admin', 'free', 10, 'admin', 'approved')
"""
content = re.sub(r'INSERT INTO api_keys \(id, key_hash, name, subscription_tier, device_limit\)\s*VALUES \(\'key_demo\', %s, \'Demo key\', \'free\', 10\)', demo_insert_pg.strip(), content)

demo_insert_sq = """
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit, role, approval_status)
                VALUES ('key_demo', ?, 'Demo Admin', 'free', 10, 'admin', 'approved')
"""
content = re.sub(r'INSERT INTO api_keys \(id, key_hash, name, subscription_tier, device_limit\)\s*VALUES \(\'key_demo\', \?, \'Demo key\', \'free\', 10\)', demo_insert_sq.strip(), content)

# 2. Add require_admin decorator
admin_decorator = """
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('np_token')
        if not token:
            return jsonify({"error": "Unauthorized"}), 401
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = get_db()
        row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ?", (token_hash,), fetchone=True)
        if not row:
            return jsonify({"error": "Unauthorized"}), 401
        if row['role'] != 'admin':
            return jsonify({"error": "Forbidden - Admin access required"}), 403
        
        request.user = row
        return f(*args, **kwargs)
    return decorated
"""
content = re.sub(r'def require_auth\(f\):', admin_decorator + "\ndef require_auth(f):", content)

# 3. Update login to block pending users
login_old = """
    row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ?", (pw_hash,), fetchone=True)
    if not row:
        return jsonify({"error": "Invalid API Key"}), 401
"""
login_new = """
    row = db_query(db, "SELECT * FROM api_keys WHERE key_hash = ?", (pw_hash,), fetchone=True)
    if not row:
        return jsonify({"error": "Invalid credentials"}), 401
    
    if row.get('approval_status') == 'pending':
        return jsonify({"error": "Your account is pending admin approval"}), 403
    elif row.get('approval_status') == 'rejected':
        return jsonify({"error": "Your account request was rejected"}), 403
"""
content = content.replace(login_old, login_new)

# 4. Update auth/me to return role
me_old = """
    return jsonify({"success": True, "user": {"id": row['id'], "email": row['name'], "tier": row['subscription_tier']}})
"""
me_new = """
    return jsonify({"success": True, "user": {
        "id": row['id'], 
        "email": row['name'], 
        "tier": row['subscription_tier'],
        "role": row.get('role', 'user'),
        "approval_status": row.get('approval_status', 'pending')
    }})
"""
content = content.replace(me_old, me_new)

# 5. Add register endpoint and admin endpoints
admin_endpoints = """
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
"""

content = content + "\n" + admin_endpoints

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api.py successfully for Phase 4")
