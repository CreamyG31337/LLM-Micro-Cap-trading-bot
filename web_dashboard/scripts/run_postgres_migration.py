#!/usr/bin/env python3
"""
Run Postgres Migration for Social Metrics
==========================================

Executes the 18_social_metrics.sql migration in Postgres.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

def run_migration():
    """Run the social_metrics table migration"""
    print("="*60)
    print("Running Postgres Migration: social_metrics table")
    print("="*60)
    
    try:
        client = PostgresClient()
        print("✅ Connected to Postgres")
        
        # Read the migration file
        migration_file = project_root / "web_dashboard" / "schema" / "18_social_metrics.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"\n📄 Reading migration file: {migration_file.name}")
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Execute the migration
        print("\n🔄 Executing migration...")
        with client.get_connection() as conn:
            cursor = conn.cursor()
            # Execute the entire SQL file
            cursor.execute(sql_content)
            conn.commit()
        
        print("✅ Migration executed successfully!")
        
        # Verify the table was created
        print("\n🔍 Verifying table creation...")
        result = client.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name = 'social_metrics'
        """)
        
        if result:
            print("✅ social_metrics table exists")
            
            # Check columns
            columns = client.execute_query("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'social_metrics'
                ORDER BY ordinal_position
            """)
            
            print(f"\n📋 Table has {len(columns)} columns:")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']}")
            
            # Check indexes
            indexes = client.execute_query("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'social_metrics'
                ORDER BY indexname
            """)
            
            if indexes:
                print(f"\n📋 Table has {len(indexes)} indexes:")
                for idx in indexes:
                    print(f"   - {idx['indexname']}")
            
            return True
        else:
            print("❌ Table verification failed - table not found")
            return False
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n🎉 Migration complete! You can now run the Supabase migration.")
    else:
        print("\n⚠️  Migration failed. Check the error messages above.")
    sys.exit(0 if success else 1)

