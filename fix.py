with open('frontend/api/index.py', 'r') as f: content = f.read()
old_code = """def require_admin(f):
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

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow both cookie-based auth (for frontend) and header-based (for SDK)
        key = None
        if 'np_token' in request.cookies:
            key = request.cookies.get('np_token')
        else:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                key = auth.split(" ", 1)[1].strip()
                
        if not key:
            return jsonify({"error": "Missing Authentication (Cookie or Header)"}), 401
            
        db = get_db()
        row = db.execute(
            "SELECT id FROM api_keys WHERE key_hash = ?", (key,)
        ).fetchone()
        
        if not row:
            return jsonify({"error": "Invalid API key or Session. Get yours at mlops.dev/dashboard"}), 401
            
        # Store user ID in g context for routes to access
        g.user_id = row["id"]
        return f(*args, **kwargs)
    return decorated"""

new_code = """def require_admin(f):
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
    return decorated"""

content = content.replace(old_code, new_code)
content = content.replace(old_code.replace('\n', '\r\n'), new_code)
with open('frontend/api/index.py', 'w') as f: f.write(content)

with open('sdk/server/api.py', 'r') as f: content = f.read()
content = content.replace(old_code, new_code)
content = content.replace(old_code.replace('\n', '\r\n'), new_code)
with open('sdk/server/api.py', 'w') as f: f.write(content)
