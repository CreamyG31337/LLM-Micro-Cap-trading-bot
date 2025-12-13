#!/usr/bin/env python3
"""
Backfill Performance Metrics Script
====================================

Populates the performance_metrics table with historical data from portfolio_positions.
This is a one-time script to catch up on past data.

Usage:
    python web_dashboard/backfill_performance_metrics.py

Options:
    --fund FUND_NAME    Only backfill for a specific fund
    --from-date DATE    Start date (YYYY-MM-DD)
    --to-date DATE      End date (YYYY-MM-DD)
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
import argparse

# Add parent directory to path for console utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from display.console_output import _safe_emoji

# Add web_dashboard to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from supabase_client import SupabaseClient
from exchange_rates_utils import get_exchange_rate_for_date_from_db


def backfill_performance_metrics(
    fund_filter: str = None,
    from_date: date = None,
    to_date: date = None
) -> None:
    """Backfill performance_metrics table with historical data."""
    
    print(f"{_safe_emoji('🔄')} Starting performance metrics backfill...")
    
    client = SupabaseClient()
    
    # Get all distinct dates from portfolio_positions
    query = client.supabase.table("portfolio_positions").select("date")
    
    if fund_filter:
        query = query.eq("fund", fund_filter)
    
    if from_date:
        query = query.gte("date", f"{from_date}T00:00:00")
    
    if to_date:
        query = query.lte("date", f"{to_date}T23:59:59.999999")
    
    # Fetch all dates (might be large, but we need distinct dates)
    print(f"{_safe_emoji('📊')} Fetching all position dates...")
    all_positions = query.execute().data
    
    if not all_positions:
        print(f"{_safe_emoji('⚠️')} No position data found matching criteria")
        return
    
    # Extract unique dates
    unique_dates = set()
    for pos in all_positions:
        dt = datetime.fromisoformat(pos['date'].replace('Z', '+00:00'))
        unique_dates.add(dt.date())
    
    dates_list = sorted(unique_dates)
    print(f"{_safe_emoji('📅')} Found {len(dates_list)} unique dates to process")
    print(f"   Range: {dates_list[0]} to {dates_list[-1]}")
    
    # Process each date
    successful_dates = 0
    skipped_funds = 0
    inserted_funds = 0
    failed = 0
    
    for target_date in dates_list:
        try:
            # Get positions for this date
            positions_result = client.supabase.table("portfolio_positions")\
                .select("fund, total_value, cost_basis, pnl, currency")\
                .gte("date", f"{target_date}T00:00:00")\
                .lt("date", f"{target_date}T23:59:59.999999")
            
            if fund_filter:
                positions_result = positions_result.eq("fund", fund_filter)
            
            positions = positions_result.execute().data
            
            if not positions:
                continue  # No positions for this date, skip silently
            
            # Aggregate by fund
            fund_totals = defaultdict(lambda: {
                'total_value': Decimal('0'),
                'cost_basis': Decimal('0'),
                'unrealized_pnl': Decimal('0'),
                'total_trades': 0
            })
            
            for pos in positions:
                fund = pos['fund']
                currency = pos.get('currency', 'CAD').upper()
                
                total_value = Decimal(str(pos.get('total_value', 0) or 0))
                cost_basis = Decimal(str(pos.get('cost_basis', 0) or 0))
                pnl = Decimal(str(pos.get('pnl', 0) or 0))
                
                # Convert USD to CAD
                if currency == 'USD':
                    rate = get_exchange_rate_for_date_from_db(
                        datetime.combine(target_date, datetime.min.time()),
                        'USD',
                        'CAD'
                    )
                    if rate:
                        rate_decimal = Decimal(str(rate))
                        total_value *= rate_decimal
                        cost_basis *= rate_decimal
                        pnl *= rate_decimal
                
                fund_totals[fund]['total_value'] += total_value
                fund_totals[fund]['cost_basis'] += cost_basis
                fund_totals[fund]['unrealized_pnl'] += pnl
                fund_totals[fund]['total_trades'] += 1
            
            # Upsert for each fund (checks per-fund existence)
            date_has_inserts = False
            for fund, totals in fund_totals.items():
                # Check if this specific fund+date combination already exists
                existing = client.supabase.table("performance_metrics")\
                    .select("id")\
                    .eq("fund", fund)\
                    .eq("date", str(target_date))\
                    .execute()
                
                if existing.data:
                    skipped_funds += 1
                    continue  # This fund+date already exists, skip
                
                performance_pct = (
                    (float(totals['unrealized_pnl']) / float(totals['cost_basis']) * 100)
                    if totals['cost_basis'] > 0 else 0.0
                )
                
                client.supabase.table("performance_metrics").upsert({
                    'fund': fund,
                    'date': str(target_date),
                    'total_value': float(totals['total_value']),
                    'cost_basis': float(totals['cost_basis']),
                    'unrealized_pnl': float(totals['unrealized_pnl']),
                    'performance_pct': round(performance_pct, 2),
                    'total_trades': totals['total_trades'],
                    'winning_trades': 0,
                    'losing_trades': 0
                }, on_conflict='fund,date').execute()
                
                inserted_funds += 1
                date_has_inserts = True
            
            if date_has_inserts:
                successful_dates += 1
            
            # Progress indicator
            if successful_dates % 10 == 0:
                print(f"   Processed {successful_dates}/{len(dates_list)} dates, {inserted_funds} fund metrics inserted...", end='\r')
        
        except Exception as e:
            print(f"\n{_safe_emoji('❌')} Error processing {target_date}: {e}")
            failed += 1
    
    print(f"\n\n{_safe_emoji('✅')} Backfill complete!")
    print(f"   Dates processed: {successful_dates}")
    print(f"   Fund metrics inserted: {inserted_funds}")
    print(f"   Fund metrics skipped (already exists): {skipped_funds}")
    print(f"   Dates failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill performance_metrics table')
    parser.add_argument('--fund', help='Only backfill for specific fund')
    parser.add_argument('--from-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date() if args.from_date else None
    to_date = datetime.strptime(args.to_date, '%Y-%m-%d').date() if args.to_date else None
    
    backfill_performance_metrics(
        fund_filter=args.fund,
        from_date=from_date,
        to_date=to_date
    )
