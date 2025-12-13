
import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

# Load env manually
env_path = os.path.join('web_dashboard', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

if not url or not key:
    print("Missing Supabase credentials")
    sys.exit(1)

print(f"Checking {url}")
print("Querying portfolio_positions for max date...")

# Get max date for Project Chimera
params = {
    "fund": "eq.Project Chimera",
    "select": "date, total_value",
    "order": "date.desc",
    "limit": "5"
}

query_string = urllib.parse.urlencode(params)
full_url = f"{url}/rest/v1/performance_metrics?{query_string}"

req = urllib.request.Request(full_url)
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        if not data:
            print("No data found for Project Chimera")
        else:
            print(f"Found {len(data)} rows. Top 5 dates:")
            for row in data:
                print(f"  - {row['date']}")
            
except Exception as e:
    print(f"Error: {e}")
