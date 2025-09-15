#!/usr/bin/env python3
"""
Rebuild Portfolio from Trade Log - Complete Recreation

PURPOSE:
This script completely rebuilds the portfolio CSV from scratch based on the trade log.
It's designed to fix data inconsistencies, recover from corruption, or create a fresh
portfolio when the existing one has issues.

WHAT IT DOES:
1. Reads the trade log (llm_trade_log.csv) chronologically
2. Processes each trade and creates corresponding portfolio entries:
   - BUY entries for each purchase with exact trade details
   - HOLD entries for price tracking between trades (using Yahoo Finance API)
   - SELL entries for each sale with proper FIFO calculations
3. Recalculates all positions, cost basis, and P&L from scratch
4. Generates a clean, consistent portfolio CSV with proper formatting

WHEN TO USE:
- Portfolio CSV is corrupted or has inconsistent data
- Need to recover from a backup or data loss
- Want to verify calculations are correct
- Adding new features that require a fresh start
- Debugging portfolio display issues

TECHNICAL DETAILS:
- **Price Caching**: Uses PriceCache with MarketDataFetcher to minimize API calls and improve performance
- **Efficient API Usage**: Caches price data in memory to avoid redundant API requests for the same ticker/date
- **Timezone Handling**: Handles timezone-aware timestamps correctly throughout the process
- **FIFO Implementation**: Implements proper FIFO lot tracking for accurate P&L calculations
- **Weekend Handling**: Skips weekends when adding HOLD entries (no market data available)
- **Data Preservation**: Preserves all original trade data while rebuilding portfolio structure

Usage:
    python debug/rebuild_portfolio_from_scratch.py
    python debug/rebuild_portfolio_from_scratch.py test_data
    python debug/rebuild_portfolio_from_scratch.py "my trading" "US/Pacific"
    python debug/rebuild_portfolio_from_scratch.py "my trading" "US/Eastern"

Configuration:
    - Change DEFAULT_TIMEZONE to your local timezone
    - Market close times are automatically calculated based on timezone
    - Supported timezones: US/Pacific, US/Eastern, US/Central, US/Mountain, Canada/*, etc.
    - Focuses on North American markets: NYSE, NASDAQ, TSX (all close at 4:00 PM ET)
    - For other global markets, see comments in MARKET_CLOSE_TIMES section
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
import yfinance as yf  # retained for compatibility, core fetching uses MarketDataFetcher
import time
from decimal import Decimal, getcontext
import pytz

# Import emoji handling
try:
    from display.console_output import _safe_emoji
except ImportError:
    # Fallback if display module not available
    def _safe_emoji(emoji: str) -> str:
        return emoji

# Set precision for decimal calculations
getcontext().prec = 10

# Configuration - Market close times by timezone
# Based on North American markets (NYSE, NASDAQ, TSX) closing at 4:00 PM ET
MARKET_CLOSE_TIMES = {
    'US/Eastern': 16,  # 4:00 PM ET (NYSE, NASDAQ)
    'US/Pacific': 13,  # 1:00 PM PT (4:00 PM ET)
    'US/Central': 15,  # 3:00 PM CT (4:00 PM ET)
    'US/Mountain': 14, # 2:00 PM MT (4:00 PM ET)
    'Canada/Eastern': 16,  # 4:00 PM ET (TSX)
    'Canada/Pacific': 13,  # 1:00 PM PT (4:00 PM ET)
    'Canada/Central': 15,  # 3:00 PM CT (4:00 PM ET)
    'Canada/Mountain': 14, # 2:00 PM MT (4:00 PM ET)
}

# Note: This bot focuses on North American markets (NYSE, NASDAQ, TSX)
# Other global markets have different closing times:
# - London (LSE): 8:30 AM PDT (4:30 PM BST)
# - Frankfurt (DB): 8:30 AM PDT (5:30 PM CEST)  
# - Tokyo (JPX): 11:00 PM PDT previous day (3:00 PM JST)
# - Hong Kong (HKEX): 1:00 AM PDT (4:00 PM HKT)

# Default timezone - change this to your local timezone
DEFAULT_TIMEZONE = 'US/Pacific'  # Change to your timezone

def get_market_close_time(timezone_str: str = None) -> str:
    """Get market close time in the specified timezone"""
    if timezone_str is None:
        timezone_str = DEFAULT_TIMEZONE
    
    # Get the hour for market close in this timezone
    close_hour = MARKET_CLOSE_TIMES.get(timezone_str, 16)  # Default to 4 PM if not found
    
    # Get timezone info
    tz = pytz.timezone(timezone_str)
    
    # Get current date in the specified timezone
    now = datetime.now(tz)
    
    # Format as "YYYY-MM-DD HH:MM:SS TZ"
    timezone_abbr = now.strftime('%Z')
    return f"{now.strftime('%Y-%m-%d')} {close_hour:02d}:00:00 {timezone_abbr}"

# Use shared market data fetcher with price cache for efficiency
# This setup minimizes API calls by caching price data in memory
from market_data.price_cache import PriceCache
from market_data.data_fetcher import MarketDataFetcher
from market_data.market_hours import MarketHours
PRICE_CACHE = PriceCache()  # In-memory price cache to avoid redundant API calls
FETCHER = MarketDataFetcher(cache_instance=PRICE_CACHE)  # Fetcher uses the cache
MARKET_HOURS = MarketHours()  # For weekend detection

def get_current_price(ticker: str) -> float:
    """
    Get current price for a ticker using the cached market data fetcher.
    
    This function attempts to fetch the most recent available price for a ticker,
    falling back to historical data if current data isn't available. It uses
    the shared MarketDataFetcher with price caching for efficiency.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
    Returns:
        Current price as float, or 0.0 if no data available
        
    Note:
        Uses a 5-day lookback window to find the most recent price data.
        Returns 0.0 if no valid price data is found to prevent calculation errors.
    """
    try:
        end = pd.Timestamp.now()
        start = end - pd.Timedelta(days=5)
        result = FETCHER.fetch_price_data(ticker, start, end)
        df = result.df
        if df is not None and not df.empty and 'Close' in df.columns and result.source != "empty":
            return float(df['Close'].iloc[-1])
    except Exception:
        pass
    return 0.0

def get_historical_close_price(ticker: str, date_str: str) -> float:
    """
    Get historical close price for a ticker on a specific date.
    
    This function fetches the closing price for a ticker on the specified date,
    with intelligent fallback to nearby trading days if the exact date isn't available.
    It handles timezone-aware date parsing and uses the cached market data fetcher.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        date_str: Date string in format 'YYYY-MM-DD HH:MM:SS TZ' or similar
        
    Returns:
        Historical close price as float, or 0.0 if no data available
        
    Note:
        Uses a 3-day window around the target date to find the closest available
        trading day. This handles cases where the target date falls on weekends
        or holidays when markets are closed.
    """
    try:
        from utils.timezone_utils import parse_csv_timestamp
        date_obj = parse_csv_timestamp(date_str)
        if not date_obj:
            return None
        date_obj = date_obj.date()
        next_date = date_obj + timedelta(days=1)
        # Fetch the exact day range
        result = FETCHER.fetch_price_data(ticker, pd.Timestamp(date_obj), pd.Timestamp(next_date))
        df = result.df
        if df is not None and not df.empty and 'Close' in df.columns and result.source != "empty":
            # Find row matching the date
            day_rows = df[df.index.date == date_obj]
            if not day_rows.empty:
                return float(day_rows['Close'].iloc[0])
            # If only one row in range, use it
            return float(df['Close'].iloc[0])
        # Fallback: fetch previous 5 days and return last close
        result2 = FETCHER.fetch_price_data(ticker, pd.Timestamp(date_obj) - pd.Timedelta(days=7), pd.Timestamp(date_obj))
        df2 = result2.df
        if df2 is not None and not df2.empty and 'Close' in df2.columns and result2.source != "empty":
            return float(df2['Close'].iloc[-1])
        return 0.0
    except Exception:
        return 0.0

def rebuild_portfolio_from_scratch(data_dir: str = "trading_data/prod", timezone_str: str = None):
    """
    Completely rebuild portfolio CSV from trade log with full recalculation.
    
    This is the main function that orchestrates the complete portfolio rebuild process.
    It reads the trade log, processes all trades chronologically, and generates a
    fresh portfolio CSV with proper HOLD entries for price tracking.
    
    PROCESS OVERVIEW:
    1. Load and validate trade log data
    2. Process all trades chronologically (BUY/SELL entries)
    3. Generate HOLD entries for price tracking between trades
    4. Recalculate all positions, cost basis, and P&L from scratch
    5. Write clean portfolio CSV with proper formatting
    
    Args:
        data_dir: Directory containing trade log and portfolio files
        timezone_str: Timezone for market close time calculations (defaults to DEFAULT_TIMEZONE)
        
    Returns:
        None (writes portfolio CSV to disk)
        
    Raises:
        FileNotFoundError: If trade log file doesn't exist
        ValueError: If trade log data is invalid or empty
        
    Note:
        This function completely overwrites the existing portfolio CSV.
        Make sure to backup your data before running if needed.
    """
    if timezone_str is None:
        timezone_str = DEFAULT_TIMEZONE
    
    data_path = Path(data_dir)
    trade_log_file = data_path / "llm_trade_log.csv"
    portfolio_file = data_path / "llm_portfolio_update.csv"
    
    print(f"{_safe_emoji('🔄')} Rebuilding Portfolio from Trade Log")
    print("=" * 50)
    print(f"📁 Using data directory: {data_dir}")
    print(f"🕐 Using timezone: {timezone_str}")
    print(f"🕐 Market close time: {MARKET_CLOSE_TIMES.get(timezone_str, 16)}:00 local time")
    
    if not trade_log_file.exists():
        print(f"{_safe_emoji('❌')} Trade log not found: {trade_log_file}")
        return False
    
    try:
        # BACKUP THE FILE FIRST
        backup_dir = data_path / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"{portfolio_file.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if portfolio_file.exists():
            portfolio_df = pd.read_csv(portfolio_file)
            portfolio_df.to_csv(backup_file, index=False)
            print(f"{_safe_emoji('💾')} Backed up portfolio to: {backup_file}")
        
        # Read trade log
        trade_df = pd.read_csv(trade_log_file)
        print(f"{_safe_emoji('📊')} Loaded {len(trade_df)} trades from trade log")
        
        # Sort trades by date
        trade_df = trade_df.sort_values('Date').reset_index(drop=True)
        
        # Process trades chronologically to build complete portfolio
        portfolio_entries = []
        running_positions = defaultdict(lambda: {'shares': Decimal('0'), 'cost': Decimal('0'), 'trades': []})
        
        print(f"\n📈 Processing trades chronologically:")
        
        for _, trade in trade_df.iterrows():
            ticker = trade['Ticker']
            date = trade['Date']
            shares = Decimal(str(trade['Shares']))  # Keep original precision
            price = Decimal(str(trade['Price']))
            cost = Decimal(str(trade['Cost Basis']))
            pnl = Decimal(str(trade['PnL']))
            reason = trade['Reason']
            
            # Determine if this is a buy or sell
            is_sell = 'SELL' in reason.upper() or 'sell' in reason.lower()
            
            print(f"   {date} | {ticker} | {shares:.4f} @ ${price:.2f} | ${cost:.2f} | PnL: ${pnl:.2f} | {reason}")
            
            if is_sell:
                # For sells, create entry with 0 shares and sell details
                avg_price = running_positions[ticker]['cost'] / running_positions[ticker]['shares'] if running_positions[ticker]['shares'] > 0 else Decimal('0')
                
                portfolio_entries.append({
                    'Date': date,
                    'Ticker': ticker,
                    'Shares': Decimal('0'),
                    'Average Price': Decimal('0'),
                    'Cost Basis': Decimal('0'),
                    'Stop Loss': Decimal('0'),
                    'Current Price': price,
                    'Total Value': Decimal('0'),
                    'PnL': pnl,  # Use actual PnL from trade log
                    'Action': 'SELL',
                    'Company': get_company_name(ticker),
                    'Currency': get_currency(ticker)
                })
                
                # Reset position after sell
                running_positions[ticker] = {'shares': Decimal('0'), 'cost': Decimal('0'), 'trades': []}
            else:
                # For buys, update running position
                running_positions[ticker]['shares'] += shares
                running_positions[ticker]['cost'] += cost
                running_positions[ticker]['trades'].append({'shares': shares, 'price': price, 'cost': cost})
                
                # Calculate current values
                total_shares = running_positions[ticker]['shares']
                total_cost = running_positions[ticker]['cost']
                avg_price = total_cost / total_shares if total_shares > 0 else Decimal('0')
                current_price = price  # Use the trade price as current price
                total_value = total_shares * current_price
                unrealized_pnl = (current_price - avg_price) * total_shares
                
                portfolio_entries.append({
                    'Date': date,
                    'Ticker': ticker,
                    'Shares': total_shares,
                    'Average Price': avg_price,
                    'Cost Basis': total_cost,
                    'Stop Loss': Decimal('0'),
                    'Current Price': current_price,
                    'Total Value': total_value,
                    'PnL': unrealized_pnl,
                    'Action': 'BUY',
                    'Company': get_company_name(ticker),
                    'Currency': get_currency(ticker)
                })
        
        # Add HOLD entries for every day between trades and current positions
        print(f"\n📊 Adding HOLD entries for price tracking...")
        
        # Get all unique trade dates
        trade_dates = sorted(trade_df['Date'].unique())
        print(f"   Trade dates: {trade_dates}")
        
        # Create a list of all dates we need HOLD entries for
        all_dates = []
        unique_calendar_dates = set()
        
        # First, collect all unique calendar dates from trade dates
        for trade_date in trade_dates:
            from utils.timezone_utils import parse_csv_timestamp
            date_obj = parse_csv_timestamp(trade_date)
            if date_obj:
                calendar_date = date_obj.strftime('%Y-%m-%d')
                unique_calendar_dates.add(calendar_date)
        
        # Convert to sorted list
        unique_calendar_dates = sorted(list(unique_calendar_dates))
        
        # Generate all dates between first trade and today
        if unique_calendar_dates:
            from utils.timezone_utils import parse_csv_timestamp
            first_date = parse_csv_timestamp(unique_calendar_dates[0])
            last_date = parse_csv_timestamp(unique_calendar_dates[-1])
            if not first_date or not last_date:
                print("Error: Could not parse trade dates")
                return False
            today = datetime.now()
            
            # Check if market is open today (before market close time)
            tz = pytz.timezone(timezone_str)
            current_time = today.astimezone(tz)
            market_close_hour = MARKET_CLOSE_TIMES.get(timezone_str, 16)
            
            # Always include today, but use different timestamp logic
            end_date = today.date()
            
            if current_time.hour < market_close_hour:
                print(f"   ⏰ Market still open ({current_time.strftime('%H:%M')} < {market_close_hour}:00), using current time for today's HOLD entries")
            else:
                print(f"   ⏰ Market closed ({current_time.strftime('%H:%M')} >= {market_close_hour}:00), using market close time for today's HOLD entries")
            
            current_date = first_date
            while current_date.date() <= end_date:
                all_dates.append(current_date.strftime('%Y-%m-%d %H:%M:%S PDT'))
                current_date += timedelta(days=1)
        
        print(f"   Adding HOLD entries for {len(all_dates)} dates")
        
        # Process each date and add HOLD entries for stocks that have shares
        for hold_date in all_dates:
            print(f"   Processing {hold_date}...")
            
            # Check if this date already has trade entries
            from utils.timezone_utils import parse_csv_timestamp
            hold_date_obj = parse_csv_timestamp(hold_date)
            if not hold_date_obj:
                continue
            
            # WEEKEND HANDLING: Skip weekends (Saturday/Sunday) as there's no market data available
            # This prevents "Could not get price" warnings for weekend dates when trying to fetch
            # historical prices for HOLD entries. The portfolio will show the last available
            # trading day's price for positions held over weekends.
            if not MARKET_HOURS.is_trading_day(hold_date_obj):
                print(f"     Skipping {hold_date_obj.strftime('%Y-%m-%d')} (weekend)")
                continue
                
            date_str = hold_date_obj.strftime('%Y-%m-%d')
            
            # Get list of tickers that were traded on this exact date
            traded_tickers_on_date = set()
            for _, trade in trade_df.iterrows():
                trade_date_obj = parse_csv_timestamp(trade['Date'])
                if trade_date_obj:
                    trade_date = trade_date_obj.strftime('%Y-%m-%d')
                    if trade_date == date_str:
                        traded_tickers_on_date.add(trade['Ticker'])
            
            print(f"     Tickers traded on {date_str}: {traded_tickers_on_date}")
            
            # Recalculate positions up to this date
            temp_positions = defaultdict(lambda: {'shares': Decimal('0'), 'cost': Decimal('0')})
            
            # Process all trades up to this date
            for _, trade in trade_df.iterrows():
                trade_date = trade['Date']
                if trade_date <= hold_date:
                    ticker = trade['Ticker']
                    shares = Decimal(str(trade['Shares']))  # Keep original precision
                    cost = Decimal(str(trade['Cost Basis']))
                    reason = trade['Reason']
                    
                    is_sell = 'SELL' in reason.upper() or 'sell' in reason.lower()
                    
                    if is_sell:
                        # Reset position after sell
                        temp_positions[ticker] = {'shares': Decimal('0'), 'cost': Decimal('0')}
                    else:
                        # Add to position
                        temp_positions[ticker]['shares'] += shares
                        temp_positions[ticker]['cost'] += cost
            
            # Add HOLD entry for each ticker that has shares on this date
            for ticker, position in temp_positions.items():
                if position['shares'] > 0:
                    # Skip HOLD entry if this ticker was traded on this date (to avoid duplicates)
                    if ticker in traded_tickers_on_date:
                        print(f"     Skipping HOLD for {ticker} (was traded on {date_str})")
                        continue
                    
                    # Determine the correct price for this hold date
                    tz = pytz.timezone(timezone_str)
                    if hold_date_obj.tzinfo is None:
                        # Naive datetime - localize it
                        hold_date_obj_tz = tz.localize(hold_date_obj)
                    else:
                        # Already timezone-aware - convert to target timezone
                        hold_date_obj_tz = hold_date_obj.astimezone(tz)
                    if hold_date_obj_tz.date() == current_time.date():
                        # Today
                        if current_time.hour < market_close_hour:
                            price_value = get_current_price(ticker)
                        else:
                            price_value = get_historical_close_price(ticker, date_str)
                    else:
                        # Historical day
                        price_value = get_historical_close_price(ticker, date_str)
                    
                    if price_value > 0:
                        current_price_decimal = Decimal(str(price_value))
                        avg_price = position['cost'] / position['shares']
                        total_value = position['shares'] * current_price_decimal
                        unrealized_pnl = (current_price_decimal - avg_price) * position['shares']
                        
                        # Set HOLD entries timestamp based on market status
                        if hold_date_obj_tz.date() == current_time.date() and current_time.hour < market_close_hour:
                            # Use current time for today if market is still open
                            hold_date_str = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                        else:
                            # Use market close time for all other days
                            close_hour = MARKET_CLOSE_TIMES.get(timezone_str, 16)
                            timezone_abbr = hold_date_obj_tz.strftime('%Z')
                            hold_date_str = f"{date_str} {close_hour:02d}:00:00 {timezone_abbr}"
                        
                        portfolio_entries.append({
                            'Date': hold_date_str,
                            'Ticker': ticker,
                            'Shares': position['shares'],
                            'Average Price': avg_price,
                            'Cost Basis': position['cost'],
                            'Stop Loss': Decimal('0'),
                            'Current Price': current_price_decimal,
                            'Total Value': total_value,
                            'PnL': unrealized_pnl,
                            'Action': 'HOLD',
                            'Company': get_company_name(ticker),
                            'Currency': get_currency(ticker)
                        })
                        print(f"     Added HOLD: {ticker} @ ${price_value:.2f}")
                    else:
                        print(f"     ⚠️  Could not get price for {ticker} on {hold_date}")
        
        # Create new portfolio DataFrame
        new_portfolio_df = pd.DataFrame(portfolio_entries)
        
        # Sort by date and ticker
        new_portfolio_df = new_portfolio_df.sort_values(['Date', 'Ticker']).reset_index(drop=True)
        
        print(f"\n📊 Generated {len(new_portfolio_df)} portfolio entries from trade log")
        
        # Show summary of positions
        print(f"\n📈 Final positions:")
        for ticker in new_portfolio_df['Ticker'].unique():
            ticker_entries = new_portfolio_df[new_portfolio_df['Ticker'] == ticker]
            latest = ticker_entries.iloc[-1]
            print(f"   {ticker}: {latest['Shares']:.2f} shares @ ${latest['Average Price']:.2f} | ${latest['Cost Basis']:.2f} | {latest['Action']} | PnL: ${latest['PnL']:.2f}")
        
        # Convert Decimal objects to float with proper precision
        numeric_columns = ['Shares', 'Average Price', 'Cost Basis', 'Stop Loss', 'Current Price', 'Total Value', 'PnL']
        for col in numeric_columns:
            if col in new_portfolio_df.columns:
                # Convert Decimal to float, preserving precision
                new_portfolio_df[col] = new_portfolio_df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
                if col == 'Shares':
                    # Round shares to 4 decimal places
                    new_portfolio_df[col] = new_portfolio_df[col].round(4)
                else:
                    # Round other columns to 2 decimal places
                    new_portfolio_df[col] = new_portfolio_df[col].round(2)
        
        # Save new portfolio
        new_portfolio_df.to_csv(portfolio_file, index=False)
        
        print(f"\n{_safe_emoji('✅')} Portfolio completely rebuilt from trade log: {portfolio_file}")
        print(f"   Created {len(new_portfolio_df)} entries from {len(trade_df)} trades")
        print(f"   Added HOLD entries for price tracking")
        print(f"   Used actual PnL from trade log for sell transactions")
        print(f"   Backup created at: {backup_file}")
        
        return True
        
    except Exception as e:
        print(f"{_safe_emoji('❌')} Error rebuilding portfolio: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_company_name(ticker: str) -> str:
    """Get company name for ticker using yfinance lookup"""
    try:
        from utils.ticker_utils import get_company_name as lookup_company_name
        return lookup_company_name(ticker)
    except Exception as e:
        print(f"Warning: Could not lookup company name for {ticker}: {e}")
        return 'Unknown'

def get_currency(ticker: str) -> str:
    """Get currency for ticker"""
    if '.TO' in ticker or '.V' in ticker:
        return 'CAD'
    return 'USD'

def main():
    """Main function to rebuild portfolio from scratch"""
    # Check if data directory argument provided
    data_dir = "trading_data/prod"
    timezone_str = None
    
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    if len(sys.argv) > 2:
        timezone_str = sys.argv[2]
    
    # Show environment banner
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from display.console_output import print_environment_banner
    print_environment_banner(data_dir)
    
    success = rebuild_portfolio_from_scratch(data_dir, timezone_str)
    
    if success:
        print("\n🎉 Portfolio rebuilt successfully from trade log!")
        print("   All entries created from scratch based on trade log")
    else:
        print(f"\n{_safe_emoji('❌')} Failed to rebuild portfolio")
        sys.exit(1)

if __name__ == "__main__":
    main()
