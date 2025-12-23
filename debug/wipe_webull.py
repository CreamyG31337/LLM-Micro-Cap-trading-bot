"""
Wipe RRSP Lance Webull portfolio_positions
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def wipe_fund(fund_name):
    client = SupabaseClient(use_service_role=True)
    
    print(f"Wiping portfolio_positions for {fund_name}...")
    
    # Count first
    count_response = client.supabase.table("portfolio_positions") \
        .select("count", count="exact") \
        .eq("fund", fund_name) \
        .execute()
    
    total = count_response.count
    print(f"Found {total} records")
    
    if total == 0:
        print("Nothing to delete!")
        return
    
    # Delete in batches
    deleted = 0
    while True:
        batch = client.supabase.table("portfolio_positions") \
            .select("id") \
            .eq("fund", fund_name) \
            .limit(500) \
            .execute()
        
        if not batch.data:
            break
        
        ids = [r['id'] for r in batch.data]
        
        client.supabase.table("portfolio_positions") \
            .delete() \
            .in_("id", ids) \
            .execute()
        
        deleted += len(ids)
        print(f"Deleted {deleted}/{total}...")
        
        if len(batch.data) < 500:
            break
    
    print(f"Done! Deleted {deleted} records for {fund_name}")

if __name__ == "__main__":
    wipe_fund("RRSP Lance Webull")
