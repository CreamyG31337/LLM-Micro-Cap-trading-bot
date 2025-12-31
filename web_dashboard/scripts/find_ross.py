
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Searching for 'Deborah Ross'...")
res = client.supabase.table('politicians').select('*').ilike('name', '%Deborah Ross%').execute()

for p in res.data:
    print(f"ID: {p['id']}")
    print(f"Name: {p['name']}")
    print(f"Bioguide: {p['bioguide_id']}")
    print(f"Party: {p['party']}")
    # Count trades
    trades = client.supabase.table('congress_trades').select('id', count='exact').eq('politician_id', p['id']).execute()
    print(f"Trades: {trades.count}")
    print("-" * 20)
