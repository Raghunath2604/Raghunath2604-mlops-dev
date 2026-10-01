import psycopg2
import hashlib

DATABASE_URL = "postgresql://mlops:devpassword@localhost:5432/mlops_db"
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

token = "test_key_123"
key_hash = hashlib.sha256(token.encode()).hexdigest()

cur.execute("INSERT INTO api_keys (id, name, key_hash, role, approval_status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", ("test_user_id", "test_user", key_hash, "admin", "approved"))
conn.commit()

cur.execute("SELECT id, name FROM api_keys")
print(cur.fetchall())
