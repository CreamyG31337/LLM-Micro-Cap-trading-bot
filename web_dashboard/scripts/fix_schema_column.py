
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient

def main():
    print("ATTEMPTING DDL via RPC")
    client = SupabaseClient(use_service_role=True)
    
    # Try different common names for SQL execution functions
    sql = "ALTER TABLE congress_trades ADD COLUMN IF NOT EXISTS risk_pattern text;"
    
    try:
        print("Trying 'exec_sql'...")
        res = client.supabase.rpc('exec_sql', {'sql': sql}).execute()
        print(f"Success: {res.data}")
        return
    except Exception as e:
        print(f"Failed exec_sql: {e}")
        
    try:
        print("Trying 'execute_sql'...")
        res = client.supabase.rpc('execute_sql', {'query': sql}).execute()
        print(f"Success: {res.data}")
        return
    except Exception as e:
        print(f"Failed execute_sql: {e}")
        
    print("\nCould not execute DDL via RPC. User must run manually.")

if __name__ == "__main__":
    main()
