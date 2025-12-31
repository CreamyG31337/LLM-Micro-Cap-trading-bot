
import sys
from pathlib import Path
import json
from datetime import datetime

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
    print("VERIFYING SUPABASE WRITES")
    client = SupabaseClient(use_service_role=True)
    
    # 1. Fetch one trade
    res = client.supabase.table("congress_trades").select("id, notes").limit(1).execute()
    if not res.data:
        print("No trades found to test.")
        return
        
    trade = res.data[0]
    tid = trade['id']
    old_notes = trade.get('notes')
    print(f"Testing update on Trade ID: {tid}")
    
    # 2. Attempt update (idempotent change)
    # We'll just set notes to what it already is, or append a space. 
    # Actually, let's just update 'notes' to itself.
    
    try:
        print("Attempting to update 'notes' field...")
        update_res = client.supabase.table("congress_trades")\
            .update({"notes": old_notes})\
            .eq("id", tid)\
            .execute()
            
        print("Success! Update returned:", update_res.data)
        print("\nCONCLUSION: No trigger is blocking updates.")
        
    except Exception as e:
        print(f"\nFAILED: Update blocked. Error: {e}")
        print("CONCLUSION: Trigger likely exists and is blocking writes.")

if __name__ == "__main__":
    main()
