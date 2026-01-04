#!/usr/bin/env python3
"""Apply archive fields migration to research database"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

from postgres_client import PostgresClient

def main():
    print("Applying archive fields migration to research_articles table...")
    
    try:
        client = PostgresClient()
        
        # Read the schema file
        schema_file = Path(__file__).parent / 'schema' / '34_add_archive_fields.sql'
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Execute the schema (DDL statements)
        with client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
        
        print("✅ Migration applied successfully!")
        print("\nVerifying columns exist...")
        
        result = client.execute_query("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'research_articles'
              AND column_name IN ('archive_submitted_at', 'archive_checked_at', 'archive_url')
            ORDER BY column_name
        """)
        
        if result:
            print("\n[ARCHIVE COLUMNS]")
            for row in result:
                print(f"  - {row['column_name']}: {row['data_type']}")
        else:
            print("[WARN] Archive columns not found after migration")
        
        # Check indexes
        index_result = client.execute_query("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'research_articles'
              AND indexname LIKE '%archive%'
            ORDER BY indexname
        """)
        
        if index_result:
            print("\n[ARCHIVE INDEXES]")
            for row in index_result:
                print(f"  - {row['indexname']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

