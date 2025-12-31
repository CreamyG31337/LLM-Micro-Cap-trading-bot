#!/usr/bin/env python3
"""Generate accurate final list of politicians without committees"""
import sys
import yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

project_root = Path(__file__).parent.parent.parent

# Load YAML
memberships_file = project_root / 'data' / 'committee-membership-current.yaml'
with open(memberships_file, 'r', encoding='utf-8') as f:
    memberships = yaml.safe_load(f)

yaml_bioguides = set()
for code, members in memberships.items():
    for member in members:
        bioguide = member.get('bioguide')
        if bioguide:
            yaml_bioguides.add(bioguide)

client = SupabaseClient(use_service_role=True)

# Get all politicians with proper bioguide IDs
all_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

# Get politicians with committee assignments
ca_pols = client.supabase.table('committee_assignments')\
    .select('politician_id')\
    .execute()

pol_ids_with_ca = {ca['politician_id'] for ca in ca_pols.data}

# Find politicians in YAML but without DB committees
missing = []
for pol in all_pols.data:
    bioguide = pol.get('bioguide_id')
    if bioguide in yaml_bioguides and pol['id'] not in pol_ids_with_ca:
        missing.append(pol)

print("="*70)
print("POLITICIANS IN YAML BUT MISSING FROM DATABASE")
print("="*70)
print(f"\nTotal: {len(missing)}")
print(f"\n{'Name':<35} {'Bioguide':<12}")
print("-" * 50)

for pol in sorted(missing, key=lambda x: x['name']):
    print(f"{pol['name']:<35} {pol.get('bioguide_id', 'N/A'):<12}")

print("\n" + "="*70)

