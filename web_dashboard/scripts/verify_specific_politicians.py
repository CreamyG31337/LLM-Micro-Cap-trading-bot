
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

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

target_ids = {
    'C001078': 'Gerry Connolly',
    'S001209': 'Abigail Spanberger',
    'P000197': 'Nancy Pelosi',
    'G000606': 'Adelita S. Grijalva',
    'V000139': 'Matt Van Epps',
    'R000305': 'Deborah Ross',
    'S001176': 'Steve Scalise',
    'C001101': 'Katherine M. Clark',
    'J000299': 'Mike Johnson',
    'J000294': 'Hakeem S. Jeffries',
    'V000137': 'J.D. Vance',
    'B001227': 'Earl Blumenauer',
    'R000595': 'Marco Rubio',
    'G000590': 'Mark Green',
    'D000620': 'John Delaney',
    'T000486': 'David Trone',
    'C001124': 'Gilbert Cisneros',
    'C000174': 'Thomas Carper',
    'B001248': 'Michael Burgess',
    'L000564': 'Douglas Lamborn',
    'G000577': 'Garret Graves'
}

print(f"Checking {len(target_ids)} specific politicians...")

# fetch politicians
pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .in_('bioguide_id', list(target_ids.keys()))\
    .execute()

found_bioguides = set()
for p in pols.data:
    bg = p['bioguide_id']
    found_bioguides.add(bg)
    print(f"\n[FOUND] {p['name']} ({bg}) - ID: {p['id']}")
    
    # Check committees
    
    committees = client.supabase.table('committee_assignments')\
        .select('*, committees(name)')\
        .eq('politician_id', p['id'])\
        .execute()
        
    if committees.data:
        print(f"  Committees ({len(committees.data)}):")
        for c in committees.data:
             print(f"    - {c['committees']['name']}")
    else:
        print("  NO COMMITTEES FOUND IN DB")

# Check for missing
missing = set(target_ids.keys()) - found_bioguides
if missing:
    print(f"\n[MISSING] Could not find these bioguide IDs in DB: {missing}")

# Check specifically for Deborah Ross by name if TMP ID failed
if 'TMP877301' in missing:
    print("\nChecking Deborah Ross by name...")
    ross = client.supabase.table('politicians').select('*').ilike('name', '%Deborah Ross%').execute()
    for r in ross.data:
        print(f"  Found: {r['name']} - Bioguide: {r['bioguide_id']} - ID: {r['id']}")

