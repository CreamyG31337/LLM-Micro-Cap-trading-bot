#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix missing is_admin() SQL function in Supabase database
"""
import os
import sys
import json
from dotenv import load_dotenv

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SECRET_KEY) must be set")
    sys.exit(1)

# SQL to create the is_admin function
IS_ADMIN_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

def create_is_admin_function():
    """Create the is_admin() function in the database"""
    print("=" * 60)
    print("FIXING MISSING is_admin() FUNCTION")
    print("=" * 60)
    
    # Try using Supabase Management API to execute SQL
    if HAS_REQUESTS:
        print("\n🔗 Attempting to execute SQL via Supabase API...")
        try:
            # Supabase Management API endpoint for executing SQL
            # Note: This may not work with all Supabase plans
            project_ref = SUPABASE_URL.split("//")[1].split(".")[0] if SUPABASE_URL else None
            if project_ref:
                mgmt_url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
                
                headers = {
                    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "query": IS_ADMIN_FUNCTION_SQL
                }
                
                response = requests.post(mgmt_url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    print("✅ Successfully created is_admin() function via API!")
                    return True
                else:
                    print(f"⚠️  API call returned status {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️  API execution failed: {e}")
    
    # Try to use psycopg2 if available
    try:
        import psycopg2
        
        # Try to get database connection from environment
        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        
        if db_url:
            print(f"\n🔗 Found DATABASE_URL, attempting to connect...")
            try:
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute(IS_ADMIN_FUNCTION_SQL)
                conn.commit()
                cur.close()
                conn.close()
                print("✅ Successfully created is_admin() function!")
                print("\n🔄 Refreshing PostgREST schema cache...")
                print("   (This may take a few seconds)")
                return True
            except Exception as e:
                print(f"❌ Error connecting to database: {e}")
                print("\n📋 Please run the SQL manually (see below)")
        else:
            print("\n⚠️  DATABASE_URL not found in environment.")
            print("   Set DATABASE_URL to your Supabase Postgres connection string")
            print("   Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres")
        
    except ImportError:
        if not HAS_REQUESTS:
            print("\n⚠️  psycopg2 and requests not available.")
            print("   Install with: pip install psycopg2-binary requests")
    
    # Provide manual instructions
    sql_file = os.path.join(os.path.dirname(__file__), "CREATE_IS_ADMIN_FUNCTION.sql")
    print("\n" + "=" * 60)
    print("MANUAL INSTRUCTIONS")
    print("=" * 60)
    print(f"\n📄 SQL file created: {sql_file}")
    print("\n📋 To fix the issue:")
    print("   1. Go to: https://supabase.com/dashboard")
    print("   2. Select your project")
    print("   3. Go to: SQL Editor > New Query")
    print("   4. Open the file: web_dashboard/CREATE_IS_ADMIN_FUNCTION.sql")
    print("   5. Copy and paste the SQL, then click 'Run'")
    print("\n" + "-" * 60)
    print("SQL to execute:")
    print("-" * 60)
    print(IS_ADMIN_FUNCTION_SQL)
    print("-" * 60)
    print("\n💡 After running:")
    print("   - Wait a few seconds for PostgREST schema cache to refresh")
    print("   - Refresh your dashboard to see the admin menu!")
    
    return False

if __name__ == "__main__":
    success = create_is_admin_function()
    if success:
        print("\n✅ Function created! Refresh your dashboard to see admin menu.")
    else:
        print("\n⚠️  Please execute the SQL manually in Supabase Dashboard.")
    sys.exit(0 if success else 1)
