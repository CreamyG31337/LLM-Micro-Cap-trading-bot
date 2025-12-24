"""
Backfill Pre-Converted Currency Values
========================================

This script backfills the total_value_base, cost_basis_base, pnl_base, and exchange_rate
columns for existing portfolio_positions records that were created before the pre-conversion
feature was added.

This eliminates the "SLOW PATH" warning by ensuring all records have pre-converted values.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Optional
import logging
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add web_dashboard to path
web_dashboard_path = Path(__file__).resolve().parent
if str(web_dashboard_path) not in sys.path:
    sys.path.insert(0, str(web_dashboard_path))

from supabase_client import SupabaseClient
from exchange_rates_utils import get_exchange_rate_for_date_from_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_fund_base_currency(client: SupabaseClient, fund_name: str) -> str:
    """Get the base currency for a fund, defaulting to CAD if not set."""
    try:
        result = client.supabase.table("funds")\
            .select("base_currency")\
            .eq("name", fund_name)\
            .limit(1)\
            .execute()
        
        if result.data and result.data[0].get('base_currency'):
            return result.data[0]['base_currency'].upper()
    except Exception as e:
        logger.warning(f"Could not get base_currency for fund {fund_name}: {e}")
    
    return 'CAD'  # Default


def backfill_preconverted_values(
    fund_filter: Optional[str] = None,
    batch_size: int = 100,
    dry_run: bool = False
) -> None:
    """
    Backfill pre-converted currency values for portfolio_positions records.
    
    Args:
        fund_filter: Optional fund name to filter by (None = all funds)
        batch_size: Number of records to update per batch
        dry_run: If True, only log what would be updated without making changes
    """
    logger.info("=" * 60)
    logger.info("BACKFILL PRE-CONVERTED CURRENCY VALUES")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    # Use service role key to bypass RLS (background job needs full access)
    client = SupabaseClient(use_service_role=True)
    
    # Step 1: Find all records missing pre-converted values
    logger.info("\n📊 Step 1: Finding records missing pre-converted values...")
    
    query = client.supabase.table("portfolio_positions")\
        .select("id, fund, ticker, date, currency, total_value, cost_basis, pnl, base_currency, total_value_base")\
        .is_("total_value_base", "null")\
        .order("date")\
        .limit(10000)  # Process in chunks
    
    if fund_filter:
        query = query.eq("fund", fund_filter)
        logger.info(f"   Filtering by fund: {fund_filter}")
    
    result = query.execute()
    
    if not result.data:
        logger.info("✅ No records found missing pre-converted values!")
        return
    
    total_records = len(result.data)
    logger.info(f"   Found {total_records} records missing pre-converted values")
    
    # Step 2: Get unique funds to cache base_currency lookups
    logger.info("\n📊 Step 2: Caching fund base currencies...")
    funds = set(record['fund'] for record in result.data)
    fund_base_currencies = {}
    for fund_name in funds:
        base_currency = get_fund_base_currency(client, fund_name)
        fund_base_currencies[fund_name] = base_currency
        logger.info(f"   {fund_name}: {base_currency}")
    
    # Step 3: Process records in batches
    logger.info(f"\n📊 Step 3: Processing {total_records} records in batches of {batch_size}...")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for i in range(0, total_records, batch_size):
        batch = result.data[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        logger.info(f"\n   Processing batch {batch_num}/{total_batches} ({len(batch)} records)...")
        
        updates = []
        
        for record in batch:
            try:
                record_id = record['id']
                fund_name = record['fund']
                position_date = pd.to_datetime(record['date'])
                position_currency = (record.get('currency') or 'CAD').upper()
                
                # Get base currency (from record if set, otherwise from fund)
                base_currency = record.get('base_currency')
                if not base_currency:
                    base_currency = fund_base_currencies.get(fund_name, 'CAD')
                else:
                    base_currency = base_currency.upper()
                
                # Get original values
                total_value = Decimal(str(record.get('total_value') or 0))
                cost_basis = Decimal(str(record.get('cost_basis') or 0))
                pnl = Decimal(str(record.get('pnl') or 0))
                
                # Calculate pre-converted values
                if position_currency == base_currency:
                    # Same currency - no conversion needed
                    total_value_base = total_value
                    cost_basis_base = cost_basis
                    pnl_base = pnl
                    exchange_rate = Decimal('1.0')
                elif position_currency == 'USD' and base_currency != 'USD':
                    # Convert USD to base currency
                    rate = get_exchange_rate_for_date_from_db(
                        position_date,
                        'USD',
                        base_currency
                    )
                    if rate is not None:
                        exchange_rate = Decimal(str(rate))
                    else:
                        # Fallback rate
                        if base_currency == 'CAD':
                            exchange_rate = Decimal('1.35')
                        else:
                            exchange_rate = Decimal('1.0')
                        logger.warning(f"   Missing exchange rate for {position_date.date()} USD→{base_currency}, using fallback {exchange_rate}")
                    
                    total_value_base = total_value * exchange_rate
                    cost_basis_base = cost_basis * exchange_rate
                    pnl_base = pnl * exchange_rate
                elif base_currency == 'USD' and position_currency != 'USD':
                    # Convert from position currency to USD
                    rate = get_exchange_rate_for_date_from_db(
                        position_date,
                        position_currency,
                        'USD'
                    )
                    if rate is not None:
                        exchange_rate = Decimal(str(rate))
                    else:
                        # Fallback: try inverse
                        if position_currency == 'CAD':
                            inverse_rate = get_exchange_rate_for_date_from_db(
                                position_date,
                                'USD',
                                'CAD'
                            )
                            if inverse_rate is not None:
                                exchange_rate = Decimal('1.0') / Decimal(str(inverse_rate))
                            else:
                                exchange_rate = Decimal('1.0') / Decimal('1.35')
                        else:
                            exchange_rate = Decimal('1.0')
                        logger.warning(f"   Missing exchange rate for {position_date.date()} {position_currency}→USD, using fallback {exchange_rate}")
                    
                    total_value_base = total_value * exchange_rate
                    cost_basis_base = cost_basis * exchange_rate
                    pnl_base = pnl * exchange_rate
                else:
                    # Other currency combinations - store as-is for now
                    logger.warning(f"   Unsupported conversion: {position_currency} → {base_currency} (record {record_id})")
                    total_value_base = total_value
                    cost_basis_base = cost_basis
                    pnl_base = pnl
                    exchange_rate = Decimal('1.0')
                
                updates.append({
                    'id': record_id,
                    'base_currency': base_currency,
                    'total_value_base': float(total_value_base),
                    'cost_basis_base': float(cost_basis_base),
                    'pnl_base': float(pnl_base),
                    'exchange_rate': float(exchange_rate)
                })
                
            except Exception as e:
                logger.error(f"   Error processing record {record.get('id', 'unknown')}: {e}")
                error_count += 1
        
        # Update batch
        if updates and not dry_run:
            try:
                # Update records one by one (Supabase doesn't support bulk updates easily)
                for update in updates:
                    client.supabase.table("portfolio_positions")\
                        .update({
                            'base_currency': update['base_currency'],
                            'total_value_base': update['total_value_base'],
                            'cost_basis_base': update['cost_basis_base'],
                            'pnl_base': update['pnl_base'],
                            'exchange_rate': update['exchange_rate']
                        })\
                        .eq('id', update['id'])\
                        .execute()
                
                updated_count += len(updates)
                logger.info(f"   ✅ Updated {len(updates)} records")
            except Exception as e:
                logger.error(f"   ❌ Error updating batch: {e}")
                error_count += len(updates)
        elif updates:
            logger.info(f"   🔍 Would update {len(updates)} records (dry run)")
            updated_count += len(updates)
        else:
            skipped_count += len(batch)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BACKFILL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records processed: {total_records}")
    if dry_run:
        logger.info(f"Would update: {updated_count}")
    else:
        logger.info(f"Updated: {updated_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)
    
    if not dry_run and updated_count > 0:
        logger.info("\n✅ Backfill complete! The warning should no longer appear.")
    elif dry_run:
        logger.info("\n🔍 Dry run complete. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill pre-converted currency values")
    parser.add_argument("--fund", type=str, help="Filter by specific fund name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for updates")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no changes)")
    
    args = parser.parse_args()
    
    backfill_preconverted_values(
        fund_filter=args.fund,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

