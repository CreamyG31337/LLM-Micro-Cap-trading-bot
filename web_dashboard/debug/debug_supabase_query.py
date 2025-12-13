
import os
import sys
from dotenv import load_dotenv
import pandas as pd

# Load env from web_dashboard/.env
load_dotenv('web_dashboard/.env')

from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

if noturl or not key:
    print("Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(url, key)

print(f"Querying portfolio_positions for 'Project Chimera'...")

# Get count first
count = supabase.table("portfolio_positions").select("count", count="exact").eq("fund", "Project Chimera").execute()
print(f"Total rows: {count.count}")

# Get latest dates
result = supabase.table("portfolio_positions").select("date").eq("fund", "Project Chimera").order("date", desc=True).limit(5).execute()

print("\nLatest 5 dates in DB:")
for r in result.data:
    print(r['date'])
