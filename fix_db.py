import re

with open("frontend/api/index.py", "r") as f:
    content = f.read()

wrapper_code = """
class DBCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    def fetchone(self):
        row = self.cursor.fetchone()
        if not row: return None
        if isinstance(row, dict) or type(row).__name__ == 'RealDictRow':
            class IndexableDict(dict):
                def __getitem__(self, key):
                    if isinstance(key, int):
                        return list(self.values())[key]
                    return super().__getitem__(key)
            return IndexableDict(row)
        return row
    def fetchall(self):
        rows = self.cursor.fetchall()
        class IndexableDict(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    return list(self.values())[key]
                return super().__getitem__(key)
        return [IndexableDict(r) if (isinstance(r, dict) or type(r).__name__ == 'RealDictRow') else r for r in rows]
    def __getattr__(self, name):
        return getattr(self.cursor, name)

class DBWrapper:
    def __init__(self, conn, is_pg):
        self.conn = conn
        self.is_pg = is_pg
    def execute(self, query, params=()):
        if self.is_pg:
            query = query.replace('?', '%s')
            import psycopg2.extras
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = self.conn.cursor()
        cur.execute(query, params)
        return DBCursorWrapper(cur)
    def commit(self):
        if not self.is_pg:
            self.conn.commit()
    def cursor(self, *args, **kwargs):
        return self.conn.cursor(*args, **kwargs)
    def executescript(self, script):
        if self.is_pg:
            cur = self.conn.cursor()
            cur.execute(script)
        else:
            self.conn.executescript(script)
    def __getattr__(self, name):
        return getattr(self.conn, name)

def get_db():
    if "db" not in g:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            import psycopg2
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            g.db = DBWrapper(conn, True)
        else:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            g.db = DBWrapper(conn, False)
    return g.db

"""

# find where get_db() starts and where get_cursor() starts
content = re.sub(r'def get_db\(\):.*?(?=\ndef get_cursor)', wrapper_code, content, flags=re.DOTALL)

with open("frontend/api/index.py", "w") as f:
    f.write(content)
