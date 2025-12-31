#!/usr/bin/env python3
"""
Update temporary bioguide IDs by matching names to YAML data
"""
import sys
import yaml
from pathlib import Path
from typing import Dict, Optional

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

def parse_legislator_name(legislator: Dict) -> str:
    """Parse legislator name from YAML format."""
    name_parts = legislator.get('name', {})
    first = name_parts.get('first', '')
    last = name_parts.get('last', '')
    suffix = name_parts.get('suffix', '')
    
    if suffix:
        return f"{first} {last} {suffix}".strip()
    return f"{first} {last}".strip()

def get_current_term(legislator: Dict) -> Optional[Dict]:
    """Get current term from legislator data."""
    terms = legislator.get('terms', [])
    if not terms:
        return None
    
    # Get most recent term (assuming they're in order)
    return terms[-1] if terms else None

def load_legislators(file_path: Path) -> Dict[str, str]:
    """Load legislators and return name -> bioguide_id mapping."""
    print(f"Loading legislators from {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    name_to_bioguide = {}
    
    for legislator in data:
        term = get_current_term(legislator)
        if not term:
            continue
        
        bioguide_id = legislator.get('id', {}).get('bioguide')
        if not bioguide_id:
            continue
        
        name = parse_legislator_name(legislator)
        name_to_bioguide[name] = bioguide_id
    
    print(f"Loaded {len(name_to_bioguide)} current legislators")
    return name_to_bioguide

def update_politician_bioguide_ids(dry_run: bool = True):
    """Update politicians with temporary bioguide IDs."""
    client = SupabaseClient(use_service_role=True)
    
    # Load YAML data
    legislators_file = project_root / 'data' / 'legislators-current.yaml'
    if not legislators_file.exists():
        print(f"ERROR: Legislators file not found: {legislators_file}")
        return
    
    name_to_bioguide = load_legislators(legislators_file)
    
    # Find all politicians with temporary bioguide IDs
    print("\nFinding politicians with temporary bioguide IDs...")
    all_pols = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .not_.is_('bioguide_id', 'null')\
        .execute()
    
    tmp_pols = [p for p in all_pols.data if p.get('bioguide_id', '').startswith('TMP')]
    print(f"Found {len(tmp_pols)} politicians with temporary bioguide IDs")
    
    updates = []
    not_found = []
    
    for pol in tmp_pols:
        name = pol['name']
        current_bioguide = pol['bioguide_id']
        
        if name in name_to_bioguide:
            proper_bioguide = name_to_bioguide[name]
            updates.append({
                'id': pol['id'],
                'name': name,
                'old_bioguide': current_bioguide,
                'new_bioguide': proper_bioguide
            })
            print(f"  [MATCH] {name}: {current_bioguide} -> {proper_bioguide}")
        else:
            not_found.append({
                'id': pol['id'],
                'name': name,
                'bioguide': current_bioguide
            })
            print(f"  [NOT FOUND] {name} (not in YAML)")
    
    print(f"\nSummary: {len(updates)} can be updated, {len(not_found)} not found in YAML")
    
    if not updates:
        print("No updates to perform.")
        return
    
    if dry_run:
        print("\n[DRY RUN] Would update the following:")
        for u in updates[:10]:
            print(f"  ID {u['id']}: {u['name']} ({u['old_bioguide']} -> {u['new_bioguide']})")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
        print("\nUse --force to apply updates.")
        return
    
    # Apply updates
    print("\nUpdating bioguide IDs...")
    updated = 0
    for u in updates:
        try:
            client.supabase.table('politicians')\
                .update({'bioguide_id': u['new_bioguide']})\
                .eq('id', u['id'])\
                .execute()
            updated += 1
            if updated % 10 == 0:
                print(f"  Updated {updated}/{len(updates)}...")
        except Exception as e:
            print(f"  [ERROR] Failed to update ID {u['id']} ({u['name']}): {e}")
    
    print(f"\n[OK] Successfully updated {updated} politicians")
    print("\nNext step: Run seed_committees.py again to add committee assignments")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Update temporary bioguide IDs')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run mode (default)')
    parser.add_argument('--force', action='store_true', help='Actually apply changes')
    args = parser.parse_args()
    
    dry_run = not args.force
    
    if not dry_run:
        import sys
        if sys.stdin.isatty():
            response = input("\n⚠️  This will update bioguide IDs. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        else:
            print("\n⚠️  Running in non-interactive mode - proceeding with updates...")
    
    update_politician_bioguide_ids(dry_run=dry_run)


