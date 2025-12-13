
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env from web_dashboard/.env
load_dotenv('web_dashboard/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

if not url or not key:
    print("Missing credentials")
    sys.exit(1)

supabase = create_client(url, key)

print("Testing pagination logic (no pandas)...")

all_rows = []
batch_size = 1000
offset = 0

while True:
    print(f"Fetching batch: {offset} to {offset + batch_size - 1}")
    result = supabase.table("portfolio_positions")\
        .select("date, fund")\
        .eq("fund", "Project Chimera")\
        .order("date")\
        .range(offset, offset + batch_size - 1)\
        .execute()
    
    rows = result.data
    count = len(rows)
    print(f"  Received {count} rows")
    
    if not rows:
        break
    
    all_rows.extend(rows)
    
    if count < batch_size:
        break
        
    offset += batch_size

print(f"Total rows fetched: {len(all_rows)}")
if len(all_rows) > 0:
    print(f"First date: {all_rows[0]['date']}")
    print(f"Last date: {all_rows[-1]['date']}")
