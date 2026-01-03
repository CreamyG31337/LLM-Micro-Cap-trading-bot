#!/usr/bin/env python3
"""
Apply ETF Holdings Schema
==========================
Execute the schema SQL file to create etf_holdings_log table.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def apply_schema():
    db = PostgresClient()
    
    # Read schema file
    schema_file = Path(__file__).parent.parent / "schema" / "31_etf_holdings_log.sql"
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    print(f"Applying schema from {schema_file.name}...")
    
    # Execute
    # Execute
    db.execute_update(schema_sql)
    
    # Also apply the ALTER just in case table exists
    try:
        db.execute_update("ALTER TABLE etf_holdings_log ALTER COLUMN holding_ticker TYPE VARCHAR(50);")
        print("[OK] Column resized to VARCHAR(50)")
    except Exception as e:
        print(f"[WARNING] ALTER failed (maybe already done): {e}")
    
    print("[OK] Schema applied successfully")

if __name__ == "__main__":
    apply_schema()
