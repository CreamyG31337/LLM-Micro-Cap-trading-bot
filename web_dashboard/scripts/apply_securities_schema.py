#!/usr/bin/env python3
"""
Apply Securities Schema
======================
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from postgres_client import PostgresClient

def apply_schema():
    db = PostgresClient()
    schema_file = Path(__file__).parent.parent / "schema" / "32_securities_metadata.sql"
    
    print(f"Applying schema from {schema_file.name}...")
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
        
    db.execute_update(schema_sql)
    print("✅ Securities table created successfully")

if __name__ == "__main__":
    apply_schema()
