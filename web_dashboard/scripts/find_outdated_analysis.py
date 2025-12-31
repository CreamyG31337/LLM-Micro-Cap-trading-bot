
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
from web_dashboard.scripts.seed_congress_trades import KNOWN_HISTORICAL_MAP

def main():
    print("="*60)
    print("SCANNING FOR OUTDATED ANALYSIS")
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

    # 2. Search for trades belonging to these politicians
    print("Fetching trade IDs...")
    trades = client.supabase.table('congress_trades')\
        .select('id')\
        .in_('politician_id', pol_ids)\
        .execute()
        
    trade_ids = [t['id'] for t in trades.data]
    print(f"  Found {len(trade_ids)} trades.")
    
    if not trade_ids:
        print("No trades found. Exiting.")
        return

    
    
    # 3. Direct ID Retrieval (Skip text search to fix timeout)
    # Since we restored these politicians, ALL their prior analysis is suspect/incomplete.
    # It is safer and cleaner to just wipe it all and let the system re-analyze with the new committee info.
    
    print(f"Retrieving analysis IDs for {len(trade_ids)} trades...")
    
    # Chunking just in case
    trade_id_chunks = [trade_ids[i:i + 200] for i in range(0, len(trade_ids), 200)]
    
    outdated_ids = []
    
    for idx, chunk in enumerate(trade_id_chunks):
        try:
            res = client.supabase.table('congress_trades_analysis')\
                .select('id')\
                .in_('trade_id', chunk)\
                .execute()
                
            chunk_ids = [r['id'] for r in res.data]
            outdated_ids.extend(chunk_ids)
            print(f"  Chunk {idx+1}/{len(trade_id_chunks)}: Found {len(chunk_ids)} records to wipe.")
            
        except Exception as e:
            print(f"  [ERROR] Chunk {idx+1} failed: {e}")
            
    print(f"\nFound {len(outdated_ids)} total analysis records to delete.")
    
    with open('web_dashboard/scripts/outdated_ids.json', 'w') as f:
        json.dump(outdated_ids, f)
    print("Saved IDs to web_dashboard/scripts/outdated_ids.json")
    
if __name__ == "__main__":
    main()
