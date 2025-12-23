"""
Wipe all portfolio_positions for Project Chimera so they can be regenerated with proper columns
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def wipe_portfolio_positions():
    client = SupabaseClient(use_service_role=True)
    fund = "Project Chimera"
    
    print(f"Wiping all portfolio_positions for {fund}...")
    print("=" * 60)
    
    # Count first
    count_response = client.supabase.table("portfolio_positions") \
        .select("count", count="exact") \
        .eq("fund", fund) \
        .execute()
    
    total = count_response.count
    print(f"Found {total} records to delete")
    
    if total == 0:
        print("Nothing to delete!")
        return
    
    # Delete in batches to avoid timeouts
    deleted = 0
    while True:
        # Get a batch of IDs
        batch = client.supabase.table("portfolio_positions") \
            .select("id") \
            .eq("fund", fund) \
            .limit(500) \
            .execute()
        
        if not batch.data:
            break
        
        ids = [r['id'] for r in batch.data]
        
        # Delete this batch
        result = client.supabase.table("portfolio_positions") \
            .delete() \
            .in_("id", ids) \
            .execute()
        
        deleted += len(ids)
        print(f"Deleted {deleted}/{total}...")
        
        if len(batch.data) < 500:
            break
    
    print(f"\nDone! Deleted {deleted} records")
    print("\nNow run the backfill job to regenerate with proper columns:")
    print("  python web_dashboard/scheduler/backfill.py")

if __name__ == "__main__":
    wipe_portfolio_positions()
