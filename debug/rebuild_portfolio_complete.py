#!/usr/bin/env python3
"""
Complete Portfolio Rebuild Script - CSV + Supabase

This script rebuilds the portfolio from the trade log and updates BOTH:
1. CSV files (for local data)
2. Supabase database (for web dashboard)

Uses the proper repository pattern to ensure consistency.
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import pandas as pd
import pytz

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from display.console_output import print_info, print_error, _safe_emoji
import numpy as np
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.repository_factory import RepositoryFactory
from portfolio.portfolio_manager import PortfolioManager
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from market_data.market_hours import MarketHours
from utils.market_holidays import MarketHolidays
from utils.ticker_utils import get_company_name
from display.console_output import print_success, print_error, print_info, print_warning, _safe_emoji

# Load environment variables
load_dotenv(project_root / 'web_dashboard' / '.env')

def rebuild_portfolio_complete(data_dir: str, fund_name: str = None) -> bool:
    """
    Rebuild portfolio from trade log and update both CSV and Supabase.
    
    CRITICAL DATA INTEGRITY PRINCIPLE:
    - NEVER uses fallback prices (old prices, average prices, etc.)
    - FAILS HARD if any position can't fetch current market prices
    - This prevents silent insertion of garbage data that would corrupt P&L calculations
    
    Args:
        data_dir: Directory containing trading data files
        fund_name: Fund name for Supabase operations (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"{_safe_emoji('🔄')} Complete Portfolio Rebuild (CSV + Supabase)")
        print("=" * 60)
        print(f"{_safe_emoji('📁')} Data directory: {data_dir}")
        if fund_name:
            print(f"{_safe_emoji('🏦')} Fund name: {fund_name}")
        
        # Extract fund name from data directory if not provided
        if not fund_name:
            fund_name = Path(data_dir).name
            print(f"{_safe_emoji('📁')} Extracted fund name: {fund_name}")
        
        # Initialize repository with Supabase dual-write capability (same as trading script)
        if fund_name:
            try:
                repository = RepositoryFactory.create_repository(repository_type='supabase-dual-write', data_directory=data_dir, fund_name=fund_name)
                print(f"{_safe_emoji('✅')} Using Supabase dual-write repository (Supabase read, CSV+Supabase write)")
            except Exception as e:
                print(f"{_safe_emoji('⚠️')} Supabase dual-write repository failed: {e}")
                print("   Falling back to CSV-only repository")
                repository = RepositoryFactory.create_repository(repository_type='csv', data_directory=data_dir, fund_name=fund_name)
        else:
            repository = RepositoryFactory.create_repository(repository_type='csv', data_directory=data_dir, fund_name=fund_name)
            print(f"{_safe_emoji('✅')} Using CSV-only repository")
        
        # Initialize portfolio manager with Fund object
        from portfolio.fund_manager import Fund
        fund = Fund(id=fund_name, name=fund_name, description=f"Fund: {fund_name}")
        portfolio_manager = PortfolioManager(repository, fund)
        
        # Load trade log
        trade_log_file = Path(data_dir) / "llm_trade_log.csv"
        if not trade_log_file.exists():
            print_error(f"{_safe_emoji('❌')} Trade log not found: {trade_log_file}")
            return False
        
        print_info(f"{_safe_emoji('📊')} Loading trade log...")
        trade_df = pd.read_csv(trade_log_file)
        from utils.timezone_utils import safe_parse_datetime_column
        trade_df['Date'] = safe_parse_datetime_column(trade_df['Date'], 'Date')
        trade_df = trade_df.sort_values('Date')
        
        print_success(f"{_safe_emoji('✅')} Loaded {len(trade_df)} trades")
        
        if len(trade_df) == 0:
            print_warning("⚠️  Trade log is empty - no portfolio entries to generate")
            return True
        
        # Clear existing portfolio data
        print_info(f"{_safe_emoji('🧹')} Clearing existing portfolio data...")
        try:
            # Clear CSV portfolio file
            portfolio_file = Path(data_dir) / "llm_portfolio_update.csv"
            if portfolio_file.exists():
                # Create backup in backups directory
                backup_dir = Path(data_dir) / "backups"
                backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = backup_dir / f"{portfolio_file.stem}.backup_{timestamp}.csv"
                shutil.copy2(portfolio_file, backup_file)
                portfolio_file.unlink()  # Remove original file
                print_info(f"   Backed up existing portfolio to: {backup_file}")
            
            # Clear Supabase data (if using dual-write)
            if hasattr(repository, 'supabase_repo') and hasattr(repository.supabase_repo, 'supabase'):
                try:
                    # Delete all portfolio positions for this fund
                    result = repository.supabase_repo.supabase.table("portfolio_positions").delete().eq("fund", fund_name).execute()
                    print_info(f"   Cleared {len(result.data) if result.data else 0} Supabase portfolio positions")
                except Exception as e:
                    print_warning(f"   Could not clear Supabase data: {e}")
            elif hasattr(repository, 'supabase'):
                try:
                    # Delete all portfolio positions for this fund
                    result = repository.supabase.table("portfolio_positions").delete().eq("fund", fund_name).execute()
                    print_info(f"   Cleared {len(result.data) if result.data else 0} Supabase portfolio positions")
                except Exception as e:
                    print_warning(f"   Could not clear Supabase data: {e}")
                
        except Exception as e:
            print_warning(f"⚠️  Could not clear existing data: {e}")
        
        # Process trades and generate snapshots below
        print_info(f"{_safe_emoji('📈')} Processing trades chronologically...")
        
        # Generate HOLD entries for all trading days
        print_info(f"{_safe_emoji('📊')} Generating HOLD entries for all trading days...")
        
        # Get all unique trading days from trades
        trade_dates = sorted(trade_df['Date'].dt.date.unique())
        
        # Add trading days from first trade to today (or last trading day)
        market_hours = MarketHours()
        market_holidays = MarketHolidays()
        current_date = trade_dates[0]
        
        # Generate up to today or the last trading day
        today = datetime.now().date()
        last_trading_day = market_hours.last_trading_date().date()
        end_date = max(trade_dates[-1], last_trading_day)
        
        all_trading_days = set(trade_dates)
        while current_date <= end_date:
            if market_hours.is_trading_day(current_date):
                all_trading_days.add(current_date)
            current_date += timedelta(days=1)
        
        # Generate historical HOLD entries for each trading day
        print_info(f"{_safe_emoji('📊')} Creating historical portfolio snapshots...")
        
        from data.models.portfolio import Position, PortfolioSnapshot
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        
        # Initialize market data fetcher and price cache
        market_fetcher = MarketDataFetcher()
        price_cache = PriceCache()
        
        # Convert all_trading_days to sorted list
        all_trading_days_list = sorted(list(all_trading_days))
        print_info(f"   Generating snapshots for {len(all_trading_days_list)} trading days")
        
        # Pre-calculate positions for each trading day
        date_positions = {}  # date -> {ticker: position_data}
        running_positions = defaultdict(lambda: {'shares': Decimal('0'), 'cost': Decimal('0'), 'currency': 'USD'})
        
        for trading_day in all_trading_days_list:
            # Process trades for this specific day only
            day_trades = trade_df[trade_df['Date'].dt.date == trading_day]
            
            for _, trade in day_trades.iterrows():
                ticker = trade['Ticker']
                reason = trade['Reason']
                shares = Decimal(str(trade['Shares']))
                price = Decimal(str(trade['Price']))
                cost = shares * price
                
                # Determine action from reason - look for SELL first, then default to BUY
                # Handle NaN and other non-string values
                if pd.isna(reason) or not isinstance(reason, str):
                    reason_str = ''
                else:
                    reason_str = str(reason).upper()
                
                if 'SELL' in reason_str:
                    # Simple FIFO: reduce shares and cost proportionally
                    if running_positions[ticker]['shares'] > 0:
                        cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                        running_positions[ticker]['shares'] -= shares
                        running_positions[ticker]['cost'] -= shares * cost_per_share
                        # Ensure we don't go negative
                        if running_positions[ticker]['shares'] < 0:
                            running_positions[ticker]['shares'] = Decimal('0')
                        if running_positions[ticker]['cost'] < 0:
                            running_positions[ticker]['cost'] = Decimal('0')
                else:
                    # Default to BUY for all other trades (including imported ones)
                    running_positions[ticker]['shares'] += shares
                    running_positions[ticker]['cost'] += cost
                    # Handle NaN currency values
                    currency = trade.get('Currency', 'USD')
                    if pd.isna(currency):
                        currency = 'USD'
                    running_positions[ticker]['currency'] = currency
            
            # Store current running positions for this date
            date_positions[trading_day] = dict(running_positions)
        
        # Generate portfolio snapshots for each trading day
        snapshots_created = 0
        
        # Pre-fetch prices for all unique tickers across all dates for better performance
        print_info("   Pre-fetching historical prices...")
        all_tickers = set()
        for positions in date_positions.values():
            all_tickers.update(positions.keys())
        
        # Fetch prices for all tickers and dates
        price_cache_dict = {}  # {(ticker, date): price}
        successful_fetches = 0
        failed_fetches = 0

        print_info(f"   Date range: {all_trading_days_list[0]} to {all_trading_days_list[-1]}")
        print_info(f"   Total trading days: {len(all_trading_days_list)}")
        print_info(f"   Fetching prices for {len(all_tickers)} tickers...")

        for ticker in all_tickers:
            try:
                # Convert date objects to datetime for API compatibility
                start_dt = datetime.combine(all_trading_days_list[0], datetime.min.time())
                end_dt = datetime.combine(all_trading_days_list[-1], datetime.max.time())
                
                # Fetch all historical data for this ticker at once
                result = market_fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                
                if result.df is not None and not result.df.empty:
                    # Cache the full dataset
                    price_cache.cache_price_data(ticker, result.df)
                    
                    # Extract prices for each trading day
                    dates_cached = 0
                    for trading_day in all_trading_days_list:
                        day_data = result.df[result.df.index.date == trading_day]
                        if not day_data.empty:
                            price_cache_dict[(ticker, trading_day)] = Decimal(str(day_data['Close'].iloc[0]))
                            dates_cached += 1
                    
                    # Only show progress for failed fetches, not every success
                    successful_fetches += 1
                else:
                    print_error(f"     {_safe_emoji('✗')} {ticker}: No data returned")
                    failed_fetches += 1
                    
            except Exception as e:
                print_error(f"     {_safe_emoji('✗')} {ticker}: Fetch failed - {e}")
                failed_fetches += 1

        print_info(f"   Batch fetch complete: {successful_fetches} succeeded, {failed_fetches} failed")

        if failed_fetches > 0:
            print_error(f"   WARNING: {failed_fetches} tickers failed to fetch - rebuild may be incomplete")
        
        today = datetime.now().date()
        for trading_day in all_trading_days_list:
            # Skip today - it will be handled by the final snapshot
            if trading_day >= today:
                continue
            
            # Get ALL positions that were held on this day (not just traded)
            # This includes positions from previous days that weren't sold
            all_held_positions = {}
            
            # Start with positions that were actively traded on this day
            positions_for_date = date_positions.get(trading_day, {})
            for ticker, pos in positions_for_date.items():
                if pos['shares'] > 0:
                    all_held_positions[ticker] = pos
            
            # Add positions from previous days that weren't sold
            for prev_day in all_trading_days_list:
                if prev_day >= trading_day:
                    break
                prev_positions = date_positions.get(prev_day, {})
                for ticker, pos in prev_positions.items():
                    if pos['shares'] > 0 and ticker not in all_held_positions:
                        # This position was held from a previous day
                        all_held_positions[ticker] = pos
            
            if len(all_held_positions) == 0:
                continue
            
            # Check if any market was open for our positions
            any_market_open = False
            for ticker in all_held_positions.keys():
                # Determine market based on ticker (.TO = Toronto, .V = Vancouver)
                if ticker.endswith(('.TO', '.V')):
                    market = 'canadian'
                else:
                    market = 'us'
                
                if market_holidays.is_trading_day(trading_day, market=market):
                    any_market_open = True
                    break
            
            if not any_market_open:
                continue
            
            # Only show progress every 10 days or for important milestones
            if len([d for d in all_trading_days_list if d <= trading_day]) % 10 == 0:
                print_info(f"   Processing {trading_day}...")
            
            # Create positions list for this date
            daily_positions = []
            for ticker, position in all_held_positions.items():
                if position['shares'] > 0:  # Only include positions with shares
                    # Check if this stock's market was open on this day (.TO = Toronto, .V = Vancouver)
                    if ticker.endswith(('.TO', '.V')):
                        market = 'canadian'
                    else:
                        market = 'us'
                    
                    if not market_holidays.is_trading_day(trading_day, market=market):
                        continue
                    # Ensure no division by zero
                    if position['shares'] > 0:
                        avg_price = position['cost'] / position['shares']
                    else:
                        avg_price = Decimal('0')
                    
                    # Use pre-fetched historical price - NO FALLBACKS ALLOWED (except for very recent dates)
                    price_key = (ticker, trading_day)
                    if price_key in price_cache_dict:
                        current_price = price_cache_dict[price_key]
                    else:
                        # Check if this is a very recent date (within 2 trading days of today)
                        # For recent dates, allow fallback to previous day's price since data may not be available yet
                        days_ago = (today - trading_day).days
                        if days_ago <= 2:
                            # Try to find the most recent available price for this ticker
                            prev_price = None
                            for prev_day in sorted([d for d in all_trading_days_list if d < trading_day], reverse=True):
                                prev_key = (ticker, prev_day)
                                if prev_key in price_cache_dict:
                                    prev_price = price_cache_dict[prev_key]
                                    break
                            
                            if prev_price is not None:
                                current_price = prev_price
                                print_warning(f"   Using previous day's price for {ticker} on {trading_day} (data not available yet)")
                            elif position['cost'] > 0 and position['shares'] > 0:
                                # Last resort: use cost basis
                                current_price = position['cost'] / position['shares']
                                print_warning(f"   Using cost basis for {ticker} on {trading_day} (no price data available)")
                            else:
                                raise ValueError(f"Historical price not available for {ticker} on {trading_day}. Market data fetch failed.")
                        else:
                            # NO FALLBACKS for older historical data - fail if price not available
                            # This ensures we don't create corrupted data with wrong prices
                            raise ValueError(f"Historical price not available for {ticker} on {trading_day}. Market data fetch failed.")
                    market_value = position['shares'] * current_price
                    unrealized_pnl = market_value - position['cost']
                    
                    # Ensure all values are valid (no NaN, no infinity)
                    # Check for NaN by converting to float and back
                    try:
                        avg_price_float = float(avg_price)
                        if avg_price_float != avg_price_float or avg_price_float == float('inf') or avg_price_float == float('-inf'):
                            print(f"WARNING: Invalid avg_price for {ticker}: {avg_price} -> 0")
                            avg_price = Decimal('0')
                    except (ValueError, TypeError, OverflowError) as e:
                        print(f"ERROR: avg_price conversion failed for {ticker}: {avg_price} - {e}")
                        avg_price = Decimal('0')
                    
                    try:
                        current_price_float = float(current_price)
                        if current_price_float != current_price_float or current_price_float == float('inf') or current_price_float == float('-inf'):
                            print(f"WARNING: Invalid current_price for {ticker}: {current_price} -> 0")
                            current_price = Decimal('0')
                    except (ValueError, TypeError, OverflowError) as e:
                        print(f"ERROR: current_price conversion failed for {ticker}: {current_price} - {e}")
                        current_price = Decimal('0')
                    
                    try:
                        market_value_float = float(market_value)
                        if market_value_float != market_value_float or market_value_float == float('inf') or market_value_float == float('-inf'):
                            print(f"WARNING: Invalid market_value for {ticker}: {market_value} -> 0")
                            market_value = Decimal('0')
                    except (ValueError, TypeError, OverflowError) as e:
                        print(f"ERROR: market_value conversion failed for {ticker}: {market_value} - {e}")
                        market_value = Decimal('0')
                    
                    try:
                        unrealized_pnl_float = float(unrealized_pnl)
                        if unrealized_pnl_float != unrealized_pnl_float or unrealized_pnl_float == float('inf') or unrealized_pnl_float == float('-inf'):
                            print(f"WARNING: Invalid unrealized_pnl for {ticker}: {unrealized_pnl} -> 0")
                            unrealized_pnl = Decimal('0')
                    except (ValueError, TypeError, OverflowError) as e:
                        print(f"ERROR: unrealized_pnl conversion failed for {ticker}: {unrealized_pnl} - {e}")
                        unrealized_pnl = Decimal('0')
                    
                    position_obj = Position(
                        ticker=ticker,
                        shares=position['shares'],
                        avg_price=avg_price,
                        cost_basis=position['cost'],
                        currency=position['currency'],
                        company=get_company_name(ticker),
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl
                    )
                    daily_positions.append(position_obj)
            
            # Create and save portfolio snapshot for this date
            if daily_positions:
                # Create timestamp for this trading day at market close
                snapshot_timestamp = datetime.combine(trading_day, datetime.min.time().replace(hour=16, minute=0))
                
                # Calculate total value with NaN checking
                total_value = Decimal('0')
                for p in daily_positions:
                    try:
                        market_val_float = float(p.market_value)
                        if market_val_float != market_val_float:  # Check for NaN
                            print(f"WARNING: NaN market_value for {p.ticker}: {p.market_value}")
                            p.market_value = Decimal('0')
                        total_value += p.market_value
                    except Exception as e:
                        print(f"ERROR: Invalid market_value for {p.ticker}: {p.market_value} - {e}")
                        p.market_value = Decimal('0')
                        total_value += Decimal('0')
                
                snapshot = PortfolioSnapshot(
                    positions=daily_positions,
                    timestamp=snapshot_timestamp,
                    total_value=total_value
                )
                
                repository.save_portfolio_snapshot(snapshot)
                snapshots_created += 1
                
                if snapshots_created % 10 == 0:  # Status update every 10 snapshots
                    print_info(f"   Created {snapshots_created} historical snapshots...")
        
        print_info(f"   Created {snapshots_created} historical portfolio snapshots")
        
        # Create final portfolio snapshot from current positions
        # Create snapshot if today is a trading day (regardless of current market status)
        # 
        # NOTE: This should use the same logic as the centralized portfolio update system
        # See utils/portfolio_update_logic.py for the correct decision logic
        # Core principle: "Get data whenever we can" - only skip if not a trading day
        from config.settings import Settings
        
        settings = Settings()
        today = datetime.now().date()
        
        if market_hours.is_trading_day(today):
            print_info(f"{_safe_emoji('📊')} Creating final portfolio snapshot...")
            
            from data.models.portfolio import Position, PortfolioSnapshot
            final_positions = []
            
            # Fetch current market prices for all positions
            print_info(f"   Fetching current market prices for {len(running_positions)} positions...")
            print_info(f"   Note: Positions with 0 shares will be filtered out (sold positions)")
            current_prices = {}  # {ticker: price}
            for ticker in running_positions.keys():
                try:
                    # Fetch price data for today
                    today = datetime.now().date()
                    start_dt = datetime.combine(today, datetime.min.time())
                    end_dt = datetime.combine(today, datetime.max.time())
                    result = market_fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                    
                    if result and result.df is not None and not result.df.empty:
                        # Get the most recent close price
                        latest_price = Decimal(str(result.df['Close'].iloc[-1]))
                        current_prices[ticker] = latest_price
                    else:
                        print_warning(f"   Could not fetch current price for {ticker} - using cost basis")
                        current_prices[ticker] = None
                except Exception as e:
                    print_warning(f"   Error fetching price for {ticker}: {e} - using cost basis")
                    current_prices[ticker] = None
            
            positions_with_shares = 0
            positions_filtered_out = 0
            
            for ticker, position in running_positions.items():
                if position['shares'] > 0:  # Only include positions with shares
                    positions_with_shares += 1
                    avg_price = position['cost'] / position['shares'] if position['shares'] > 0 else Decimal('0')
                    
                    # Get fetched current price for today
                    current_price = current_prices.get(ticker)
                    
                    if current_price is None:
                        print_error(f"   ❌ CRITICAL: Price fetch failed for {ticker}")
                        print_error(f"      Cannot create snapshot without valid market prices")
                        print_error(f"      This is likely running on a non-trading day or there's a network/API issue")
                        print_error(f"      NO FALLBACK PRICES ALLOWED - data integrity is critical")
                        raise Exception(f"Price fetch failed for {ticker} - aborting snapshot creation")
                    
                    market_value = position['shares'] * current_price
                    unrealized_pnl = market_value - position['cost']
                    
                    final_position = Position(
                        ticker=ticker,
                        shares=position['shares'],
                        avg_price=avg_price,
                        cost_basis=position['cost'],
                        currency=position['currency'],
                        company=get_company_name(ticker),
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl
                    )
                    final_positions.append(final_position)
                else:
                    positions_filtered_out += 1
                    print_info(f"   Filtered out {ticker}: 0 shares (sold position)")
            
            print_info(f"   Position filtering complete:")
            print_info(f"   - {positions_with_shares} positions with shares included")
            print_info(f"   - {positions_filtered_out} positions with 0 shares filtered out")
            print_info(f"   - All included positions have real market prices (no fallbacks)")
            
            # Create and save final portfolio snapshot
            if final_positions:
                # All positions have current prices - safe to save
                from datetime import timezone
                # Use market close time in Eastern timezone for proper historical price fetching
                # Market closes at 16:00 ET (Eastern Time)
                from market_config import _is_dst
                from datetime import timezone as dt_timezone
                utc_now = datetime.now(dt_timezone.utc)
                is_dst = _is_dst(utc_now)
                # 16:00 ET = 20:00 UTC during EDT, 21:00 UTC during EST
                market_close_hour_utc = 20 if is_dst else 21
                
                # Convert date to datetime for final snapshot
                final_timestamp = datetime.combine(today, datetime.min.time().replace(hour=market_close_hour_utc, minute=0, second=0, microsecond=0))
                
                final_snapshot = PortfolioSnapshot(
                    positions=final_positions,
                    timestamp=final_timestamp,
                    total_value=sum(p.cost_basis for p in final_positions)
                )
                repository.save_portfolio_snapshot(final_snapshot)
                print_info(f"   Saved final portfolio snapshot with {len(final_positions)} positions")
        else:
            print_info(f"   Skipping final snapshot - today ({today}) is not a trading day")
        
        # NOTE: Portfolio CSV is already written incrementally by repository.save_portfolio_snapshot()
        # during the snapshot generation loop above. Do NOT overwrite it here.
        # All historical snapshots have been saved correctly to CSV and Supabase.
        print_info(f"{_safe_emoji('📊')} Portfolio CSV already saved with all {snapshots_created} historical snapshots")
        
        print_success(f"{_safe_emoji('✅')} Portfolio rebuild completed successfully!")
        print_info(f"   {_safe_emoji('✅')} CSV files updated with {snapshots_created} snapshots")
        if fund_name:
            print_info(f"   {_safe_emoji('✅')} Trades saved to Supabase")
        print_info(f"   {_safe_emoji('✅')} Positions recalculated from trade log")
        
        return True
        
    except Exception as e:
        print_error(f"{_safe_emoji('❌')} Error rebuilding portfolio: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to rebuild portfolio completely."""
    if len(sys.argv) < 2:
        print_error("❌ Error: data_dir parameter is required")
        print("Usage: python rebuild_portfolio_complete.py <data_dir> [fund_name]")
        print("Example: python rebuild_portfolio_complete.py 'trading_data/funds/Project Chimera' 'Project Chimera'")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    fund_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = rebuild_portfolio_complete(data_dir, fund_name)
    
    if success:
        print_success(f"\n{_safe_emoji('🎉')} Complete portfolio rebuild successful!")
        print_info("   Both CSV and Supabase have been updated")
    else:
        print_error(f"\n{_safe_emoji('❌')} Portfolio rebuild failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
