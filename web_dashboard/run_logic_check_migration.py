#!/usr/bin/env python3
"""
Execute the logic_check field migration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

def main():
    """Execute the migration."""
    print("🚀 Executing logic_check field migration...")
    
    # Read SQL file
    sql_file = Path(__file__).parent / "schema" / "17_add_logic_check_field.sql"
    if not sql_file.exists():
        print(f"❌ Migration file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Execute migration
    try:
        client = PostgresClient()
        
        if not client.test_connection():
            print("❌ Database connection failed")
            return False
        
        print("✅ Connected to database")
        print("📝 Executing migration...")
        
        with client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_content)
            conn.commit()
        
        print("✅ Migration executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error executing migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

