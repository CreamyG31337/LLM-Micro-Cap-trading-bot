
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

print(f"Counting rows for Project Chimera up to Nov 19...")

# Count rows where date <= 2025-11-19
params = {
    "fund": "eq.Project Chimera",
    "date": "lte.2025-11-19T23:59:59",
    "select": "count",
    "head": "true" # Returns count in header
}

# PostgREST count query
# We need to use Prefer header for count
req = urllib.request.Request(f"{url}/rest/v1/portfolio_positions?fund=eq.Project%20Chimera&date=lte.2025-11-19T23:59:59&select=*")
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")
req.add_header("Range", "0-0") # Just get one row, we care about the total count
req.add_header("Prefer", "count=exact")

try:
    with urllib.request.urlopen(req) as response:
        # The content range header format is "0-0/TOTAL"
        content_range = response.headers.get('Content-Range')
        print(f"Content-Range: {content_range}")
        
        if content_range:
             total = content_range.split('/')[1]
             print(f"Total rows up to Nov 19: {total}")
             
except Exception as e:
    print(f"Error: {e}")

# Now attempt to get 2000 rows
print("\nAttempting to fetch 2000 rows via REST API...")
params = {
    "fund": "eq.Project Chimera",
    "select": "date",
    "limit": "2000"
}
query_string = urllib.parse.urlencode(params)
req = urllib.request.Request(f"{url}/rest/v1/portfolio_positions?{query_string}")
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Successfully fetched {len(data)} rows")
        if len(data) > 0:
            print(f"First date: {data[0]['date']}")
            print(f"Last date: {data[-1]['date']}")
except Exception as e:
    print(f"Error fetching 2000 rows: {e}")
