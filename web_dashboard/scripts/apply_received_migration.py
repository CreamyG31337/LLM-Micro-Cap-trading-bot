#!/usr/bin/env python3
"""
Apply migration to allow "Received" transaction type in congress_trades table.

This script updates the database constraint to allow "Received" transactions
in addition to "Purchase", "Sale", and "Exchange".
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / "web_dashboard" / ".env")

try:
    from web_dashboard.supabase_client import SupabaseClient
except ImportError as e:
    print(f"❌ Error importing SupabaseClient: {e}")
    print("   Make sure you're in the project root and dependencies are installed")
    sys.exit(1)


def apply_migration():
    """Apply the migration to allow 'Received' transaction type."""
    
    print("=" * 60)
    print("CONGRESS TRADES - ALLOW RECEIVED TRANSACTION TYPE")
    print("=" * 60)
    print()
    
    # Initialize Supabase client with service role
    try:
        client = SupabaseClient(use_service_role=True)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        print("\n   Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in:")
        print("   - web_dashboard/.env file, or")
        print("   - Environment variables")
        return False
    
    # Read migration file
    migration_file = project_root / "web_dashboard" / "schema" / "22_congress_trades_allow_received.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📄 Reading migration file: {migration_file.name}")
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False
    
    # Execute migration
    print("\n🔄 Executing migration...")
    try:
        # Supabase doesn't have a direct SQL execution method via the Python client
        # We need to use the REST API or execute via psql
        # For now, we'll provide instructions to run it manually
        
        print("\n⚠️  Supabase Python client doesn't support direct SQL execution.")
        print("   Please apply this migration using one of these methods:\n")
        print("   METHOD 1: Supabase SQL Editor (Recommended)")
        print("   1. Go to your Supabase dashboard")
        print("   2. Navigate to SQL Editor")
        print(f"   3. Copy and paste the contents of: {migration_file}")
        print("   4. Click 'Run'\n")
        print("   METHOD 2: Supabase CLI")
        print(f"   supabase db execute -f {migration_file}\n")
        print("   METHOD 3: Direct psql connection")
        print("   (If you have direct database access)\n")
        
        # Show the SQL content for easy copy-paste
        print("=" * 60)
        print("SQL TO EXECUTE:")
        print("=" * 60)
        print(sql_content)
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = apply_migration()
    if success:
        print("\n✅ Migration instructions displayed above")
        print("   After applying the migration, you can re-run seed_congress_trades.py")
        print("   to import the previously failed 'Received' transactions.")
    else:
        print("\n❌ Failed to prepare migration")
        sys.exit(1)

