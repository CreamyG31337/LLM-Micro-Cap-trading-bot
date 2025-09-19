#!/usr/bin/env python3
"""
Fix the missing current_positions view in Supabase
"""

import os
from dotenv import load_dotenv
from supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

def fix_current_positions_view():
    """Create the missing current_positions view"""
    print("🔧 Fixing current_positions view...")
    
    try:
        client = SupabaseClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ Cannot connect to Supabase")
            return False
        
        print("✅ Connected to Supabase")
        
        # The view creation SQL
        view_sql = """
        CREATE OR REPLACE VIEW current_positions AS
        SELECT 
            ticker,
            SUM(shares) as total_shares,
            AVG(price) as avg_price,
            SUM(cost_basis) as total_cost_basis,
            SUM(pnl) as total_pnl,
            SUM(total_value) as total_market_value,
            MAX(date) as last_updated
        FROM portfolio_positions 
        WHERE shares > 0
        GROUP BY ticker;
        """
        
        # Execute the view creation
        print("📝 Creating current_positions view...")
        
        # Use a direct SQL execution approach
        result = client.client.postgrest.rpc('exec_sql', {'sql': view_sql}).execute()
        print("✅ View created successfully!")
        
        # Test the view
        print("🔍 Testing the view...")
        result = client.client.table("current_positions").select("*").limit(5).execute()
        print(f"✅ View working! Found {len(result.data)} current positions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating view: {e}")
        print("\n📋 Manual fix needed:")
        print("Go to your Supabase SQL Editor and run this SQL:")
        print(view_sql)
        return False

if __name__ == "__main__":
    fix_current_positions_view()
