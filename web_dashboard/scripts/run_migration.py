#!/usr/bin/env python3
"""
Run database migrations for research articles schema.

This script applies migration SQL files to update the database schema.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from web_dashboard.postgres_client import PostgresClient
    from dotenv import load_dotenv
except ImportError as e:
    print(f"[ERROR] Missing dependencies: {e}")
    print("Install with: pip install psycopg2-binary python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv("web_dashboard/.env")


def run_migration(migration_file: Path) -> bool:
    """Run a single migration SQL file.
    
    Args:
        migration_file: Path to the migration SQL file
        
    Returns:
        True if successful, False otherwise
    """
    if not migration_file.exists():
        print(f"[ERROR] Migration file not found: {migration_file}")
        return False
    
    # Check for RESEARCH_DATABASE_URL
    database_url = os.getenv("RESEARCH_DATABASE_URL")
    if not database_url:
        print("[ERROR] RESEARCH_DATABASE_URL must be set in environment")
        print("   Add to web_dashboard/.env:")
        print("   RESEARCH_DATABASE_URL=postgresql://postgres@localhost:5432/trading_db")
        return False
    
    # Initialize Postgres client
    try:
        print(f"\n[INFO] Initializing Postgres client...")
        client = PostgresClient()
        print("[OK] Postgres client initialized")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize Postgres client: {e}")
        return False
    
    # Test connection
    if not client.test_connection():
        print("[ERROR] Connection test failed")
        return False
    
    # Read and execute migration file
    print(f"\n[INFO] Executing migration: {migration_file.name}")
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Execute the SQL file
        with client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_content)
            conn.commit()
            print(f"[OK] Successfully executed {migration_file.name}")
            
    except Exception as e:
        print(f"[ERROR] Error executing {migration_file.name}: {e}")
        print("\n[INFO] Common issues:")
        print("   - Column might already exist (this is OK for IF NOT EXISTS)")
        print("   - Insufficient permissions")
        print("   - SQL syntax error")
        return False
    
    return True


def run_ticker_migration() -> bool:
    """Run the ticker to tickers migration.
    
    Returns:
        True if successful, False otherwise
    """
    # Use absolute path from project root
    migration_file = project_root / "web_dashboard" / "migrations" / "migrate_ticker_to_tickers.sql"
    return run_migration(migration_file)


if __name__ == "__main__":
    print("Running Database Migration")
    print("=" * 50)
    
    success = run_ticker_migration()
    
    if success:
        print("\n[OK] Migration complete!")
        print("\n[INFO] Verification:")
        print("   You can verify the migration by checking:")
        print("   SELECT column_name FROM information_schema.columns")
        print("   WHERE table_name = 'research_articles' AND column_name = 'tickers';")
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)

