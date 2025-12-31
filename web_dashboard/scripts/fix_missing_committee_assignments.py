#!/usr/bin/env python3
"""Fix missing committee assignments for politicians in YAML"""
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set

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
from scripts.seed_committees import (
    load_committee_memberships,
    determine_chamber_from_code,
    match_committee_code_to_name,
    find_target_sectors
)

client = SupabaseClient(use_service_role=True)

print("="*70)
print("FIX MISSING COMMITTEE ASSIGNMENTS")
print("="*70)

# Load YAML data
memberships_file = project_root / 'data' / 'committee-membership-current.yaml'
if not memberships_file.exists():
    print(f"ERROR: Committee membership file not found: {memberships_file}")
    sys.exit(1)

memberships = load_committee_memberships(memberships_file)

# Get ALL politicians with bioguide IDs (not just newly inserted ones)
print("\nBuilding bioguide_id -> politician_id mapping...")
all_pols = client.supabase.table('politicians')\
    .select('id, bioguide_id')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

bioguide_to_id = {}
for row in all_pols.data:
    bioguide_to_id[row['bioguide_id']] = row['id']

print(f"   Mapped {len(bioguide_to_id)} politicians")

# Get existing committee assignments
print("\nGetting existing committee assignments...")
existing_ca = client.supabase.table('committee_assignments')\
    .select('politician_id, committee_id')\
    .execute()

existing_keys = {(ca['politician_id'], ca['committee_id']) for ca in existing_ca.data}
print(f"   Found {len(existing_keys)} existing assignments")

# Get committee IDs
print("\nGetting committee IDs...")
committees = client.supabase.table('committees')\
    .select('id, name, chamber')\
    .execute()

name_chamber_to_id = {}
for row in committees.data:
    key = (row['name'], row['chamber'])
    name_chamber_to_id[key] = row['id']

print(f"   Mapped {len(name_chamber_to_id)} committees")

# Process committee memberships
print("\nProcessing committee memberships...")
code_to_name = {}
new_assignments_dict = {}  # Use dict to deduplicate by (politician_id, committee_id)

for code, members in memberships.items():
    chamber = determine_chamber_from_code(code)
    committee_name = match_committee_code_to_name(code, chamber)
    
    if not committee_name:
        committee_name = f"Committee {code}"
    
    code_to_name[code] = committee_name
    committee_id = name_chamber_to_id.get((committee_name, chamber))
    
    if not committee_id:
        continue
    
    for member in members:
        bioguide = member.get('bioguide')
        if not bioguide or bioguide not in bioguide_to_id:
            continue
        
        politician_id = bioguide_to_id[bioguide]
        key = (politician_id, committee_id)
        
        if key not in existing_keys and key not in new_assignments_dict:
            new_assignments_dict[key] = {
                'politician_id': politician_id,
                'committee_id': committee_id,
                'rank': member.get('rank'),
                'title': member.get('title'),
                'party': member.get('party')
            }

new_assignments = list(new_assignments_dict.values())

print(f"   Found {len(new_assignments)} new assignments to create")

if not new_assignments:
    print("\n✅ No missing assignments found!")
    sys.exit(0)

# Insert new assignments
print(f"\nInserting {len(new_assignments)} new committee assignments...")
BATCH_SIZE = 100
inserted = 0

for i in range(0, len(new_assignments), BATCH_SIZE):
    batch = new_assignments[i:i+BATCH_SIZE]
    try:
        client.supabase.table('committee_assignments')\
            .upsert(batch, on_conflict='politician_id,committee_id')\
            .execute()
        inserted += len(batch)
        print(f"   Inserted batch {i//BATCH_SIZE + 1}/{(len(new_assignments) + BATCH_SIZE - 1)//BATCH_SIZE}: {len(batch)} assignments")
    except Exception as e:
        print(f"   [ERROR] Failed to insert batch: {e}")

print(f"\n✅ Successfully inserted {inserted} committee assignments")
print("="*70)

