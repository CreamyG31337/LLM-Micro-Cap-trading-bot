import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*70)
print("VERIFYING POLITICIAN INTEGRITY (FK CHECK)")
print("="*70)

# 1. Check trades without politician_id
print("1️⃣  Checking for trades with NULL politician_id...")
null_fk_result = client.supabase.table('congress_trades')\
    .select('politician')\
    .is_('politician_id', 'null')\
    .execute()

if not null_fk_result.data:
    print("   ✅ ALL trades have a politician_id!")
else:
    print(f"   ❌ Found {len(null_fk_result.data)} trades with missing politician_id:")
    
    # Analyze failures
    null_fk_counts = defaultdict(int)
    for t in null_fk_result.data:
        null_fk_counts[t['politician']] += 1
        
    for pol, count in sorted(null_fk_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      - {pol}: {count} trades")

# 2. Check for Orphaned IDs (politician_id exists but points to non-existent politician? FK constraint prevents this, but good to know)
# We can skip this as the database enforces it.

# 3. Check Politicians without Committees
print("\n2️⃣  Checking for politicians without committee assignments...")

# Get all politician IDs referenced in trades
referenced_pols = set()
trades_pols = client.supabase.table('congress_trades')\
    .select('politician_id')\
    .not_.is_('politician_id', 'null')\
    .execute()

for t in trades_pols.data:
    referenced_pols.add(t['politician_id'])

print(f"   {len(referenced_pols)} unique politicians found in trade history.")

# Get politicians with committees
pols_with_committees = set()
assignments = client.supabase.table('committee_assignments').select('politician_id').execute()
for a in assignments.data:
    pols_with_committees.add(a['politician_id'])

# Find intersection issues
active_without_committees = []
for pid in referenced_pols:
    if pid not in pols_with_committees:
        active_without_committees.append(pid)

if not active_without_committees:
    print("   ✅ All active traders have committee assignments!")
else:
    print(f"   ⚠️  {len(active_without_committees)} active traders missing committee data.")
    
    # Resolve names for report
    if len(active_without_committees) > 0:
        print("   fetching names...")
        names_result = client.supabase.table('politicians')\
            .select('id, name, bioguide_id')\
            .in_('id', active_without_committees[:20])\
            .execute()
        
        for p in names_result.data:
            print(f"      - {p['name']} (ID: {p['bioguide_id']})")
            
        if len(active_without_committees) > 20:
            print(f"      ... and {len(active_without_committees) - 20} more.")

print("\n" + "="*70)
