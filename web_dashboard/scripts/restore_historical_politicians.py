
import sys
from pathlib import Path
from datetime import datetime
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
        # Fallback for older python
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient
from web_dashboard.scripts.seed_congress_trades import KNOWN_HISTORICAL_MAP, normalize_politician_name

def main():
    print("="*60)
    print("RESTORING HISTORICAL POLITICIANS")
    print("="*60)
    
    client = SupabaseClient(use_service_role=True)
    
    restored_count = 0
    merged_count = 0
    
    for name, metadata in KNOWN_HISTORICAL_MAP.items():
        print(f"\nProcessing: {name.title()} ({metadata['bioguide']})")
        
        # 1. Ensure Real Record Exists
        real_rec = client.supabase.table('politicians').select('*').eq('bioguide_id', metadata['bioguide']).execute()
        
        if real_rec.data:
            real_id = real_rec.data[0]['id']
            print(f"  [OK] Real record exists: ID {real_id}")
        else:
            print(f"  [MISSING] Creating real record...")
            new_pol = {
                'name': name.title(), # Estimate proper casing
                'bioguide_id': metadata['bioguide'],
                'party': metadata['party'],
                'state': metadata['state'],
                'chamber': metadata['chamber'],
                'updated_at': datetime.now().isoformat()
            }
            res = client.supabase.table('politicians').insert(new_pol).execute()
            if res.data:
                real_id = res.data[0]['id']
                print(f"  [CREATED] ID {real_id}")
                restored_count += 1
            else:
                print("  [ERROR] Failed to create record.")
                continue

        # 2. Find any TMPs matching this name?
        # We search by the name key we have (e.g. "earl blumenauer")
        # AND by the broader "TMP%" check
        
        # Search for TMPs with similar names
        tmps = client.supabase.table('politicians').select('*')\
            .ilike('bioguide_id', 'TMP%')\
            .ilike('name', f"%{name}%")\
            .execute()
            
        if not tmps.data:
            # Try normalized matching logic just in case
            pass
            
        for tmp in tmps.data:
            tmp_id = tmp['id']
            if tmp_id == real_id: continue # Should not happen due to TMP filter
            
            print(f"  [FOUND TMP] {tmp['name']} (ID: {tmp_id}) - Merging...")
            
            # Move trades
            client.supabase.table('congress_trades')\
                .update({'politician_id': real_id})\
                .eq('politician_id', tmp_id)\
                .execute()
                
            # Delete TMP
            client.supabase.table('politicians').delete().eq('id', tmp_id).execute()
            print(f"  [MERGED] Done.")
            merged_count += 1

    print("\n" + "="*60)
    print(f"COMPLETE. Restored: {restored_count}, TMPs Merged: {merged_count}")

if __name__ == "__main__":
    main()
