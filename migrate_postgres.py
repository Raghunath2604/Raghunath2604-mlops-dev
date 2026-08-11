import re

path = "c:/Users/raghu/Downloads/mlopsdev-phase1-launch/mlops-dev/sdk/server/api.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update imports
content = re.sub(
    r'import sqlite3\n',
    "import sqlite3\nimport psycopg2\nimport psycopg2.extras\nfrom urllib.parse import urlparse\n",
    content
)

# 2. Update get_db
get_db_new = """def get_db():
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
        return db.cursor()"""

content = re.sub(
    r'def get_db\(\):\n    if "db" not in g:\n        g\.db = sqlite3\.connect\(str\(DB_PATH\)\)\n        g\.db\.row_factory = sqlite3\.Row\n    return g\.db',
    get_db_new,
    content,
    flags=re.DOTALL
)

# 3. Modify init_db for postgres support
init_db_new = """def init_db():
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
        ''')
        # Insert demo user if not exists
        cursor.execute("SELECT id FROM api_keys WHERE id = 'key_demo'")
        if not cursor.fetchone():
            demo_hash = hashlib.sha256(b'demo').hexdigest()
            cursor.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit)
                VALUES ('key_demo', %s, 'Demo key', 'free', 10)
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
        ''')
        # Check and insert demo
        row = db.execute("SELECT id FROM api_keys WHERE id = 'key_demo'").fetchone()
        if not row:
            demo_hash = hashlib.sha256(b'demo').hexdigest()
            db.execute('''
                INSERT INTO api_keys (id, key_hash, name, subscription_tier, device_limit)
                VALUES ('key_demo', ?, 'Demo key', 'free', 10)
            ''', (demo_hash,))
            db.commit()
    db.close()"""

content = re.sub(
    r'def init_db\(\):.*?\n    db\.close\(\)',
    init_db_new,
    content,
    flags=re.DOTALL
)

# 4. Helper for db queries to abstract away ?, %s
exec_helper = """def db_query(db, query, args=(), fetchone=False, fetchall=False, commit=False):
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
    return res"""

content = re.sub(
    r'def require_auth\(f\):',
    exec_helper + "\n\ndef require_auth(f):",
    content
)

# Replace all db.execute in api.py with db_query
content = re.sub(r'db\.execute\("SELECT (.*?)", \((.*?)\)\)\.fetchone\(\)', r'db_query(db, "SELECT \1", (\2), fetchone=True)', content)
content = re.sub(r'db\.execute\("SELECT (.*?)", \((.*?)\)\)\.fetchall\(\)', r'db_query(db, "SELECT \1", (\2), fetchall=True)', content)
content = re.sub(r'db\.execute\("SELECT (.*?)"\)\.fetchall\(\)', r'db_query(db, "SELECT \1", fetchall=True)', content)
content = re.sub(r'db\.execute\("INSERT INTO (.*?)", \((.*?)\)\)', r'db_query(db, "INSERT INTO \1", (\2), commit=True)', content)
content = re.sub(r'db\.execute\("UPDATE (.*?)", \((.*?)\)\)', r'db_query(db, "UPDATE \1", (\2), commit=True)', content)
content = re.sub(r'db\.execute\("DELETE FROM (.*?)", \((.*?)\)\)', r'db_query(db, "DELETE FROM \1", (\2), commit=True)', content)
content = re.sub(r'db\.execute\("SELECT COUNT(.*?)", \((.*?)\)\)\.fetchone\(\)', r'db_query(db, "SELECT COUNT\1", (\2), fetchone=True)', content)

# Commit
content = re.sub(r'db\.commit\(\)', '', content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api.py successfully")
