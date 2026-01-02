import sys
from pathlib import Path
import os

# Setup paths
current_dir = Path(__file__).resolve().parent
# web_dashboard needs to be in path for supabase_client to work if it's there
wb_path = current_dir / 'web_dashboard'
if str(wb_path) not in sys.path:
    sys.path.append(str(wb_path))

# Root path for utils
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from supabase_client import SupabaseClient
except ImportError:
    # Try importing directly if script is in root but supabase_client is in web_dashboard
    sys.path.append(str(current_dir / 'web_dashboard'))
    from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("🔍 Verifying DB Tables...")

# 1. Check dividend_log
try:
    res = client.supabase.table('dividend_log').select('count', count='exact').limit(0).execute()
    # Supabase-py select doesn't always return count unless requested
    # Just selecting * limit 1 is enough to prove table exists
    res = client.supabase.table('dividend_log').select('*').limit(1).execute()
    print("✅ Table 'dividend_log' exists and is accessible.")
except Exception as e:
    print(f"❌ Error accessing 'dividend_log': {e}")
    print("   (This table is required for the backfill.)")

# 2. Check trade_log columns
try:
    res = client.supabase.table('trade_log').select('*').limit(1).execute()
    print("✅ Table 'trade_log' exists.")
    if res.data:
        cols = res.data[0].keys()
        print(f"   Columns: {list(cols)}")
        if 'action' not in cols:
            print("   ℹ️ 'action' column is missing (Expected). Logic updated to infer from signed 'shares'.")
        if 'shares' in cols:
             print("   ✅ 'shares' column present.")
    else:
        print("   Table is empty, cannot verify columns directly but table exists.")
except Exception as e:
    print(f"❌ Error accessing 'trade_log': {e}")
