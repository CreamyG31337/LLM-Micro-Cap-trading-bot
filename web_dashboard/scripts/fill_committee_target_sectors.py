#!/usr/bin/env python3
"""
Fill Committee Target Sectors
=============================

Updates existing committees in the database with target_sectors from committee_map.py.
This script fixes null target_sectors values that may have been missed during seeding.

Usage:
    python web_dashboard/scripts/fill_committee_target_sectors.py
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

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
            logger.info(f"Subcommittee match: {committee_name} -> {parent_name}")
            return COMMITTEE_MAP[parent_name]
        else:
            logger.warning(f"Subcommittee parent not found: '{parent_name}' (from '{committee_name}')")
    
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


def fill_null_target_sectors(client: SupabaseClient) -> Dict[str, Any]:
    """
    Find all committees with null target_sectors and update them.
    Returns statistics about the update operation.
    """
    logger.info("=" * 60)
    logger.info("Filling Null Committee Target Sectors")
    logger.info("=" * 60)
    
    # Fetch all committees with null target_sectors
    try:
        result = client.supabase.table('committees')\
            .select('id, name, chamber, code, target_sectors')\
            .is_('target_sectors', 'null')\
            .execute()
        
        committees = result.data
        logger.info(f"Found {len(committees)} committees with null target_sectors")
        
    except Exception as e:
        logger.error(f"Error fetching committees: {e}")
        return {'error': str(e)}
    
    if not committees:
        logger.info("No committees with null target_sectors found. All done!")
        return {
            'total': 0,
            'matched': 0,
            'unmatched': 0,
            'updated': 0,
            'errors': 0
        }
    
    # Process each committee
    matched = []
    unmatched = []
    updates = []
    
    for committee in committees:
        committee_id = committee['id']
        committee_name = committee['name']
        chamber = committee.get('chamber', 'Unknown')
        code = committee.get('code', 'N/A')
        
        # Find target sectors
        target_sectors = find_target_sectors(committee_name)
        
        if target_sectors is not None:
            matched.append({
                'id': committee_id,
                'name': committee_name,
                'chamber': chamber,
                'code': code,
                'target_sectors': target_sectors
            })
            updates.append({
                'id': committee_id,
                'target_sectors': target_sectors,
                'updated_at': datetime.now().isoformat()
            })
        else:
            unmatched.append({
                'id': committee_id,
                'name': committee_name,
                'chamber': chamber,
                'code': code
            })
    
    logger.info(f"  Matched: {len(matched)}")
    logger.info(f"  Unmatched: {len(unmatched)}")
    
    # Update matched committees (one by one since Supabase doesn't support batch updates)
    updated_count = 0
    error_count = 0
    
    if updates:
        logger.info(f"Updating {len(updates)} committees...")
        for i, update in enumerate(updates, 1):
            try:
                client.supabase.table('committees')\
                    .update({
                        'target_sectors': update['target_sectors'],
                        'updated_at': update['updated_at']
                    })\
                    .eq('id', update['id'])\
                    .execute()
                updated_count += 1
                if i % 10 == 0:
                    logger.info(f"  Updated {i}/{len(updates)} committees...")
            except Exception as e:
                logger.error(f"Error updating committee {update['id']}: {e}")
                error_count += 1
    
    # Report results
    logger.info("=" * 60)
    logger.info("✅ Update complete!")
    logger.info(f"   Total committees with nulls: {len(committees)}")
    logger.info(f"   Matched and updated: {updated_count}")
    logger.info(f"   Unmatched: {len(unmatched)}")
    if error_count > 0:
        logger.warning(f"   Errors: {error_count}")
    
    if unmatched:
        logger.info("")
        logger.info("Unmatched committees (not in committee_map.py):")
        for committee in unmatched[:10]:  # Show first 10
            logger.info(f"   - {committee['name']} ({committee['chamber']}, code: {committee['code']})")
        if len(unmatched) > 10:
            logger.info(f"   ... and {len(unmatched) - 10} more")
    
    logger.info("=" * 60)
    
    return {
        'total': len(committees),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'updated': updated_count,
        'errors': error_count,
        'unmatched_list': unmatched
    }


def main():
    """Main execution function."""
    # Initialize database client
    try:
        client = SupabaseClient(use_service_role=True)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        results = fill_null_target_sectors(client)
        if 'error' in results:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during update: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

