#!/usr/bin/env python3
"""Apply user setup fix to Supabase"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Read the SQL file
with open('schema/fix_user_setup.sql', 'r') as f:
    sql = f.read()

# Create client with service role key
client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Execute the SQL
print("Applying user setup fix to Supabase...")
print("=" * 60)

try:
    result = client.rpc('exec_sql', {'query': sql}).execute()
    print("✅ User setup fixed successfully!")
    print("\nFrom now on:")
    print("- First user to sign up = automatic admin")
    print("- Admin gets all funds automatically assigned")
    print("- Other users need manual fund assignment via admin dashboard")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nYou can also run this SQL directly in Supabase SQL Editor:")
    print("https://supabase.com/dashboard/project/_/sql")
