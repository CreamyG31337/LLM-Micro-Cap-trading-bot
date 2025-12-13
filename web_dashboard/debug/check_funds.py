
import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

env_path = os.path.join('web_dashboard', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

print(f"Checking funds in {url}")

# Check distinct funds for recent dates (Dec 2025)
# filtering for date > 2025-12-01
params = {
    "select": "fund,date",
    "date": "gt.2025-12-01T00:00:00",
    "limit": "100"
}

query_string = urllib.parse.urlencode(params)
full_url = f"{url}/rest/v1/portfolio_positions?{query_string}"

req = urllib.request.Request(full_url)
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        print(f"Found {len(data)} rows since Dec 1st. Funds found:")
        funds = set()
        for row in data:
            funds.add(f"'{row['fund']}'") # Quote to see whitespace
            
        for f in funds:
            print(f"  - {f}")
            
except Exception as e:
    print(f"Error: {e}")
