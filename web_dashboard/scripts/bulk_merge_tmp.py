
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

from supabase_client import SupabaseClient

def main():
    print("="*60)
    print("BULK MERGE TMP POLITICIANS")
    print("="*60)
    
    matches_file = Path("web_dashboard/scripts/tmp_matches.json")
    if not matches_file.exists():
        print("Matches file not found!")
        return

    with open(matches_file, 'r') as f:
        matches = json.load(f)
        
    print(f"Loaded {len(matches)} matches to process.")
    
    client = SupabaseClient(use_service_role=True)
    
    merged_count = 0
    errors = 0
    
    for m in matches:
        pool_name = m['tmp_name']
        tmp_id = m['tmp_id']
        real_id = m['real_id']
        real_name = m['real_name']
        
        print(f"Processing: {pool_name} -> {real_name}")
        
        try:
            # 1. Move trades
            res = client.supabase.table('congress_trades')\
                .update({'politician_id': real_id})\
                .eq('politician_id', tmp_id)\
                .execute()
            
            # 2. Check committees (rare but possible)
            client.supabase.table('committee_assignments')\
                .update({'politician_id': real_id})\
                .eq('politician_id', tmp_id)\
                .execute()
                
            # 3. Delete TMP
            client.supabase.table('politicians').delete().eq('id', tmp_id).execute()
            
            print(f"  [OK] Merged.")
            merged_count += 1
            
        except Exception as e:
            print(f"  [ERROR] Failed to merge {pool_name}: {e}")
            errors += 1
            
    print("\n" + "="*60)
    print(f"COMPLETE. Merged: {merged_count}, Errors: {errors}")

if __name__ == "__main__":
    main()
