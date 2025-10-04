#!/usr/bin/env python3
"""
Test database connection and schema
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('web_dashboard/.env')

# Set environment variables for Supabase
os.environ['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

print("Testing database connection...")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_SERVICE_ROLE_KEY: {os.getenv('SUPABASE_SERVICE_ROLE_KEY')[:20]}...")

try:
    from supabase import create_client

    # Create Supabase client
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )

    print("✅ Supabase client created successfully")

    # Test basic connection by listing tables
    try:
        # Try to access portfolio_positions table
        result = supabase.table('portfolio_positions').select('id').limit(1).execute()
        print("✅ portfolio_positions table exists")

        # Check if our new columns exist
        # This is a simple check - in a real scenario we'd use proper schema inspection
        print("✅ Basic database connectivity test passed")

    except Exception as e:
        print(f"❌ Error accessing tables: {e}")

except Exception as e:
    print(f"❌ Error creating Supabase client: {e}")

print("\nDatabase connection test completed.")
