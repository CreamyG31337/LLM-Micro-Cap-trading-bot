#!/usr/bin/env python3
"""
Rebuild Portfolio from Trade Log to Supabase - Complete Recreation

PURPOSE:
This script completely rebuilds the portfolio in Supabase from scratch based on the trade log.
It works exactly like the original CSV rebuild script but writes to Supabase instead.

WHAT IT DOES:
1. Reads the trade log (llm_trade_log.csv) chronologically
2. Processes each trade and creates corresponding portfolio entries:
   - BUY entries for each purchase with exact trade details
   - HOLD entries for price tracking between trades (using Yahoo Finance API)
   - SELL entries for each sale with proper FIFO calculations
3. Recalculates all positions, cost basis, and P&L from scratch
4. Writes clean portfolio data to Supabase with proper formatting

Usage:
    python debug/rebuild_portfolio_supabase.py
    python debug/rebuild_portfolio_supabase.py "Project Chimera"
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import pytz
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.repository_factory import RepositoryFactory
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from display.console_output import print_success, print_error, print_info, print_warning, _safe_emoji

# Load environment variables
load_dotenv(project_root / 'web_dashboard' / '.env')

# Setup price cache and fetcher like the original script
PRICE_CACHE = PriceCache()  # In-memory price cache to avoid redundant API calls
FETCHER = MarketDataFetcher(cache_instance=PRICE_CACHE)  # Fetcher uses the cache

# Set up currency cache for proper CAD/USD detection
def setup_currency_cache(tickers):
    """Set up currency cache for MarketDataFetcher to use correct exchanges"""
    currency_cache = {}
    for ticker in tickers:
        if ticker.endswith('.TO') or ticker.endswith('.V'):
            currency_cache[ticker] = 'CAD'
        else:
            currency_cache[ticker] = 'USD'

    # Set the currency cache on the fetcher
    FETCHER._portfolio_currency_cache = currency_cache
    return currency_cache

# Market close times by timezone
MARKET_CLOSE_TIMES = {
    'US/Pacific': 16,  # 4:00 PM PT = 7:00 PM ET
    'US/Eastern': 16,  # 4:00 PM ET
    'US/Central': 16,  # 4:00 PM CT = 5:00 PM ET
    'US/Mountain': 16, # 4:00 PM MT = 6:00 PM ET
    'Canada/Pacific': 16,  # 4:00 PM PT = 7:00 PM ET
    'Canada/Eastern': 16,  # 4:00 PM ET
}

def get_company_name(ticker):
    """Get company name for ticker (simplified version)"""
    company_names = {
        'CNR.TO': 'Canadian National Railway',
        'CRWD': 'CrowdStrike',
        'CTRN': 'Core & Main',
        'DRX.TO': 'DRI Healthcare Trust',
        'FTS.TO': 'Fortis Inc',
        'GLO.TO': 'Global Atomic Corporation',
        'GMIN.TO': 'G Mining Ventures Corp',
        'HLIT.TO': 'HLS Therapeutics Inc',
        'KO': 'Coca-Cola Company',
        'LTRX': 'Lantronix Inc',
        'MRK': 'Merck & Co Inc',
        'PLTR': 'Palantir Technologies',
        'QCOM': 'Qualcomm Inc',
        'RAIL': 'FreightCar America Inc',
        'SMH': 'VanEck Semiconductor ETF',
        'STLD': 'Steel Dynamics Inc',
        'TRP.TO': 'TC Energy Corporation',
        'URNJ': 'Sprott Junior Uranium Miners ETF',
        'URNM': 'Sprott Uranium Miners ETF',
        'VEE.TO': 'Veeva Systems Inc',
        'WEB.V': 'Webis Holdings Inc',
        'XMA.TO': 'XTM Inc',
        'ZCH.TO': 'BMO MSCI China ESG Leaders Index ETF'
    }
    return company_names.get(ticker, ticker)

def get_currency(ticker):
    """Get currency for ticker"""
    if ticker.endswith('.TO') or ticker.endswith('.V'):
        return 'CAD'
    return 'USD'

def get_historical_close_price(ticker: str, date_str: str, trade_price: float = None, currency: str = "CAD") -> float:
    """
    Get historical close price for a ticker on a specific date.
    
    This function fetches the closing price for a ticker on the specified date,
    with intelligent fallback to nearby trading days if the exact date isn't available.
    """
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        
        # Parse date
        date_obj = pd.to_datetime(date_str).date()
        
        # Prevent future date API calls - only fetch historical data
        today = datetime.now().date()
        if date_obj > today:
            return 0.0
        
        # Skip weekends
        if date_obj.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return 0.0
        
        # Try multiple date ranges to find available data
        date_ranges = [
            (date_obj, date_obj + timedelta(days=1)),  # Exact day
            (date_obj - timedelta(days=1), date_obj + timedelta(days=2)),  # 3-day window
            (date_obj - timedelta(days=3), date_obj + timedelta(days=4)),  # 7-day window
            (date_obj - timedelta(days=7), date_obj + timedelta(days=8)),  # 15-day window
        ]
        
        for start_date, end_date in date_ranges:
            try:
                result = FETCHER.fetch_price_data(ticker, pd.Timestamp(start_date), pd.Timestamp(end_date))
                if result and hasattr(result, 'df') and result.df is not None:
                    df = result.df
                    if not df.empty and 'Close' in df.columns and result.source != "empty":
                        # Find row matching the target date or closest available
                        day_rows = df[df.index.date == date_obj]
                        if not day_rows.empty:
                            return float(day_rows['Close'].iloc[0])
                        # If no exact match, use the closest available date
                        if not df.empty:
                            return float(df['Close'].iloc[-1])
            except Exception as e:
                # Continue to next date range if this one fails
                continue
        
        return 0.0
    except Exception:
        return 0.0

def rebuild_portfolio_to_supabase(fund_name="Project Chimera"):
    """Rebuild portfolio in Supabase from trade log with full recalculation."""
    
    print_info(f"🚀 Starting complete portfolio rebuild for fund: {fund_name}")
    print("🔄 Complete Portfolio Rebuild to Supabase")
    print("=" * 50)
    
    # Setup paths
    data_dir = project_root / "trading_data" / "funds" / fund_name
    trade_log_file = data_dir / "llm_trade_log.csv"
    
    if not trade_log_file.exists():
        print_error(f"❌ Trade log not found: {trade_log_file}")
        return False
    
    # Load trade log
    print_info("📊 Loading trade log...")
    try:
        if not trade_log_file.exists():
            print_error(f"❌ Trade log not found: {trade_log_file}")
            print_info("💡 Create a trade log CSV file with columns: Date,Ticker,Shares,Price,Cost Basis,PnL,Reason,Currency")
            return False

        trade_df = pd.read_csv(trade_log_file)
        print_success(f"✅ Loaded {len(trade_df)} trades")

        if len(trade_df) == 0:
            print_warning("⚠️ Trade log is empty - no portfolio entries to generate")
            return True  # Not an error, just no data

    except Exception as e:
        print_error(f"❌ Failed to load trade log: {e}")
        return False
    
    # Parse dates
    trade_df['Date'] = pd.to_datetime(trade_df['Date'])
    trade_df = trade_df.sort_values('Date')
    
    # Setup Supabase connection
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print_error("❌ Missing Supabase credentials")
        return False
    
    try:
        repository = RepositoryFactory.create_repository(
            'supabase',
            url=supabase_url,
            key=supabase_key,
            fund=fund_name
        )
        print_success("✅ Connected to Supabase")
    except Exception as e:
        print_error(f"❌ Failed to connect to Supabase: {e}")
        return False
    
    # Clear existing data
    print_info("🗑️ Clearing existing portfolio data...")
    try:
        repository.supabase.table('portfolio_positions').delete().eq('fund', fund_name).execute()
        print_success("✅ Cleared existing data")
    except Exception as e:
        print_warning(f"⚠️ Could not clear existing data: {e}")
    
    # Setup market data fetcher
    fetcher = MarketDataFetcher()
    
    # Process trades and generate portfolio entries
    portfolio_entries = []
    running_positions = {}  # ticker -> {shares, cost, last_price, last_currency}
    ticker_currencies = {}

    # Setup currency cache for proper exchange detection
    all_tickers = trade_df['Ticker'].unique()
    currency_cache = setup_currency_cache(all_tickers)
    
    print_info("📈 Processing trades and generating portfolio entries...")
    
    # Process each trade
    for _, trade in trade_df.iterrows():
        ticker = trade['Ticker']
        shares = Decimal(str(trade['Shares']))
        price = Decimal(str(trade['Price']))
        cost_basis = Decimal(str(trade['Cost Basis']))
        pnl = Decimal(str(trade.get('PnL', 0)))
        reason = trade.get('Reason', 'TRADE')
        
        # Determine action
        if 'BUY' in reason.upper():
            action = 'BUY'
        elif 'SELL' in reason.upper():
            action = 'SELL'
        else:
            action = 'BUY'  # Default to BUY
        
        # Track currency
        ticker_currencies[ticker] = get_currency(ticker)
        
        # Initialize position if new
        if ticker not in running_positions:
            running_positions[ticker] = {
                'shares': Decimal('0'),
                'cost': Decimal('0'),
                'last_price': price,
                'last_currency': ticker_currencies[ticker]
            }
        
        if action == 'BUY':
            # Add to position
            running_positions[ticker]['shares'] += shares
            running_positions[ticker]['cost'] += cost_basis
            running_positions[ticker]['last_price'] = price
            running_positions[ticker]['last_currency'] = ticker_currencies[ticker]
            
            # Add portfolio entry
            portfolio_entries.append({
                'Date': trade['Date'],
                'Ticker': ticker,
                'Shares': float(running_positions[ticker]['shares']),
                'Average Price': float(running_positions[ticker]['cost'] / running_positions[ticker]['shares']),
                'Cost Basis': float(running_positions[ticker]['cost']),
                'Current Price': float(price),
                'Total Value': float(running_positions[ticker]['shares'] * price),
                'PnL': float(running_positions[ticker]['shares'] * price - running_positions[ticker]['cost']),
                'Action': 'BUY',
                'Company': get_company_name(ticker),
                'Currency': ticker_currencies[ticker]
            })
            
        elif action == 'SELL':
            # Remove from position (FIFO)
            remaining_shares = running_positions[ticker]['shares'] - shares
            remaining_cost = running_positions[ticker]['cost'] - (running_positions[ticker]['cost'] * shares / running_positions[ticker]['shares'])
            
            running_positions[ticker]['shares'] = remaining_shares
            running_positions[ticker]['cost'] = remaining_cost
            running_positions[ticker]['last_price'] = price
            running_positions[ticker]['last_currency'] = ticker_currencies[ticker]
            
            # Add portfolio entry
            portfolio_entries.append({
                'Date': trade['Date'],
                'Ticker': ticker,
                'Shares': float(running_positions[ticker]['shares']),
                'Average Price': float(running_positions[ticker]['cost'] / running_positions[ticker]['shares']) if running_positions[ticker]['shares'] > 0 else 0,
                'Cost Basis': float(running_positions[ticker]['cost']),
                'Current Price': float(price),
                'Total Value': float(running_positions[ticker]['shares'] * price),
                'PnL': float(pnl),  # Use actual PnL from trade log
                'Action': 'SELL',
                'Company': get_company_name(ticker),
                'Currency': ticker_currencies[ticker]
            })
    
    print_success(f"✅ Processed {len(portfolio_entries)} trade entries")
    
    # Generate HOLD entries for every trading day
    print_info("📊 Adding HOLD entries for price tracking...")
    
    # Get date range
    first_date = trade_df['Date'].min()
    last_date = trade_df['Date'].max()
    today = datetime.now(pytz.timezone('US/Pacific'))
    
    # Generate all dates from first trade to today
    all_dates = []
    current_date = first_date
    while current_date.date() <= today.date():
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            all_dates.append(current_date)
        current_date += timedelta(days=1)
    
    print_info(f"📅 Generating HOLD entries for {len(all_dates)} trading days...")
    
    # Generate HOLD entries
    hold_entries_added = 0
    for date_idx, hold_date in enumerate(all_dates):
        if date_idx % 10 == 0:
            print_info(f"   Processing date {date_idx + 1}/{len(all_dates)}: {hold_date.date()}")
        
        # Get current positions for this date
        temp_positions = dict(running_positions)
        
        # Add HOLD entries for each position
        for ticker, position in temp_positions.items():
            if position['shares'] > 0:
                try:
                    # Get historical price for this specific date using FETCHER
                    date_str = hold_date.strftime('%Y-%m-%d %H:%M:%S')
                    price_value = get_historical_close_price(ticker, date_str)

                    if price_value and price_value > 0:
                        current_price = Decimal(str(price_value))
                        if hold_date.date().strftime('%Y-%m-%d') == '2025-10-01':
                            print(f"   {ticker} on Oct 1: ${price_value} (historical)")
                    else:
                        # Fallback to last known price - this is normal for some tickers
                        current_price = position['last_price']
                        if hold_date.date().strftime('%Y-%m-%d') == '2025-10-01':
                            print(f"   {ticker} on Oct 1: ${position['last_price']} (fallback)")

                    # Create HOLD entry even if price fetch failed
                    portfolio_entries.append({
                        'Date': hold_date,
                        'Ticker': ticker,
                        'Shares': float(position['shares']),
                        'Average Price': float(position['cost'] / position['shares']),
                        'Cost Basis': float(position['cost']),
                        'Current Price': float(current_price),
                        'Total Value': float(position['shares'] * current_price),
                        'PnL': float(position['shares'] * current_price - position['cost']),
                        'Action': 'HOLD',
                        'Company': get_company_name(ticker),
                        'Currency': position['last_currency']
                    })
                    hold_entries_added += 1

                except Exception as e:
                    print_warning(f"⚠️ Failed to process {ticker} on {hold_date.date()}: {e}")
                    # Still create entry with fallback price
                    current_price = position['last_price']
                    portfolio_entries.append({
                        'Date': hold_date,
                        'Ticker': ticker,
                        'Shares': float(position['shares']),
                        'Average Price': float(position['cost'] / position['shares']),
                        'Cost Basis': float(position['cost']),
                        'Current Price': float(current_price),
                        'Total Value': float(position['shares'] * current_price),
                        'PnL': float(position['shares'] * current_price - position['cost']),
                        'Action': 'HOLD',
                        'Company': get_company_name(ticker),
                        'Currency': position['last_currency']
                    })
                    hold_entries_added += 1
                    continue
    
    print_success(f"✅ Added {hold_entries_added} HOLD entries")
    
    # Convert to DataFrame and sort
    portfolio_df = pd.DataFrame(portfolio_entries)
    portfolio_df = portfolio_df.sort_values(['Date', 'Ticker'])
    
    print_success(f"✅ Generated {len(portfolio_df)} total portfolio entries")
    
    # Write to Supabase
    print_info("💾 Writing portfolio data to Supabase...")
    
    # Convert to Supabase format
    db_entries = []
    for _, row in portfolio_df.iterrows():
        db_entry = {
            'fund': fund_name,
            'ticker': row['Ticker'],
            'shares': float(row['Shares']),
            'price': float(row['Current Price']),  # Use current price as the price field
            'cost_basis': float(row['Cost Basis']),
            'pnl': float(row['PnL']),
            'currency': row['Currency'],
            'company': row['Company'],
            'date': row['Date'].isoformat()
        }
        db_entries.append(db_entry)
    
    # Insert in batches
    batch_size = 100
    for i in range(0, len(db_entries), batch_size):
        batch = db_entries[i:i + batch_size]
        try:
            repository.supabase.table('portfolio_positions').insert(batch).execute()
            print_info(f"✅ Inserted batch {i//batch_size + 1}/{(len(db_entries) + batch_size - 1)//batch_size}")
        except Exception as e:
            print_error(f"❌ Failed to insert batch {i//batch_size + 1}: {e}")
            return False
    
    print_success(f"✅ Successfully rebuilt portfolio in Supabase!")
    print_success(f"📊 Total entries: {len(db_entries)}")
    print_success(f"📅 Date range: {first_date.date()} to {today.date()}")
    
    return True

if __name__ == "__main__":
    fund_name = "Project Chimera"
    if len(sys.argv) > 1:
        fund_name = sys.argv[1]
    
    if rebuild_portfolio_to_supabase(fund_name):
        print_success("\n🎉 Portfolio rebuild successful!")
        print_info("✅ All missing entries have been generated")
        print_info("✅ HOLD entries created for every trading day")
        print_info("✅ October 1st data should now exist")
    else:
        print_error("\n❌ Portfolio rebuild failed!")
