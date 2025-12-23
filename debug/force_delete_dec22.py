import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def force_delete_dec22():
    client = SupabaseClient()
    
    # First, let's see exactly what's there
    print("Checking for Dec 22 records...")
    check = client.supabase.table("portfolio_positions") \
        .select("id, date, fund, ticker") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    if not check.data:
        print("No Dec 22 records found!")
        return
    
    print(f"Found {len(check.data)} Dec 22 records")
    
    # Delete each one by ID to bypass any RLS issues
    print("Deleting records by ID...")
    deleted_count = 0
    for record in check.data:
        try:
            result = client.supabase.table("portfolio_positions") \
                .delete() \
                .eq("id", record['id']) \
                .execute()
            deleted_count += 1
            if deleted_count % 5 == 0:
                print(f"  Deleted {deleted_count}...")
        except Exception as e:
            print(f"  Error deleting {record['id']}: {e}")
    
    print(f"\nTotal deleted: {deleted_count}")
    
    # Verify deletion
    verify = client.supabase.table("portfolio_positions") \
        .select("count", count="exact") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    print(f"Remaining Dec 22 records: {verify.count}")

if __name__ == "__main__":
    force_delete_dec22()
