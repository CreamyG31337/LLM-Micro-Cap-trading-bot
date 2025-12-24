"""Delete Dec 23 portfolio positions and re-run rebuild"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def main():
    client = SupabaseClient(use_service_role=True)
    if not client:
        print("Failed to connect to Supabase")
        return False
    
    fund = "Project Chimera"
    date_to_delete = "2025-12-23"
    
    print(f"\n=== Deleting {date_to_delete} positions for {fund} ===")
    
    # Check how many records exist
    check = client.supabase.table('portfolio_positions')\
        .select('id', count='exact')\
        .eq('fund', fund)\
        .gte('date', f'{date_to_delete} 00:00:00')\
        .lte('date', f'{date_to_delete} 23:59:59')\
        .execute()
    
    count = check.count if hasattr(check, 'count') else len(check.data)
    print(f"Found {count} positions to delete")
    
    if count == 0:
        print("No positions found for this date")
        return True
    
    # Delete in batches
    deleted = 0
    batch_size = 1000
    
    while True:
        # Get batch of IDs
        batch = client.supabase.table('portfolio_positions')\
            .select('id')\
            .eq('fund', fund)\
            .gte('date', f'{date_to_delete} 00:00:00')\
            .lte('date', f'{date_to_delete} 23:59:59')\
            .limit(batch_size)\
            .execute()
        
        if not batch.data:
            break
        
        # Delete this batch
        ids = [row['id'] for row in batch.data]
        for id in ids:
            client.supabase.table('portfolio_positions').delete().eq('id', id).execute()
        
        deleted += len(ids)
        print(f"Deleted {deleted}/{count} positions...")
        
        if len(batch.data) < batch_size:
            break
    
    print(f"\nSuccessfully deleted {deleted} positions for {date_to_delete}")
    
    # Verify deletion
    verify = client.supabase.table('portfolio_positions')\
        .select('id', count='exact')\
        .eq('fund', fund)\
        .gte('date', f'{date_to_delete} 00:00:00')\
        .lte('date', f'{date_to_delete} 23:59:59')\
        .execute()
    
    remaining = verify.count if hasattr(verify, 'count') else len(verify.data)
    print(f"Remaining positions: {remaining}")
    
    return remaining == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
