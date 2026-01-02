#!/usr/bin/env python3
"""
Incremental Portfolio Rebuild - Rebuild from specific date onwards

This script rebuilds portfolio positions and metrics from a specific date forward.
Used when backdated trades are entered to recalculate affected historical data.

Can be run as a background subprocess or called directly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict, deque
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / 'web_dashboard' / '.env')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rebuild_fund_from_date(fund_name: str, start_date: date, job_id: str = None) -> dict:
    """
    Rebuild portfolio positions and metrics from a specific date forward.
    
    This performs an incremental rebuild by:
    1. Deleting positions/metrics from start_date onwards
    2. Re-processing all trades to recalculate positions
    3. Saving updated snapshots for affected dates
    
    Args:
        fund_name: Fund to rebuild
        start_date: Start date for rebuild (inclusive)
        job_id: Optional job execution ID for tracking
        
    Returns:
        Dict with {'success': bool, 'dates_rebuilt': int, 'positions_updated': int, 'message': str}
    """
    try:
        logger.info(f"Starting incremental rebuild for {fund_name} from {start_date}")
        
        # Import dependencies
        from web_dashboard.supabase_client import SupabaseClient
        from data.repositories.supabase_repository import SupabaseRepository
        from data.models.portfolio import Position, PortfolioSnapshot
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.market_hours import MarketHours
        from utils.market_holidays import MarketHolidays
        from utils.timezone_utils import get_trading_timezone
        import pandas as pd
        
        # Update job status if job_id provided
        if job_id:
            _update_job_status(job_id, 'running', f'Starting rebuild from {start_date}')
        
        # Initialize Supabase client (service role for admin operations)
        client = SupabaseClient(use_service_role=True)
        supabase = client.supabase
        
        # Step 1: Delete stale data
        logger.info(f"Step 1: Deleting stale positions from {start_date} onwards...")
        if job_id:
            _update_job_status(job_id, 'running', f'Deleting stale positions from {start_date}')
        
        delete_count_pos = 0
        delete_count_metrics = 0
        
        try:
            # Delete positions
            result = supabase.table("portfolio_positions").delete()\
                .eq("fund", fund_name)\
                .gte("date", f"{start_date}T00:00:00")\
                .execute()
            delete_count_pos = len(result.data) if result.data else 0
            logger.info(f"   Deleted {delete_count_pos} portfolio positions")
            
            # Delete performance metrics
            result = supabase.table("performance_metrics").delete()\
                .eq("fund", fund_name)\
                .gte("date", start_date.isoformat())\
                .execute()
            delete_count_metrics = len(result.data) if result.data else 0
            logger.info(f"   Deleted {delete_count_metrics} performance metrics")
        except Exception as e:
            logger.warning(f"Error during deletion: {e}")
        
        # Step 2: Get all trades for fund (from beginning)
        logger.info("Step 2: Loading trade log...")
        if job_id:
            _update_job_status(job_id, 'running', 'Loading trade history from database')
        
        repository = SupabaseRepository(fund_name=fund_name)
        trades = repository.get_trade_history()
        
        if not trades or len(trades) == 0:
            msg = f"No trades found for fund {fund_name}"
            logger.warning(msg)
            if job_id:
                _update_job_status(job_id, 'completed', msg)
            return {
                'success': True,
                'dates_rebuilt': 0,
                'positions_updated': 0,
                'message': msg
            }
        
        logger.info(f"   Loaded {len(trades)} trades")
        
        # Step 3: Rebuild positions using FIFO
        logger.info(f"Step 3: Rebuilding positions from {start_date}...")
        if job_id:
            _update_job_status(job_id, 'running', f'Calculating positions for {len(trades)} trades')
        
        # Get trading days from start_date onwards
        market_hours = MarketHours()
        today = datetime.now().date()
        
        # Get all trading days we need to rebuild
        trading_days_to_rebuild = []
        current = start_date
        while current <= today:
            if market_hours.is_trading_day(current):
                trading_days_to_rebuild.append(current)
            current += timedelta(days=1)
        
        logger.info(f"   Need to rebuild {len(trading_days_to_rebuild)} trading days")
        
        # Calculate positions for each day using FIFO
        # We need to process ALL trades from beginning to maintain FIFO integrity
        running_positions = defaultdict(lambda: {
            'shares': Decimal('0'),
            'cost': Decimal('0'),
            'currency': 'USD'
        })
        lots_by_ticker = defaultdict(deque)  # FIFO lot tracking
        
        # Convert trades to DataFrame for easier processing
        trade_data = []
        for trade in trades:
            trade_data.append({
                'Date': trade.timestamp,
                'Ticker': trade.ticker,
                'Shares': float(trade.shares),
                'Price': float(trade.price),
                'Action': trade.action if hasattr(trade, 'action') else 'BUY',
                'Currency': trade.currency if hasattr(trade, 'currency') else 'USD'
            })
        trade_df = pd.DataFrame(trade_data)
        trade_df['Date'] = pd.to_datetime(trade_df['Date'])
        trade_df = trade_df.sort_values('Date')
        
        # Build positions day by day
        date_positions = {}
        all_dates = sorted(trade_df['Date'].dt.date.unique())
        
        for trading_day in all_dates:
            day_trades = trade_df[trade_df['Date'].dt.date == trading_day]
            
            for _, trade in day_trades.iterrows():
                ticker = trade['Ticker']
                shares = Decimal(str(trade['Shares']))
                price = Decimal(str(trade['Price']))
                action = str(trade['Action']).upper()
                
                if action == 'SELL':
                    # FIFO sell - consume lots
                    remaining = shares
                    while remaining > 0 and lots_by_ticker[ticker]:
                        lot_shares, lot_price = lots_by_ticker[ticker][0]
                        if lot_shares <= remaining:
                            remaining -= lot_shares
                            lots_by_ticker[ticker].popleft()
                        else:
                            lots_by_ticker[ticker][0] = (lot_shares - remaining, lot_price)
                            remaining = Decimal('0')
                    
                    # Update running positions
                    if running_positions[ticker]['shares'] > 0:
                        cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                        running_positions[ticker]['shares'] -= shares
                        running_positions[ticker]['cost'] -= shares * cost_per_share
                        # Prevent negative
                        if running_positions[ticker]['shares'] < 0:
                            running_positions[ticker]['shares'] = Decimal('0')
                        if running_positions[ticker]['cost'] < 0:
                            running_positions[ticker]['cost'] = Decimal('0')
                else:
                    # BUY - add lot
                    lots_by_ticker[ticker].append((shares, price))
                    running_positions[ticker]['shares'] += shares
                    running_positions[ticker]['cost'] += shares * price
                    running_positions[ticker]['currency'] = trade['Currency']
            
            # Store positions snapshot for this date
            date_positions[trading_day] = dict(running_positions)
        
        # Step 4: Fetch current prices for positions we need to rebuild
        logger.info("Step 4: Fetching current prices...")
        if job_id:
            _update_job_status(job_id, 'running', 'Fetching market prices')
        
        # Get unique tickers that have positions in rebuild period
        tickers_to_price = set()
        for trading_day in trading_days_to_rebuild:
            if trading_day in date_positions:
                for ticker in date_positions[trading_day]:
                    if date_positions[trading_day][ticker]['shares'] > 0:
                        tickers_to_price.add(ticker)
        
        logger.info(f"   Fetching prices for {len(tickers_to_price)} tickers")
        
        # Fetch prices
        fetcher = MarketDataFetcher()
        price_cache = {}  # (ticker, date) -> price
        
        for ticker in tickers_to_price:
            try:
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(today, datetime.max.time())
                result = fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                
                if result.df is not None and not result.df.empty:
                    for idx, row in result.df.iterrows():
                        price_date = idx.date() if hasattr(idx, 'date') else idx
                        price_cache[(ticker, price_date)] = Decimal(str(row['Close']))
            except Exception as e:
                logger.warning(f"Failed to fetch prices for {ticker}: {e}")
        
        # Step 5: Save snapshots for rebuild dates
        logger.info("Step 5: Saving updated snapshots...")
        if job_id:
            _update_job_status(job_id, 'running', f'Saving {len(trading_days_to_rebuild)} snapshots')
        
        positions_created = 0
        trading_tz = get_trading_timezone()
        
        for trading_day in trading_days_to_rebuild:
            if trading_day not in date_positions:
                continue
                
            positions_on_day = date_positions[trading_day]
            snapshot_positions = []
            
            for ticker, pos_data in positions_on_day.items():
                if pos_data['shares'] <= 0:
                    continue
                
                # Get price for this ticker on this date
                current_price = price_cache.get((ticker, trading_day))
                if current_price is None:
                    logger.warning(f"No price for {ticker} on {trading_day}, skipping")
                    continue
                
                # Create Position object
                shares = pos_data['shares']
                cost_basis = pos_data['cost']
                avg_price = cost_basis / shares
                total_value = shares * current_price
                pnl = total_value - cost_basis
                
                position = Position(
                    ticker=ticker,
                    shares=shares,
                    avg_price=avg_price,
                    cost_basis=cost_basis,
                    current_price=current_price,
                    total_value=total_value,
                    unrealized_pnl=pnl,
                    currency=pos_data['currency']
                )
                snapshot_positions.append(position)
            
            if snapshot_positions:
                # Create snapshot timestamp (4pm ET on trading day)
                snapshot_time = datetime.combine(trading_day, datetime.min.time().replace(hour=16, minute=0))
                snapshot_time = trading_tz.localize(snapshot_time)
                
                snapshot = PortfolioSnapshot(
                    positions=snapshot_positions,
                    timestamp=snapshot_time
                )
                
                # Save to database
                try:
                    repository.save_portfolio_snapshot(snapshot)
                    positions_created += len(snapshot_positions)
                except Exception as e:
                    logger.error(f"Failed to save snapshot for {trading_day}: {e}")
        
        # Success
        msg = f"Rebuilt {len(trading_days_to_rebuild)} days, created {positions_created} position records"
        logger.info(f"✅ Rebuild complete: {msg}")
        
        if job_id:
            _update_job_status(job_id, 'completed', msg)
        
        return {
            'success': True,
            'dates_rebuilt': len(trading_days_to_rebuild),
            'positions_updated': positions_created,
            'message': msg
        }
        
    except Exception as e:
        error_msg = f"Rebuild failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if job_id:
            _update_job_status(job_id, 'failed', error_msg)
        
        return {
            'success': False,
            'dates_rebuilt': 0,
            'positions_updated': 0,
            'message': error_msg
        }


def _update_job_status(job_id: str, status: str, message: str):
    """Update job execution status in database."""
    try:
        from web_dashboard.supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        client.supabase.table("job_executions").update({
            'status': status,
            'output': message,
            'end_time': datetime.utcnow().isoformat() if status in ('completed', 'failed') else None
        }).eq('id', job_id).execute()
    except Exception as e:
        logger.warning(f"Could not update job status: {e}")


def main():
    """CLI entry point for running as subprocess."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rebuild portfolio from specific date')
    parser.add_argument('fund_name', help='Fund name to rebuild')
    parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--job-id', help='Job execution ID for tracking')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.fromisoformat(args.start_date).date()
    except ValueError:
        print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD")
        sys.exit(1)
    
    result = rebuild_fund_from_date(args.fund_name, start_date, args.job_id)
    
    print(f"\n{result['message']}")
    print(f"Dates rebuilt: {result['dates_rebuilt']}")
    print(f"Positions updated: {result['positions_updated']}")
    
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
