
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
from web_dashboard.scripts.seed_congress_trades import KNOWN_HISTORICAL_MAP

def main():
    print("="*60)
    print("WIPING OUTDATED ANALYSIS FROM congress_trades")
    print("="*60)
    
    client = SupabaseClient(use_service_role=True)
    
    # 1. Get IDs of the restored politicians
    print("Fetching IDs for restored politicians...")
    target_bioguides = [m['bioguide'] for m in KNOWN_HISTORICAL_MAP.values()]
    
    pols = client.supabase.table('politicians')\
        .select('id, name')\
        .in_('bioguide_id', target_bioguides)\
        .execute()
        
    pol_ids = [p['id'] for p in pols.data]
    print(f"  Found {len(pol_ids)} restored politician IDs.")
    
    if not pol_ids:
        print("No politicians found. Exiting.")
        return

    # 2. Count trades before update
    count_res = client.supabase.table('congress_trades')\
        .select('count', count='exact')\
        .in_('politician_id', pol_ids)\
        .not_.is_('reasoning', 'null')\
        .execute()
        
    print(f"  Found {count_res.count} trades with existing analysis to wipe.")
    
    if count_res.count == 0:
        print("Nothing to wipe.")
        return

    # 3. Perform Update
    # We update reasoning -> NULL, risk_pattern -> NULL
    # Using batches to be safe, though a single update might work for 2000 rows.
    # Supabase/PostgREST usually handles a few thousand rows fine. 
    # Let's try direct update.
    
    print("Executing Wipe...")
    try:
        res = client.supabase.table('congress_trades')\
            .update({'reasoning': None})\
            .in_('politician_id', pol_ids)\
            .execute()
            
        # Note: .update() returns modified rows by default in JS client, 
        # python client behavior: returns data list.
        print(f"  Success! Wiped analysis for {len(res.data)} trades.")
        
    except Exception as e:
        print(f"  [ERROR] Update failed: {e}")
            
    print("\n" + "="*60)
    print("COMPLETE.")

if __name__ == "__main__":
    main()
