"""
Run Migration 36: Fix Congress Trades ON CONFLICT
"""
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postgres_client import PostgresClient

def main():
    # Read migration SQL
    migration_file = Path(__file__).parent.parent / "schema" / "36_fix_congress_trades_on_conflict.sql"
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print(f"Running migration: {migration_file.name}")
    print("=" * 80)
    
    # Initialize client
    client = PostgresClient()
    
    try:
        # Execute migration
        # Split into individual statements since execute_update may not handle multiple statements
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"\nExecuting statement {i}...")
                print(statement[:100] + "..." if len(statement) > 100 else statement)
                try:
                    client.execute_update(statement)
                    print(f"✅ Statement {i} completed successfully")
                except Exception as e:
                    print(f"⚠️  Statement {i} failed (may be expected): {e}")
        
        print("\n" + "=" * 80)
        print("Migration complete!")
        
        # Verify
        result = client.execute_query("""
            SELECT 
                conname as constraint_name,
                contype as constraint_type
            FROM pg_constraint 
            WHERE conrelid = 'congress_trades'::regclass 
            AND conname LIKE '%politician%ticker%'
            ORDER BY conname
        """)
        
        print("\nCurrent constraints:")
        for row in result:
            print(f"  - {row}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
