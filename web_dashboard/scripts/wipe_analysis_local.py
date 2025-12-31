
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
from postgres_client import PostgresClient
from web_dashboard.scripts.seed_congress_trades import KNOWN_HISTORICAL_MAP

def main():
    print("="*60)
    print("WIPING OUTDATED ANALYSIS (LOCAL POSTGRES)")
    print("="*60)
    
    # 1. Fetch Target Trades from Supabase
    supabase = SupabaseClient(use_service_role=True)
    print("Fetching IDs for restored politicians from Supabase...")
    
    target_bioguides = [m['bioguide'] for m in KNOWN_HISTORICAL_MAP.values()]
    
    pols = supabase.supabase.table('politicians')\
        .select('id, name')\
        .in_('bioguide_id', target_bioguides)\
        .execute()
        
    pol_ids = [p['id'] for p in pols.data]
    print(f"  Found {len(pol_ids)} restored politician IDs.")
    
    if not pol_ids:
        print("No restored politicians found. Exiting.")
        return

    print("Fetching trade IDs for these politicians...")
    # Fetch all trades
    all_trade_ids = []
    
    # Pagination to be safe
    offset = 0
    limit = 1000
    while True:
        res = supabase.supabase.table('congress_trades')\
            .select('id')\
            .in_('politician_id', pol_ids)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        if not res.data:
            break
            
        batch_ids = [t['id'] for t in res.data]
        all_trade_ids.extend(batch_ids)
        if len(res.data) < limit:
            break
        offset += limit
            
    print(f"  Found {len(all_trade_ids)} trades involved.")
    
    if not all_trade_ids:
        print("No trades found. Nothing to wipe.")
        return

    # 2. Wipe Analysis from Local Postgres
    print("\nConnecting to Local Postgres...")
    try:
        pg = PostgresClient()
    except Exception as e:
        print(f"Failed to connect to Local Postgres: {e}")
        return
        
    print(f"Deleting analysis for {len(all_trade_ids)} trades...")
    
    # Batch delete
    batch_size = 500
    total_deleted = 0
    
    chunks = [all_trade_ids[i:i + batch_size] for i in range(0, len(all_trade_ids), batch_size)]
    
    for idx, chunk in enumerate(chunks):
        try:
            # We need to format the list of IDs for SQL IN clause
            # execute_update expects a query string.
            # We can use ANY(%s) for array parameter
            
            query = "DELETE FROM congress_trades_analysis WHERE trade_id = ANY(%s)"
            
            count = pg.execute_update(query, (chunk,))
            total_deleted += count
            print(f"  Chunk {idx+1}/{len(chunks)}: Deleted {count} analysis records.")
            
        except Exception as e:
            print(f"  [ERROR] Chunk {idx+1} failed: {e}")
            
    print("\n" + "="*60)
    print(f"COMPLETE. Total Analysis Records Deleted: {total_deleted}")
    print("Run `analyze_congress_trades_batch.py` to regenerate analysis with correct committee data.")

if __name__ == "__main__":
    main()
