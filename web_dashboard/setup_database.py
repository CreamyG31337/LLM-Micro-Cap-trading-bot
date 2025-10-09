#!/usr/bin/env python3
"""
Set up Supabase database with required schema.

This script creates the necessary tables in Supabase for the trading bot.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install supabase python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv("web_dashboard/.env")

def setup_database():
    """Set up the Supabase database with required schema."""
    print("🚀 Setting up Supabase Database")
    print("=" * 50)
    
    # Initialize Supabase client
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
            return False
        
        supabase = create_client(url, key)
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        return False
    
    # Read and execute SQL schema files
    schema_files = [
        "web_dashboard/schema/01_main_schema.sql",
        "web_dashboard/schema/04_thesis_schema.sql"
    ]
    
    for schema_file in schema_files:
        if not Path(schema_file).exists():
            print(f"⚠️  Schema file not found: {schema_file}")
            continue
        
        print(f"\n📄 Executing: {schema_file}")
        try:
            with open(schema_file, 'r') as f:
                sql_content = f.read()
            
            # Execute the SQL
            result = supabase.rpc('exec_sql', {'sql': sql_content}).execute()
            print(f"✅ Successfully executed {schema_file}")
            
        except Exception as e:
            print(f"❌ Error executing {schema_file}: {e}")
            # Continue with other files
    
    print("\n🔍 Verifying database setup...")
    
    # Check if main tables exist
    try:
        # Test portfolio_positions table
        result = supabase.table("portfolio_positions").select("id").limit(1).execute()
        print("✅ portfolio_positions table exists")
    except Exception as e:
        print(f"❌ portfolio_positions table error: {e}")
    
    try:
        # Test fund_thesis table
        result = supabase.table("fund_thesis").select("id").limit(1).execute()
        print("✅ fund_thesis table exists")
    except Exception as e:
        print(f"❌ fund_thesis table error: {e}")
    
    try:
        # Test fund_thesis_pillars table
        result = supabase.table("fund_thesis_pillars").select("id").limit(1).execute()
        print("✅ fund_thesis_pillars table exists")
    except Exception as e:
        print(f"❌ fund_thesis_pillars table error: {e}")
    
    print("\n✅ Database setup complete!")
    print("📋 Next steps:")
    print("  1. Run: python web_dashboard/migrate_thesis_to_supabase.py")
    print("  2. Test: python prompt_generator.py --data-dir 'trading_data/funds/TEST' --type daily")
    
    return True

if __name__ == "__main__":
    success = setup_database()
    if not success:
        sys.exit(1)
