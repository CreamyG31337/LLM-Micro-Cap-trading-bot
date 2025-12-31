
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    # Fix for Windows Unicode output safely
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient

def main():
    print("DEBUGGING congress_trades_analysis TABLE")
    client = SupabaseClient(use_service_role=True)
    
    try:
        print("Attempting to fetch 1 record...")
        res = client.supabase.table('congress_trades_analysis').select('*').limit(1).execute()
        print(f"Success! Data: {res.data}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    main()
