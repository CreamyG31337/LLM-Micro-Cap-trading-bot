"""
Backfill Pre-Converted Currency Values
========================================

This script uses a SQL function to backfill pre-converted values in a single query.
Much faster than updating records one-by-one (seconds vs minutes/hours).

Requires the SQL function to be installed:
  database/setup/11_backfill_preconverted_values.sql
"""

import sys
from pathlib import Path
from typing import Optional
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add web_dashboard to path
web_dashboard_path = Path(__file__).resolve().parent
if str(web_dashboard_path) not in sys.path:
    sys.path.insert(0, str(web_dashboard_path))

from supabase_client import SupabaseClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def backfill_preconverted_values(
    fund_filter: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """
    Backfill pre-converted currency values using SQL function (single query).
    
    Args:
        fund_filter: Optional fund name to filter by (None = all funds)
        dry_run: If True, only log what would be updated without making changes
    """
    logger.info("=" * 60)
    logger.info("BACKFILL PRE-CONVERTED CURRENCY VALUES")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
        logger.warning("⚠️  SQL function doesn't support dry-run - will show what would be updated")
    
    # Use service role key to bypass RLS (background job needs full access)
    client = SupabaseClient(use_service_role=True)
    
    # Step 1: Check how many records need updating
    logger.info("\n📊 Step 1: Checking records missing pre-converted values...")
    
    query = client.supabase.table("portfolio_positions")\
        .select("id", count='exact')\
        .is_("total_value_base", "null")
    
    if fund_filter:
        query = query.eq("fund", fund_filter)
        logger.info(f"   Filtering by fund: {fund_filter}")
    
    result = query.execute()
    total_missing = result.count if result.count else 0
    
    if total_missing == 0:
        logger.info("✅ No records found missing pre-converted values!")
        return
    
    logger.info(f"   Found {total_missing} records missing pre-converted values")
    
    if dry_run:
        logger.info(f"\n🔍 DRY RUN: Would update {total_missing} records using SQL function")
        logger.info("   (To actually update, run without --dry-run flag)")
        return
    
    # Step 2: Call SQL function to update all records at once
    logger.info(f"\n📊 Step 2: Calling SQL function to update {total_missing} records...")
    logger.info("   This should be very fast (single SQL query)")
    
    try:
        import time
        start_time = time.time()
        
        # Call the SQL function via RPC
        result = client.supabase.rpc(
            'backfill_preconverted_values',
            {'fund_filter': fund_filter}
        ).execute()
        
        duration = time.time() - start_time
        
        if result.data and len(result.data) > 0:
            stats = result.data[0]
            updated = stats.get('records_updated', 0)
            skipped = stats.get('records_skipped', 0)
            errors = stats.get('errors_count', 0)
            
            logger.info(f"\n✅ SQL function completed in {duration:.2f} seconds")
            logger.info(f"   Records updated: {updated}")
            logger.info(f"   Records skipped: {skipped}")
            logger.info(f"   Errors: {errors}")
            
            if updated > 0:
                logger.info("\n✅ Backfill complete! The warning should no longer appear.")
            else:
                logger.warning("\n⚠️  No records were updated - check if function exists in database")
        else:
            logger.warning("⚠️  SQL function returned no results")
            logger.info("   This might mean:")
            logger.info("   1. The SQL function doesn't exist (run the SQL file first)")
            logger.info("   2. No records matched the filter")
            logger.info("   3. RPC call failed silently")
            
    except Exception as e:
        logger.error(f"❌ Error calling SQL function: {e}")
        logger.error("   This might mean:")
        logger.error("   1. The SQL function doesn't exist in the database")
        logger.error("   2. RPC is not enabled or configured correctly")
        logger.error("   3. Permission issues")
        logger.error("\n   To fix:")
        logger.error("   1. Run database/setup/11_backfill_preconverted_values.sql in Supabase SQL editor")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Backfill pre-converted currency values using SQL function (fast version)"
    )
    parser.add_argument("--fund", type=str, help="Filter by specific fund name")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no changes)")
    
    args = parser.parse_args()
    
    backfill_preconverted_values(
        fund_filter=args.fund,
        dry_run=args.dry_run
    )

