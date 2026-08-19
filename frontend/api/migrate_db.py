import sqlite3
import os
from pathlib import Path

DB_PATH = Path("mlops.db")

def migrate():
    if not DB_PATH.exists():
        print("Database mlops.db does not exist yet. Ensure it is created before migrating.")
        return
        
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    
    try:
        # Check if owner_id exists in models
        cursor.execute("PRAGMA table_info(models)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'owner_id' not in columns:
            print("Adding owner_id to models...")
            # We set a default to prevent NOT NULL constraint failures on existing rows
            cursor.execute("ALTER TABLE models ADD COLUMN owner_id TEXT DEFAULT 'admin_migration'")
        else:
            print("models table already has owner_id")
            
        # Check if owner_id exists in deployments
        cursor.execute("PRAGMA table_info(deployments)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'owner_id' not in columns:
            print("Adding owner_id to deployments...")
            cursor.execute("ALTER TABLE deployments ADD COLUMN owner_id TEXT DEFAULT 'admin_migration'")
        else:
            print("deployments table already has owner_id")
            
        db.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
