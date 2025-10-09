#!/usr/bin/env python3
"""
Debug script to investigate why 5-day P&L is showing as N/A in the portfolio summary.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal

# Set up the path and imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_5day_pnl():
    """Debug the 5-day P&L calculation step by step."""
    print("🐛 Debugging 5-Day P&L Calculation")
    print("=" * 50)
    
    try:
        # Import necessary modules
        from portfolio.fund_manager import FundManager
        from data.repositories.repository_factory import RepositoryContainer
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from market_data.market_hours import MarketHours
        from financial.pnl_calculator import PnLCalculator
        
        # Initialize components
        print("📦 Initializing components...")
        fund_manager = FundManager('funds.yml')
        funds = fund_manager.get_all_funds()
        default_fund = funds[0] if funds else None
        
        if not default_fund:
            print("❌ No funds found")
            return
        
        print(f"💰 Using fund: {default_fund.name}")
        
        # Initialize repository
        repository_container = RepositoryContainer()
        fund_data_dir = f"trading_data/funds/{default_fund.name}"
        repo_config = {
            'default': {
                'type': 'csv',
                'data_directory': fund_data_dir
            }
        }
        repository_container.configure(repo_config)
        repository = repository_container.get_repository('default')
        
        print(f"🏛️ Repository: {repository}")
        
        # Load portfolio snapshot
        from portfolio.portfolio_manager import PortfolioManager
        portfolio_manager = PortfolioManager(repository, default_fund)
        portfolio_snapshots = portfolio_manager.load_portfolio()
        
        if not portfolio_snapshots:
            print("❌ No portfolio snapshots found")
            return
        
        latest_snapshot = portfolio_snapshots[-1]
        print(f"📊 Latest snapshot: {latest_snapshot.timestamp.date()} with {len(latest_snapshot.positions)} positions")
        
        # Initialize market components with proper Settings
        from config.settings import Settings
        settings = Settings()
        settings.set('repository.csv.data_directory', str(repository.data_dir))
        
        price_cache = PriceCache(settings=settings)
        market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
        market_hours = MarketHours()
        pnl_calculator = PnLCalculator(repository)
        
        # Get a sample ticker to debug
        if not latest_snapshot.positions:
            print("❌ No positions found in latest snapshot")
            return
            
        # Find an older position that should have 5-day P&L data
        position = None
        for pos in latest_snapshot.positions:
            try:
                trades = repository.get_trade_history(pos.ticker)
                if trades:
                    buy_trades = [t for t in trades if t.action.upper() == 'BUY']
                    if buy_trades:
                        first_buy = min(buy_trades, key=lambda t: t.timestamp)
                        opened_date = first_buy.timestamp.strftime('%m-%d-%y')
                        
                        # Check if this position is old enough
                        from datetime import datetime as _dt
                        opened_dt = _dt.strptime(opened_date, '%m-%d-%y')
                        if opened_dt.year < 2000:
                            opened_dt = opened_dt.replace(year=opened_dt.year + 2000)
                        
                        tz = market_hours.get_trading_timezone()
                        opened_dt = tz.localize(opened_dt)
                        now_tz = _dt.now(tz)
                        
                        days_held_trading = market_hours.trading_days_between(opened_dt, now_tz)
                        
                        if days_held_trading > 5:
                            position = pos
                            print(f"🔍 Found older position: {pos.ticker} ({days_held_trading} trading days held)")
                            break
            except Exception:
                continue
                
        if position is None:
            print("❌ No positions found with >5 trading days")
            position = latest_snapshot.positions[0]  # Use first position anyway
        print(f"\n🎯 Debugging ticker: {position.ticker}")
        print(f"   Shares: {position.shares}")
        print(f"   Current Price: ${position.current_price}")
        print(f"   Currency: {position.currency}")
        
        # Step 1: Check opened date from trade log
        print(f"\n📅 Step 1: Checking opened date...")
        try:
            trades = repository.get_trade_history(position.ticker)
            if trades:
                buy_trades = [t for t in trades if t.action.upper() == 'BUY']
                if buy_trades:
                    first_buy = min(buy_trades, key=lambda t: t.timestamp)
                    opened_date = first_buy.timestamp.strftime('%m-%d-%y')
                    print(f"   ✅ Found opened date: {opened_date}")
                else:
                    print(f"   ❌ No BUY trades found")
                    return
            else:
                print(f"   ❌ No trades found")
                return
        except Exception as e:
            print(f"   ❌ Error getting trades: {e}")
            return
        
        # Step 2: Parse date and calculate days held
        print(f"\n🗓️ Step 2: Calculating days held...")
        try:
            from datetime import datetime as _dt
            opened_dt = _dt.strptime(opened_date, '%m-%d-%y')
            if opened_dt.year < 2000:
                opened_dt = opened_dt.replace(year=opened_dt.year + 2000)
            
            tz = market_hours.get_trading_timezone()
            opened_dt = tz.localize(opened_dt)
            now_tz = _dt.now(tz)
            
            days_held_trading = market_hours.trading_days_between(opened_dt, now_tz)
            print(f"   📈 Trading days held: {days_held_trading}")
            
            if days_held_trading <= 5:
                print(f"   ⚠️  Position too new for 5-day P&L ({days_held_trading} <= 5 days)")
                print("   This is why 5-day P&L shows N/A")
                return
            else:
                print(f"   ✅ Position old enough for 5-day P&L")
        except Exception as e:
            print(f"   ❌ Date parsing error: {e}")
            return
        
        # Step 3: Check historical data availability
        print(f"\n📈 Step 3: Checking historical price data...")
        
        # First check price cache
        cached_data = price_cache.get_cached_price(position.ticker)
        if cached_data is not None and not cached_data.empty:
            print(f"   💾 Found cached data: {len(cached_data)} days")
            print(f"   📊 Columns: {list(cached_data.columns)}")
            print(f"   📅 Date range: {cached_data.index[0]} to {cached_data.index[-1]}")
            
            if 'Close' in cached_data.columns:
                closes_series = cached_data['Close']
                print(f"   💰 Close prices available: {len(closes_series)} days")
                
                if len(closes_series) >= 6:
                    start_price_5d = closes_series.iloc[-6]
                    current_price_from_data = closes_series.iloc[-1]
                    print(f"   📊 5 days ago price: ${start_price_5d:.2f}")
                    print(f"   📊 Current price from data: ${current_price_from_data:.2f}")
                    print(f"   📊 Position current price: ${position.current_price:.2f}")
                    
                    # Calculate 5-day P&L
                    period = pnl_calculator.calculate_period_pnl(
                        position.current_price,
                        Decimal(str(start_price_5d)),
                        position.shares,
                        period_name="five_day"
                    )
                    
                    abs_pnl = period.get('five_day_absolute_pnl')
                    pct_pnl = period.get('five_day_percentage_pnl')
                    
                    print(f"   💹 Absolute P&L: ${abs_pnl:.2f}")
                    print(f"   📈 Percentage P&L: {float(pct_pnl) * 100:.1f}%")
                    
                    # Format display
                    pct_value = float(pct_pnl) * 100
                    if abs_pnl >= 0:
                        display = f"${abs_pnl:.2f} +{pct_value:.1f}%"
                    else:
                        display = f"-${abs(abs_pnl):.2f} {pct_value:.1f}%"
                    
                    print(f"   ✅ 5-day P&L should display as: {display}")
                    
                else:
                    print(f"   ❌ Insufficient cached data ({len(closes_series)} < 6 days)")
            else:
                print(f"   ❌ No 'Close' column in cached data")
        else:
            print(f"   ❌ No cached price data found")
            
            # Try to fetch fresh data
            print(f"   🔄 Attempting to fetch fresh data...")
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=15)  # 15 calendar days back
                
                result = market_data_fetcher.fetch_price_data(position.ticker, start_date, end_date)
                print(f"   📊 Fetched {len(result.df)} days from {result.source}")
                
                if not result.df.empty and 'Close' in result.df.columns:
                    print(f"   📅 Date range: {result.df.index[0]} to {result.df.index[-1]}")
                    closes = result.df['Close']
                    if len(closes) >= 6:
                        print(f"   ✅ Sufficient data for 5-day P&L calculation")
                    else:
                        print(f"   ❌ Still insufficient data ({len(closes)} < 6 days)")
                else:
                    print(f"   ❌ No valid data fetched")
                    
            except Exception as e:
                print(f"   ❌ Error fetching data: {e}")
        
    except Exception as e:
        print(f"❌ Debug script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_5day_pnl()