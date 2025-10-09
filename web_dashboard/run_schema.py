#!/usr/bin/env python3
"""
Run database schema in Supabase.

This script executes the SQL schema files to create the required tables.
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

def run_schema():
    """Run the database schema in Supabase."""
    print("🚀 Running Database Schema in Supabase")
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
        
        print(f"\n📄 Reading: {schema_file}")
        try:
            with open(schema_file, 'r') as f:
                sql_content = f.read()
            
            print(f"📝 SQL Content Preview:")
            print("=" * 30)
            print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
            print("=" * 30)
            
            # Note: Supabase Python client doesn't have a direct way to execute arbitrary SQL
            # You need to run this in the Supabase SQL Editor
            print(f"\n⚠️  IMPORTANT: Copy the SQL above and run it in your Supabase SQL Editor")
            print(f"   URL: https://supabase.com/dashboard/project/{url.split('//')[1].split('.')[0]}/sql")
            
        except Exception as e:
            print(f"❌ Error reading {schema_file}: {e}")
    
    print(f"\n📋 Manual Steps Required:")
    print(f"1. Go to: https://supabase.com/dashboard")
    print(f"2. Open your project")
    print(f"3. Go to SQL Editor")
    print(f"4. Copy and paste the SQL from the files above")
    print(f"5. Run the SQL to create the tables")
    print(f"6. Then run: python web_dashboard/migrate_thesis_to_supabase.py")
    
    return True

if __name__ == "__main__":
    success = run_schema()
    if not success:
        sys.exit(1)
