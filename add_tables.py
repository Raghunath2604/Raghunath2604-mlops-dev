import re

tables_sql = """
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
"""

for file_path in ['frontend/api/index.py', 'sdk/server/api.py']:
    with open(file_path, 'r') as f:
        content = f.read()

    # Find the end of the events table creation
    target_str = "ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            );"
    
    if target_str in content:
        # We need to insert tables_sql right after target_str
        # There are two occurrences: one for postgres, one for sqlite
        # We will just replace all occurrences
        new_content = content.replace(target_str, target_str + tables_sql)
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"Could not find target string in {file_path}")
