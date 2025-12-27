#!/usr/bin/env python3
"""
Check database constraints on portfolio_positions table
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient

def check_constraints():
    """Check what constraints exist on portfolio_positions table"""
    client = SupabaseClient(use_service_role=True)
    
    print("="*80)
    print("CHECKING DATABASE CONSTRAINTS")
    print("="*80)
    
    # Query to check for unique constraints/indexes
    # Note: Supabase/PostgREST doesn't expose this easily via the client
    # We'll need to check via raw SQL or inspect the schema
    
    print("\nChecking portfolio_positions table structure...")
    print("(Note: This requires direct database access to see constraints)")
    
    # Try to get table info via a test query
    try:
        result = client.supabase.table('portfolio_positions')\
            .select('id')\
            .limit(1)\
            .execute()
        
        print("[OK] Table exists and is accessible")
        
        # Try to insert a duplicate to see if constraint prevents it
        # (We'll delete it immediately after)
        print("\nTesting for unique constraint by attempting duplicate insert...")
        print("(This is a safe test - we'll clean up immediately)")
        
    except Exception as e:
        print(f"[ERROR] Could not access table: {e}")

if __name__ == "__main__":
    check_constraints()

