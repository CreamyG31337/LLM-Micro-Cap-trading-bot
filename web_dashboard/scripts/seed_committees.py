#!/usr/bin/env python3
"""
Seed Committees Metadata
========================

Loads current US Congress members, committees, and assignments from YAML files
into the database. This enables Granite to calculate conflict scores for stock trades.

Inputs:
- data/legislators-current.yaml - Current Congress members
- data/committee-membership-current.yaml - Committee assignments
- data/committee_map.py - Committee name to sector mappings

Usage:
    python web_dashboard/scripts/seed_committees.py
"""

import sys
import os
import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import committee map
try:
    from data.committee_map import COMMITTEE_MAP
except ImportError:
    logger.error("Failed to import COMMITTEE_MAP from data.committee_map")
    COMMITTEE_MAP = {}


def get_current_term(legislator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract the current term for a legislator.
    Returns the most recent term that hasn't ended yet (or has end date in future).
    """
    terms = legislator.get('terms', [])
    if not terms:
        return None
    
    now = datetime.now()
    current_terms = []
    
    for term in terms:
        end_date_str = term.get('end')
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                if end_date > now:
                    current_terms.append(term)
            except ValueError:
                # If end date parsing fails, assume it's current
                current_terms.append(term)
        else:
            # No end date means current term
            current_terms.append(term)
    
    if not current_terms:
        return None
    
    # Return the most recent term (highest start date)
    return max(current_terms, key=lambda t: t.get('start', ''))


def parse_legislator_name(legislator: Dict[str, Any]) -> str:
    """Extract full name from legislator data."""
    name_data = legislator.get('name', {})
    # Prefer official_full, fallback to first + last
    if 'official_full' in name_data:
        return name_data['official_full']
    elif 'first' in name_data and 'last' in name_data:
        first = name_data.get('first', '')
        middle = name_data.get('middle', '')
        last = name_data.get('last', '')
        if middle:
            return f"{first} {middle} {last}".strip()
        return f"{first} {last}".strip()
    return 'Unknown'


def determine_chamber_from_term(term: Dict[str, Any]) -> str:
    """Determine chamber from term type."""
    term_type = term.get('type', '').lower()
    if term_type == 'sen':
        return 'Senate'
    elif term_type == 'rep':
        return 'House'
    else:
        return 'Unknown'


def determine_chamber_from_code(code: str) -> str:
    """Try to determine chamber from committee code."""
    if code.startswith('S'):
        return 'Senate'
    elif code.startswith('H'):
        return 'House'
    elif code.startswith('J'):
        return 'Senate'  # Joint committees - store under Senate to satisfy DB constraint
    else:
        return 'Senate'  # Default to Senate if unknown


# Standard Congress.gov/Thomas committee code mappings
# Base codes map to main committees; numbered suffixes are subcommittees
COMMITTEE_CODE_MAP = {
    # Senate Committees
    'SSAF': 'Senate Committee on Agriculture, Nutrition, and Forestry',
    'SSAP': 'Senate Committee on Appropriations',
    'SSAS': 'Senate Committee on Armed Services',
    'SSBK': 'Senate Committee on Banking, Housing, and Urban Affairs',
    'SSBU': 'Senate Committee on the Budget',
    'SSCM': 'Senate Committee on Commerce, Science, and Transportation',
    'SSEG': 'Senate Committee on Energy and Natural Resources',
    'SSEV': 'Senate Committee on Environment and Public Works',
    'SSFI': 'Senate Committee on Finance',
    'SSFR': 'Senate Committee on Foreign Relations',
    'SSGA': 'Senate Committee on Homeland Security and Governmental Affairs',
    'SSHR': 'Senate Committee on Health, Education, Labor, and Pensions',
    'SSJU': 'Senate Committee on the Judiciary',
    'SSRA': 'Senate Committee on Rules and Administration',
    'SSSB': 'Senate Committee on Small Business and Entrepreneurship',
    'SSVA': "Senate Committee on Veterans' Affairs",
    'SLIA': 'Senate Committee on Indian Affairs',
    'SLET': 'Senate Select Committee on Ethics',
    'SLIN': 'Senate Select Committee on Intelligence',
    'SPAG': 'Senate Special Committee on Aging',
    'SCNC': 'Senate Caucus on International Narcotics Control',
    
    # House Committees
    'HSAG': 'House Committee on Agriculture',
    'HSAP': 'House Committee on Appropriations',
    'HSAS': 'House Committee on Armed Services',
    'HSBA': 'House Committee on Financial Services',
    'HSBU': 'House Committee on the Budget',
    'HSED': 'House Committee on Education and the Workforce',
    'HSFA': 'House Committee on Foreign Affairs',
    'HSGO': 'House Committee on Oversight and Accountability',
    'HSHA': 'House Committee on House Administration',
    'HSHM': 'House Committee on Homeland Security',
    'HSIF': 'House Committee on Energy and Commerce',
    'HSII': 'House Committee on Natural Resources',
    'HSJU': 'House Committee on the Judiciary',
    'HSPW': 'House Committee on Transportation and Infrastructure',
    'HSRU': 'House Committee on Rules',
    'HSSM': 'House Committee on Small Business',
    'HSSY': 'House Committee on Science, Space, and Technology',
    'HSVR': "House Committee on Veterans' Affairs",
    'HSWM': 'House Committee on Ways and Means',
    'HLIG': 'House Permanent Select Committee on Intelligence',
}


def match_committee_code_to_name(code: str, chamber: str) -> Optional[str]:
    """
    Match a committee code to a full committee name.
    Uses direct lookup for base codes; subcommittees inherit parent name.
    """
    code_upper = code.upper()
    
    # Direct lookup first
    if code_upper in COMMITTEE_CODE_MAP:
        result = COMMITTEE_CODE_MAP[code_upper]
        logger.debug(f"Direct match: {code} -> {result}")
        return result
    
    # For subcommittees (e.g., SSAP01), strip numeric suffix and lookup parent
    # Pattern: base code (4 letters) + optional numeric suffix
    import re
    match = re.match(r'^([A-Z]{4})(\d+)?$', code_upper)
    if match:
        base_code = match.group(1)
        if base_code in COMMITTEE_CODE_MAP:
            suffix = match.group(2)
            if suffix:
                result = f"{COMMITTEE_CODE_MAP[base_code]} - Subcommittee"
                logger.debug(f"Subcommittee match: {code} -> {result}")
                return result
            return COMMITTEE_CODE_MAP[base_code]
    
    logger.debug(f"No match for: {code}")
    return None


def find_target_sectors(committee_name: str) -> Optional[List[str]]:
    """
    Find target sectors for a committee name with fallback matching.
    - Tries exact match first
    - For subcommittees, strips "- Subcommittee" suffix and matches parent committee
    - Uses case-insensitive matching as fallback
    Returns None only if truly no match found.
    """
    # Try exact match first
    if committee_name in COMMITTEE_MAP:
        return COMMITTEE_MAP[committee_name]
    
    # For subcommittees, strip "- Subcommittee" suffix and try parent committee
    if committee_name.endswith(" - Subcommittee"):
        parent_name = committee_name.rsplit(" - Subcommittee", 1)[0]  # Remove " - Subcommittee" suffix
        if parent_name in COMMITTEE_MAP:
            logger.debug(f"Subcommittee match: {committee_name} -> {parent_name}")
            return COMMITTEE_MAP[parent_name]
    
    # Try case-insensitive match as fallback
    committee_name_lower = committee_name.lower()
    for map_name, sectors in COMMITTEE_MAP.items():
        if map_name.lower() == committee_name_lower:
            logger.debug(f"Case-insensitive match: {committee_name} -> {map_name}")
            return sectors
    
    # Try case-insensitive match for subcommittees
    if committee_name_lower.endswith(" - subcommittee"):
        parent_name_lower = committee_name_lower.rsplit(" - subcommittee", 1)[0]
        for map_name, sectors in COMMITTEE_MAP.items():
            if map_name.lower() == parent_name_lower:
                logger.debug(f"Case-insensitive subcommittee match: {committee_name} -> {map_name}")
                return sectors
    
    # No match found
    logger.debug(f"No target_sectors match for: {committee_name}")
    return None


def load_legislators(file_path: Path) -> List[Dict[str, Any]]:
    """Load and parse legislators-current.yaml file."""
    logger.info(f"Loading legislators from {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"Legislators file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    current_legislators = []
    
    for legislator in data:
        term = get_current_term(legislator)
        if not term:
            continue
        
        bioguide_id = legislator.get('id', {}).get('bioguide')
        if not bioguide_id:
            continue
        
        name = parse_legislator_name(legislator)
        party = term.get('party', 'Unknown')
        state = term.get('state', '')
        chamber = determine_chamber_from_term(term)
        
        current_legislators.append({
            'bioguide_id': bioguide_id,
            'name': name,
            'party': party,
            'state': state,
            'chamber': chamber
        })
    
    logger.info(f"Found {len(current_legislators)} current legislators")
    return current_legislators


def load_committee_memberships(file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load and parse committee-membership-current.yaml file."""
    logger.info(f"Loading committee memberships from {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"Committee membership file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data  # Returns dict with committee codes as keys


def insert_politicians(client: SupabaseClient, legislators: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Insert politicians into database using batch upsert.
    Returns mapping of bioguide_id to database id.
    """
    logger.info(f"Inserting {len(legislators)} politicians (batch mode)...")
    
    # Prepare all records for batch upsert
    records = []
    for leg in legislators:
        records.append({
            'name': leg['name'],
            'bioguide_id': leg['bioguide_id'],
            'party': leg['party'],
            'state': leg['state'],
            'chamber': leg['chamber'],
            'updated_at': datetime.now().isoformat()
        })
    
    # Batch upsert (much faster than one-by-one)
    BATCH_SIZE = 100
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        try:
            client.supabase.table('politicians')\
                .upsert(batch, on_conflict='bioguide_id')\
                .execute()
            logger.info(f"  Upserted batch {i//BATCH_SIZE + 1}/{(len(records) + BATCH_SIZE - 1)//BATCH_SIZE}")
        except Exception as e:
            logger.error(f"Error upserting politician batch: {e}")
    
    # Fetch all politician IDs for mapping
    bioguide_to_id = {}
    try:
        result = client.supabase.table('politicians')\
            .select('id, bioguide_id')\
            .execute()
        for row in result.data:
            bioguide_to_id[row['bioguide_id']] = row['id']
    except Exception as e:
        logger.error(f"Error fetching politician IDs: {e}")
    
    logger.info(f"  Mapped {len(bioguide_to_id)} politicians")
    return bioguide_to_id


def insert_committees_and_assignments(
    client: SupabaseClient,
    memberships: Dict[str, List[Dict[str, Any]]],
    bioguide_to_id: Dict[str, int]
) -> Dict[str, int]:
    """
    Insert committees and their assignments using batch operations.
    Returns mapping of committee code to database id.
    """
    logger.info("Inserting committees and assignments (batch mode)...")
    
    code_to_id = {}
    code_to_name = {}  # Track code→name for assignment lookup
    unmapped_codes = []
    
    # Step 1: Prepare all committee records (deduplicated by name+chamber)
    seen_committees = {}  # key: (name, chamber), value: record
    for code, members in memberships.items():
        chamber = determine_chamber_from_code(code)
        committee_name = match_committee_code_to_name(code, chamber)
        
        if not committee_name:
            committee_name = f"Committee {code}"
            unmapped_codes.append(code)
        
        code_to_name[code] = committee_name
        
        key = (committee_name, chamber)
        if key not in seen_committees:
            # Use improved matching function that handles subcommittees
            target_sectors = find_target_sectors(committee_name)
            # Use empty array [] instead of None to match schema default
            if target_sectors is None:
                target_sectors = []
            seen_committees[key] = {
                'name': committee_name,
                'code': code,  # Use first code encountered
                'chamber': chamber,
                'target_sectors': target_sectors,
                'updated_at': datetime.now().isoformat()
            }
    
    committee_records = list(seen_committees.values())
    logger.info(f"  Prepared {len(committee_records)} unique committees from {len(memberships)} codes")
    
    # Step 2: Batch upsert committees
    BATCH_SIZE = 50
    for i in range(0, len(committee_records), BATCH_SIZE):
        batch = committee_records[i:i+BATCH_SIZE]
        try:
            client.supabase.table('committees')\
                .upsert(batch, on_conflict='name,chamber')\
                .execute()
            logger.info(f"  Committees batch {i//BATCH_SIZE + 1}/{(len(committee_records) + BATCH_SIZE - 1)//BATCH_SIZE}")
        except Exception as e:
            logger.error(f"Error upserting committee batch: {e}")
    
    # Step 3: Fetch all committee IDs by name+chamber
    name_chamber_to_id = {}
    try:
        result = client.supabase.table('committees')\
            .select('id, name, chamber')\
            .execute()
        for row in result.data:
            key = (row['name'], row['chamber'])
            name_chamber_to_id[key] = row['id']
    except Exception as e:
        logger.error(f"Error fetching committee IDs: {e}")
    
    logger.info(f"  Mapped {len(name_chamber_to_id)} committees")
    
    # Step 4: Prepare all assignment records (deduplicated by politician_id, committee_id)
    seen_assignments = {}  # key: (politician_id, committee_id)
    for code, members in memberships.items():
        # Look up committee by name (which we tracked earlier)
        committee_name = code_to_name.get(code)
        if not committee_name:
            continue
        chamber = determine_chamber_from_code(code)
        committee_id = name_chamber_to_id.get((committee_name, chamber))
        if not committee_id:
            continue
        
        # Track for return value
        code_to_id[code] = committee_id
        
        for member in members:
            bioguide = member.get('bioguide')
            if not bioguide or bioguide not in bioguide_to_id:
                continue
            
            politician_id = bioguide_to_id[bioguide]
            key = (politician_id, committee_id)
            if key not in seen_assignments:
                seen_assignments[key] = {
                    'politician_id': politician_id,
                    'committee_id': committee_id,
                    'rank': member.get('rank'),
                    'title': member.get('title'),
                    'party': member.get('party')
                }
    
    assignment_records = list(seen_assignments.values())
    
    # Step 5: Batch upsert assignments
    for i in range(0, len(assignment_records), BATCH_SIZE):
        batch = assignment_records[i:i+BATCH_SIZE]
        try:
            client.supabase.table('committee_assignments')\
                .upsert(batch, on_conflict='politician_id,committee_id')\
                .execute()
            logger.info(f"  Assignments batch {i//BATCH_SIZE + 1}/{(len(assignment_records) + BATCH_SIZE - 1)//BATCH_SIZE}")
        except Exception as e:
            logger.error(f"Error upserting assignment batch: {e}")
    
    logger.info(f"  Total assignments: {len(assignment_records)}")
    if unmapped_codes:
        logger.warning(f"  Unmapped committee codes: {len(unmapped_codes)}")
    
    return code_to_id


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Congress Committees Metadata Seeder")
    logger.info("=" * 60)
    
    # File paths
    data_dir = project_root / 'data'
    legislators_file = data_dir / 'legislators-current.yaml'
    memberships_file = data_dir / 'committee-membership-current.yaml'
    
    # Validate files exist
    if not legislators_file.exists():
        logger.error(f"Legislators file not found: {legislators_file}")
        sys.exit(1)
    
    if not memberships_file.exists():
        logger.error(f"Committee membership file not found: {memberships_file}")
        sys.exit(1)
    
    # Initialize database client
    try:
        client = SupabaseClient(use_service_role=True)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # Step 1: Load and insert politicians
        legislators = load_legislators(legislators_file)
        bioguide_to_id = insert_politicians(client, legislators)
        
        # Step 2: Load committee memberships
        memberships = load_committee_memberships(memberships_file)
        
        # Step 3: Insert committees and assignments
        code_to_id = insert_committees_and_assignments(client, memberships, bioguide_to_id)
        
        logger.info("=" * 60)
        logger.info("✅ Seeding complete!")
        logger.info(f"   Politicians: {len(bioguide_to_id)}")
        logger.info(f"   Committees: {len(code_to_id)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

