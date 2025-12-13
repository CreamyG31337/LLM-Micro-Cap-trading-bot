#!/usr/bin/env python3
"""
Backfill Securities Table - One-Time Utility
=============================================
This script finds all tickers in portfolio_positions and trade_log that are
missing from the securities table (or have NULL company_name) and populates
them with yfinance metadata.

This is a ONE-TIME utility since the auto-population feature will handle
all future trades automatically.

Usage:
    python debug/backfill_securities.py [--dry-run]
    
Options:
    --dry-run    Show what would be updated without making changes
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.supabase_client import SupabaseClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_missing_tickers(client: SupabaseClient):
    """Find all tickers that need to be added to securities table."""
    
    print("\nFinding tickers missing from securities table...")
    print("=" * 60)
    
    # Get all unique tickers from portfolio_positions
    print("\nChecking portfolio_positions...")
    positions_result = client.supabase.table('portfolio_positions').select('ticker, currency').execute()
    position_tickers = {}
    for row in positions_result.data:
        ticker = row.get('ticker')
        currency = row.get('currency', 'USD')
        if ticker:
            position_tickers[ticker] = currency
    
    print(f"   Found {len(position_tickers)} unique tickers in portfolio_positions")
    
    # Get all unique tickers from trade_log
    print("\nChecking trade_log...")
    trades_result = client.supabase.table('trade_log').select('ticker, currency').execute()
    trade_tickers = {}
    for row in trades_result.data:
        ticker = row.get('ticker')
        currency = row.get('currency', 'USD')
        if ticker:
            trade_tickers[ticker] = currency
    
    print(f"   Found {len(trade_tickers)} unique tickers in trade_log")
    
    # Combine and deduplicate (prefer portfolio_positions currency)
    all_tickers = {**trade_tickers, **position_tickers}
    print(f"\nTotal unique tickers: {len(all_tickers)}")
    
    # Get existing securities
    print("\nChecking securities table...")
    securities_result = client.supabase.table('securities').select('ticker, company_name').execute()
    existing_securities = {}
    for row in securities_result.data:
        ticker = row.get('ticker')
        company_name = row.get('company_name')
        existing_securities[ticker] = company_name
    
    print(f"   Found {len(existing_securities)} tickers in securities table")
    
    # Find tickers that need to be added/updated
    missing_tickers = []
    needs_update = []
    
    for ticker, currency in all_tickers.items():
        if ticker not in existing_securities:
            missing_tickers.append((ticker, currency))
        elif not existing_securities[ticker] or existing_securities[ticker] == 'Unknown':
            needs_update.append((ticker, currency))
    
    print(f"\nSummary:")
    print(f"   - Missing from securities: {len(missing_tickers)}")
    print(f"   - Exists but needs update (NULL/Unknown): {len(needs_update)}")
    print(f"   - Total to process: {len(missing_tickers) + len(needs_update)}")
    
    return missing_tickers + needs_update


def backfill_securities(client: SupabaseClient, tickers_to_process, dry_run=False):
    """Backfill securities table with yfinance data."""
    
    if not tickers_to_process:
        print("\nNo tickers need to be processed!")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing {len(tickers_to_process)} tickers...")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for idx, (ticker, currency) in enumerate(tickers_to_process, 1):
        print(f"\n[{idx}/{len(tickers_to_process)}] Processing {ticker} ({currency})...")
        
        if dry_run:
            print(f"   [DRY RUN] Would call ensure_ticker_in_securities('{ticker}', '{currency}', None)")
            success_count += 1
        else:
            try:
                result = client.ensure_ticker_in_securities(ticker, currency, None)
                if result:
                    success_count += 1
                    print(f"   SUCCESS")
                else:
                    error_count += 1
                    print(f"   FAILED")
            except Exception as e:
                error_count += 1
                print(f"   ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total: {len(tickers_to_process)}")
    
    if dry_run:
        print("\nRun without --dry-run to actually update the database")


def main():
    """Main entry point."""
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("[DRY RUN] Running in DRY RUN mode - no changes will be made\n")
    
    print("Securities Table Backfill Utility")
    print("=" * 60)
    print("This utility populates the securities table with yfinance")
    print("metadata for all tickers that currently exist in your")
    print("portfolio_positions or trade_log tables.")
    print("=" * 60)
    
    # Initialize client with service role (admin access)
    try:
        print("\nConnecting to Supabase...")
        client = SupabaseClient(use_service_role=True)
        print("Connected successfully")
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")
        print("\nMake sure SUPABASE_URL and SUPABASE_SECRET_KEY are set in .env")
        sys.exit(1)
    
    # Find missing tickers
    try:
        tickers_to_process = find_missing_tickers(client)
    except Exception as e:
        print(f"ERROR: Error finding missing tickers: {e}")
        logger.exception("Error in find_missing_tickers")
        sys.exit(1)
    
    # Confirm before proceeding (skip in dry-run)
    if not dry_run and tickers_to_process:
        print("\nWARNING: This will fetch metadata from yfinance and update the database.")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Cancelled by user")
            sys.exit(0)
    
    # Backfill securities table
    try:
        backfill_securities(client, tickers_to_process, dry_run)
    except Exception as e:
        print(f"ERROR: Error during backfill: {e}")
        logger.exception("Error in backfill_securities")
        sys.exit(1)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
