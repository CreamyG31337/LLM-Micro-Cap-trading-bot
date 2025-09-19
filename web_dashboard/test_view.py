#!/usr/bin/env python3
"""
Test the current_positions view
"""

from supabase_client import SupabaseClient

def test_view():
    try:
        client = SupabaseClient()
        result = client.client.table('current_positions').select('*').limit(5).execute()
        print(f"✅ Current positions view working! Found {len(result.data)} positions")
        
        for pos in result.data[:3]:
            print(f"  - {pos['ticker']}: {pos['total_shares']} shares @ ${pos['avg_price']:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_view()
