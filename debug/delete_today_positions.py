
import os
import sys
from datetime import datetime

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def delete_positions_for_date(date_str):
    client = SupabaseClient()
    
    try:
        # Check count first
        response = client.supabase.table("portfolio_positions") \
            .select("count", count="exact") \
            .gte("date", f"{date_str}T00:00:00") \
            .lt("date", f"{date_str}T23:59:59") \
            .execute()
            
        count = response.count
        print(f"Found {count} records for date {date_str}")
        
        if count > 0:
            # Delete records using date range
            del_response = client.supabase.table("portfolio_positions") \
                .delete() \
                .gte("date", f"{date_str}T00:00:00") \
                .lt("date", f"{date_str}T23:59:59") \
                .execute()
                
            print(f"Successfully deleted records for {date_str}")
            print(f"Response: {len(del_response.data)} records deleted")
        else:
            print("Nothing to delete.")
            
    except Exception as e:
        print(f"Error deleting records: {e}")

if __name__ == "__main__":
    delete_positions_for_date("2025-12-22")
