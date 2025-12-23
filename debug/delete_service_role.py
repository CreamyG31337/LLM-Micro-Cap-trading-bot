import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def delete_with_service_role():
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    # Use service role key to bypass RLS
    service_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    
    if not service_key:
        print("ERROR: No service/secret key found!")
        print("Available env vars:", [k for k in os.environ.keys() if 'SUPABASE' in k])
        return
    
    print(f"Using service role key (first 10 chars): {service_key[:10]}...")
    
    # Create client with service role
    client = create_client(url, service_key)
    
    # Check what's there
    check = client.table("portfolio_positions") \
        .select("id, date, fund") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    print(f"Found {len(check.data)} Dec 22 records")
    
    if not check.data:
        return
    
    # DELETE using service role (bypasses RLS)
    print("Deleting with service role...")
    result = client.table("portfolio_positions") \
        .delete() \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    print(f"Delete result data length: {len(result.data) if result.data else 0}")
    
    # Verify
    verify = client.table("portfolio_positions") \
        .select("count", count="exact") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    print(f"Remaining after delete: {verify.count}")

if __name__ == "__main__":
    delete_with_service_role()
