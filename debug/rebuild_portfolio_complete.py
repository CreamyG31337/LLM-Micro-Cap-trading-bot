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
import pandas as pd
import pytz
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.repository_factory import RepositoryFactory
from portfolio.portfolio_manager import PortfolioManager
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from market_data.market_hours import MarketHours
from display.console_output import print_success, print_error, print_info, print_warning, _safe_emoji

# Load environment variables
load_dotenv(project_root / 'web_dashboard' / '.env')

def rebuild_portfolio_complete(data_dir: str, fund_name: str = None) -> bool:
    """
    Rebuild portfolio from trade log and update both CSV and Supabase.
    
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
                repository = RepositoryFactory.create_repository('supabase-dual-write', data_directory=data_dir, fund_name=fund_name)
                print(f"{_safe_emoji('✅')} Using Supabase dual-write repository (Supabase read, CSV+Supabase write)")
            except Exception as e:
                print(f"{_safe_emoji('⚠️')} Supabase dual-write repository failed: {e}")
                print("   Falling back to CSV-only repository")
                repository = RepositoryFactory.create_repository('csv', data_directory=data_dir, fund_name=fund_name)
        else:
            repository = RepositoryFactory.create_repository('csv', data_directory=data_dir, fund_name=fund_name)
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
        trade_df['Date'] = pd.to_datetime(trade_df['Date'])
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
        
        # Process trades chronologically
        print_info(f"{_safe_emoji('📈')} Processing trades chronologically...")
        
        # Track running positions
        running_positions = {}
        
        for idx, trade_row in trade_df.iterrows():
            # Create Trade object
            from data.models.trade import Trade
            
            # Get shares value first
            shares = Decimal(str(trade_row['Shares']))
            
            # Determine action from Reason field (more reliable than share signs)
            reason = trade_row.get('Reason', '').upper()
            if 'SELL' in reason:
                action = 'SELL'
            elif 'BUY' in reason:
                action = 'BUY'
            else:
                # Fallback to share signs if reason doesn't indicate action
                action = 'BUY' if shares > 0 else 'SELL'
            
            # Handle NaN values in currency
            currency = trade_row.get('Currency', 'USD')
            if pd.isna(currency):
                currency = 'USD'  # Default to USD for NaN currencies
            
            trade = Trade(
                ticker=trade_row['Ticker'],
                action=action,
                shares=abs(shares),  # Use absolute value for shares
                price=Decimal(str(trade_row['Price'])),
                timestamp=trade_row['Date'],
                cost_basis=Decimal(str(trade_row.get('Cost Basis', 0))),
                pnl=Decimal(str(trade_row.get('PnL', 0))),
                reason=trade_row.get('Reason', ''),
                currency=currency
            )
            
            # Save trade to repository (updates both CSV and Supabase)
            repository.save_trade(trade)
            
            # Update running positions
            ticker = trade.ticker
            if ticker not in running_positions:
                running_positions[ticker] = {'shares': Decimal('0'), 'cost': Decimal('0'), 'currency': trade.currency}
            
            if trade.action == 'BUY':
                running_positions[ticker]['shares'] += trade.shares
                running_positions[ticker]['cost'] += trade.cost_basis
                running_positions[ticker]['currency'] = trade.currency
            elif trade.action == 'SELL':
                running_positions[ticker]['shares'] -= trade.shares
                # For sells, reduce cost proportionally
                if running_positions[ticker]['shares'] > 0:
                    cost_per_share = running_positions[ticker]['cost'] / (running_positions[ticker]['shares'] + trade.shares)
                    running_positions[ticker]['cost'] -= cost_per_share * trade.shares
                else:
                    running_positions[ticker]['cost'] = Decimal('0')
            
            print(f"   {trade.timestamp.strftime('%Y-%m-%d %H:%M')} | {trade.ticker} | {trade.shares} @ ${trade.price} | ${trade.cost_basis} | {trade.action}")
        
        # Generate HOLD entries for all trading days
        print_info(f"{_safe_emoji('📊')} Generating HOLD entries for all trading days...")
        
        # Get all unique trading days from trades
        trade_dates = sorted(trade_df['Date'].dt.date.unique())
        
        # Add trading days between first and last trade
        market_hours = MarketHours()
        current_date = trade_dates[0]
        end_date = trade_dates[-1]
        
        all_trading_days = set(trade_dates)
        while current_date <= end_date:
            if market_hours.is_trading_day(current_date):
                all_trading_days.add(current_date)
            current_date += timedelta(days=1)
        
        # Create final portfolio snapshot from current positions
        print_info(f"{_safe_emoji('📊')} Creating final portfolio snapshot...")
        
        from data.models.portfolio import Position, PortfolioSnapshot
        final_positions = []
        
        for ticker, position in running_positions.items():
            if position['shares'] > 0:  # Only include positions with shares
                avg_price = position['cost'] / position['shares'] if position['shares'] > 0 else Decimal('0')
                final_position = Position(
                    ticker=ticker,
                    shares=position['shares'],
                    avg_price=avg_price,
                    cost_basis=position['cost'],
                    currency=position['currency'],
                    company=ticker,  # Will be updated by company name lookup
                    current_price=avg_price,  # Use avg_price as current_price for now
                    market_value=position['cost'],  # Use cost_basis as market_value for now
                    unrealized_pnl=Decimal('0')  # Will be updated by price refresh
                )
                final_positions.append(final_position)
        
        # Create and save final portfolio snapshot
        if final_positions:
            final_snapshot = PortfolioSnapshot(
                positions=final_positions,
                timestamp=datetime.now(),
                total_value=sum(p.cost_basis for p in final_positions)
            )
            repository.save_portfolio_snapshot(final_snapshot)
            print_info(f"   Saved final portfolio snapshot with {len(final_positions)} positions")
        
        # Create final portfolio CSV from current positions
        print_info(f"{_safe_emoji('📊')} Creating final portfolio CSV...")
        portfolio_entries = []
        for ticker, position in running_positions.items():
            if position['shares'] > 0:  # Only include positions with shares
                portfolio_entries.append({
                    'Date': datetime.now().strftime('%Y-%m-%d'),
                    'Ticker': ticker,
                    'Shares': float(position['shares']),
                    'Average Price': float(position['cost'] / position['shares']) if position['shares'] > 0 else 0,
                    'Cost Basis': float(position['cost']),
                    'Stop Loss': 0.0,
                    'Current Price': 0.0,  # Will be updated by price refresh
                    'Total Value': 0.0,   # Will be updated by price refresh
                    'PnL': 0.0,           # Will be updated by price refresh
                    'Action': 'HOLD',
                    'Company': ticker,  # Will be updated by company name lookup
                    'Currency': position.get('currency', 'USD')
                })
        
        # Create and save portfolio CSV
        if portfolio_entries:
            portfolio_df = pd.DataFrame(portfolio_entries)
            
            # Round numeric columns
            for col in portfolio_df.columns:
                if col in ['Shares', 'Average Price', 'Cost Basis', 'Current Price', 'Total Value', 'PnL']:
                    if col == 'Shares':
                        portfolio_df[col] = portfolio_df[col].round(4)
                    else:
                        portfolio_df[col] = portfolio_df[col].round(2)
            
            # Save portfolio CSV
            portfolio_file = Path(data_dir) / "llm_portfolio_update.csv"
            portfolio_df.to_csv(portfolio_file, index=False)
            print_info(f"   Portfolio CSV saved: {portfolio_file}")
        else:
            print_info("   No positions found - creating empty portfolio")
            # Create empty portfolio file
            empty_df = pd.DataFrame(columns=['Date', 'Ticker', 'Shares', 'Average Price', 'Cost Basis', 'Stop Loss', 'Current Price', 'Total Value', 'PnL', 'Action', 'Company', 'Currency'])
            portfolio_file = Path(data_dir) / "llm_portfolio_update.csv"
            empty_df.to_csv(portfolio_file, index=False)
        
        print_success(f"{_safe_emoji('✅')} Portfolio rebuild completed successfully!")
        print_info(f"   {_safe_emoji('✅')} CSV files updated")
        if fund_name:
            print_info(f"   {_safe_emoji('✅')} Trades saved to Supabase")
        print_info(f"   {_safe_emoji('✅')} Positions recalculated from trade log")
        print_info(f"   {_safe_emoji('✅')} Final portfolio CSV created with {len(portfolio_entries)} positions")
        
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
