
import sys
from pathlib import Path
import yaml
from datetime import datetime

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

print("="*60)
print("MERGING DEBORAH ROSS")
print("="*60)

# 1. Get TMP Ross
print("\nFetching TMP Ross...")
tmp_ross = client.supabase.table('politicians').select('*').ilike('bioguide_id', 'TMP%').ilike('name', '%Deborah Ross%').execute()
if not tmp_ross.data:
    print("TMP Ross not found. Already fixed?")
    tmp_id = None
else:
    tmp_rec = tmp_ross.data[0]
    tmp_id = tmp_rec['id']
    print(f"Found TMP Ross: {tmp_rec['name']} (ID: {tmp_id}, Bioguide: {tmp_rec['bioguide_id']})")

# 2. Get Real Ross (R000305)
print("\nFetching Real Ross (R000305)...")
real_ross = client.supabase.table('politicians').select('*').eq('bioguide_id', 'R000305').execute()

real_id = None
if real_ross.data:
    real_rec = real_ross.data[0]
    real_id = real_rec['id']
    print(f"Found Real Ross: {real_rec['name']} (ID: {real_id})")
else:
    print("Real Ross not found in DB. Inserting from YAML data...")
    # Manually construct based on YAML lookup knowledge
    # name: Deborah Ross
    # bioguide: R000305
    # party: Democrat
    # state: NC
    # chamber: House
    new_pol = {
        'name': 'Deborah Ross',
        'bioguide_id': 'R000305',
        'party': 'Democrat',
        'state': 'NC',
        'chamber': 'House',
        'updated_at': datetime.now().isoformat()
    }
    res = client.supabase.table('politicians').insert(new_pol).execute()
    if res.data:
        real_id = res.data[0]['id']
        print(f"Inserted Real Ross: ID {real_id}")
    else:
        print("Failed to insert Real Ross")
        sys.exit(1)

# 3. Move trades
if tmp_id and real_id:
    print(f"\nMoving trades from TMP ({tmp_id}) to Real ({real_id})...")
    
    # Check count first
    trades = client.supabase.table('congress_trades').select('id', count='exact').eq('politician_id', tmp_id).execute()
    count = trades.count if hasattr(trades, 'count') else len(trades.data)
    print(f"Found {count} trades to move.")
    
    if count > 0:
        # Update trades
        upd = client.supabase.table('congress_trades')\
            .update({'politician_id': real_id})\
            .eq('politician_id', tmp_id)\
            .execute()
        print(f"Moved trades.")
    
    # 4. Check Committee Assignments for TMP?
    # Usually TMP has none (that was the original issue), but good to check
    ca = client.supabase.table('committee_assignments').select('id', count='exact').eq('politician_id', tmp_id).execute()
    ca_count = ca.count if hasattr(ca, 'count') else len(ca.data)
    if ca_count > 0:
        print(f"Moving {ca_count} committee assignments...")
        client.supabase.table('committee_assignments')\
            .update({'politician_id': real_id})\
            .eq('politician_id', tmp_id)\
            .execute()

    # 5. Delete TMP politician
    print("\nDeleting TMP Ross record...")
    client.supabase.table('politicians').delete().eq('id', tmp_id).execute()
    print("Deleted.")

print("\nDone.")
