#!/usr/bin/env python3
"""Check if politicians without committees are actually in the YAML committee data"""
import sys
import yaml
from pathlib import Path
from typing import Dict, Set

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient

def load_committee_memberships(file_path: Path) -> Dict[str, Set[str]]:
    """Load committee memberships and return bioguide_id -> set of committee codes."""
    print(f"Loading committee memberships from {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    bioguide_to_committees: Dict[str, Set[str]] = {}
    
    # data is a dict with committee codes as keys
    for committee_code, members in data.items():
        if not isinstance(members, list):
            continue
        
        for member in members:
            bioguide_id = member.get('bioguide')
            if bioguide_id:
                if bioguide_id not in bioguide_to_committees:
                    bioguide_to_committees[bioguide_id] = set()
                bioguide_to_committees[bioguide_id].add(committee_code)
    
    print(f"Loaded committee memberships for {len(bioguide_to_committees)} politicians")
    return bioguide_to_committees

client = SupabaseClient(use_service_role=True)

# Load YAML data
memberships_file = project_root / 'data' / 'committee-membership-current.yaml'
if not memberships_file.exists():
    print(f"ERROR: Committee membership file not found: {memberships_file}")
    sys.exit(1)

yaml_bioguide_to_committees = load_committee_memberships(memberships_file)

# Get politicians with proper bioguide IDs but no committees
proper_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

# Get politicians with committee assignments
pols_with_ca = client.supabase.table('committee_assignments')\
    .select('politician_id')\
    .execute()

pol_ids_with_ca = {ca['politician_id'] for ca in pols_with_ca.data}

# Find politicians with proper bioguide but no committees
pols_without_ca = [
    p for p in proper_pols.data 
    if p['id'] not in pol_ids_with_ca
]

print("\n" + "="*70)
print("ANALYSIS: Politicians with proper bioguide IDs but no committees")
print("="*70)

# Check if they're in YAML
in_yaml_but_no_db_ca = []
not_in_yaml = []

for pol in pols_without_ca:
    bioguide = pol.get('bioguide_id')
    if bioguide in yaml_bioguide_to_committees:
        in_yaml_but_no_db_ca.append((pol, yaml_bioguide_to_committees[bioguide]))
    else:
        not_in_yaml.append(pol)

print(f"\nTotal politicians with proper bioguide IDs but no DB committees: {len(pols_without_ca)}")
print(f"  - In YAML committee data but missing from DB: {len(in_yaml_but_no_db_ca)} ⚠️")
print(f"  - Not in YAML committee data (expected): {len(not_in_yaml)}")

if in_yaml_but_no_db_ca:
    print("\n" + "="*70)
    print("⚠️  ISSUE: Politicians in YAML but missing from database committee assignments:")
    print("="*70)
    print(f"{'Name':<35} {'Bioguide':<12} {'YAML Committees':<20}")
    print("-" * 70)
    
    # Sort by number of committees in YAML
    in_yaml_but_no_db_ca.sort(key=lambda x: len(x[1]), reverse=True)
    
    for pol, yaml_committees in in_yaml_but_no_db_ca[:30]:
        name = pol['name'][:34]
        bioguide = pol.get('bioguide_id', 'N/A')[:11]
        comm_count = len(yaml_committees)
        print(f"{name:<35} {bioguide:<12} {comm_count} committees")
    
    if len(in_yaml_but_no_db_ca) > 30:
        print(f"\n... and {len(in_yaml_but_no_db_ca) - 30} more")

if not_in_yaml:
    print("\n" + "="*70)
    print("Politicians NOT in YAML committee data (expected - may not be on committees):")
    print("="*70)
    print(f"Total: {len(not_in_yaml)}")
    print("(These are likely not currently serving on committees)")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
if in_yaml_but_no_db_ca:
    print(f"⚠️  FOUND ISSUE: {len(in_yaml_but_no_db_ca)} politicians are in YAML committee data")
    print("   but don't have committee assignments in the database.")
    print("   This suggests seed_committees.py didn't process them correctly.")
else:
    print("✅ All politicians in YAML committee data have database assignments.")
    print(f"   The {len(not_in_yaml)} without assignments are not in YAML (expected).")
print("="*70)


