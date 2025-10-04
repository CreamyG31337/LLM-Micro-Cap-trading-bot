#!/usr/bin/env python3
"""
Compare CSV portfolio data with Supabase portfolio data to verify rebuild worked correctly
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv('web_dashboard/.env')

from data.repositories.repository_factory import RepositoryFactory
from display.console_output import print_success, print_error, print_info, print_warning

def load_csv_portfolio(fund_name: str = "Project Chimera"):
    """Load portfolio data from CSV files"""
    try:
        # Find the CSV data directory for this fund
        csv_dir = None
        for fund_dir in Path("trading_data/funds").glob("*"):
            if fund_dir.is_dir() and fund_dir.name == fund_name:
                csv_dir = fund_dir
                break
        
        if not csv_dir:
            print_error(f"❌ CSV directory not found for fund: {fund_name}")
            return None
        
        portfolio_file = csv_dir / "llm_portfolio_update.csv"
        if not portfolio_file.exists():
            print_error(f"❌ Portfolio CSV not found: {portfolio_file}")
            return None
        
        # Load CSV data
        df = pd.read_csv(portfolio_file)
        print_success(f"✅ Loaded CSV portfolio: {len(df)} entries")
        return df
        
    except Exception as e:
        print_error(f"❌ Failed to load CSV portfolio: {e}")
        return None

def load_supabase_portfolio(fund_name: str = "Project Chimera"):
    """Load portfolio data from Supabase"""
    try:
        # Check Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print_error("❌ Missing Supabase credentials")
            return None
        
        # Create repository
        repository = RepositoryFactory.create_repository(
            'supabase',
            url=supabase_url,
            key=supabase_key,
            fund=fund_name
        )
        
        # Get portfolio data - this returns snapshots, we need individual positions
        snapshots = repository.get_portfolio_data()
        
        if not snapshots:
            print_error("❌ No portfolio data found in Supabase")
            return None
        
        # Extract individual positions from snapshots
        all_positions = []
        for snapshot in snapshots:
            if hasattr(snapshot, 'positions') and snapshot.positions:
                for position in snapshot.positions:
                    # Convert Position object to dict
                    pos_dict = {
                        'ticker': position.ticker,
                        'shares': float(position.shares),
                        'price': float(position.avg_price),  # Use avg_price instead of price
                        'cost_basis': float(position.cost_basis),
                        'pnl': float(getattr(position, 'pnl', 0) or 0),
                        'currency': position.currency,
                        'date': snapshot.timestamp
                    }
                    all_positions.append(pos_dict)
        
        if not all_positions:
            print_error("❌ No individual positions found in Supabase snapshots")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(all_positions)
        print_success(f"✅ Loaded Supabase portfolio: {len(df)} entries from {len(snapshots)} snapshots")
        return df
        
    except Exception as e:
        print_error(f"❌ Failed to load Supabase portfolio: {e}")
        return None

def compare_portfolios(csv_df, supabase_df, fund_name: str):
    """Compare CSV and Supabase portfolio data"""
    print_info(f"\n🔍 Comparing portfolios for fund: {fund_name}")
    print("=" * 60)
    
    # Basic counts
    print_info(f"📊 Entry counts:")
    print(f"   CSV: {len(csv_df)} entries")
    print(f"   Supabase: {len(supabase_df)} entries")
    
    if len(csv_df) != len(supabase_df):
        print_warning(f"⚠️ Entry count mismatch: CSV has {len(csv_df)}, Supabase has {len(supabase_df)}")
    
    # Check columns
    print_info(f"\n📋 Column comparison:")
    csv_cols = set(csv_df.columns)
    supabase_cols = set(supabase_df.columns)
    
    print(f"   CSV columns: {sorted(csv_cols)}")
    print(f"   Supabase columns: {sorted(supabase_cols)}")
    
    common_cols = csv_cols.intersection(supabase_cols)
    print(f"   Common columns: {sorted(common_cols)}")
    
    # Compare by ticker
    print_info(f"\n🎯 Ticker comparison:")
    
    # Get unique tickers from both
    csv_tickers = set(csv_df['Ticker'].unique()) if 'Ticker' in csv_df.columns else set()
    supabase_tickers = set(supabase_df['ticker'].unique()) if 'ticker' in supabase_df.columns else set()
    
    print(f"   CSV tickers: {sorted(csv_tickers)}")
    print(f"   Supabase tickers: {sorted(supabase_tickers)}")
    
    if csv_tickers == supabase_tickers:
        print_success("✅ Ticker sets match perfectly!")
    else:
        print_warning("⚠️ Ticker sets differ:")
        print(f"   Only in CSV: {sorted(csv_tickers - supabase_tickers)}")
        print(f"   Only in Supabase: {sorted(supabase_tickers - csv_tickers)}")
    
    # Compare shares for common tickers
    print_info(f"\n📈 Shares comparison:")
    for t in csv_tickers.intersection(supabase_tickers):
        csv_shares = csv_df[csv_df['Ticker'] == t]['Shares'].sum() if 'Shares' in csv_df.columns else 0
        supabase_shares = supabase_df[supabase_df['ticker'] == t]['shares'].sum() if 'shares' in supabase_df.columns else 0
        
        if abs(csv_shares - supabase_shares) < 0.001:  # Allow for small floating point differences
            print(f"   ✅ {t}: {csv_shares} shares (match)")
        else:
            print(f"   ❌ {t}: CSV={csv_shares}, Supabase={supabase_shares}")
    
    # Compare cost basis
    print_info(f"\n💰 Cost basis comparison:")
    for t in csv_tickers.intersection(supabase_tickers):
        csv_cost = csv_df[csv_df['Ticker'] == t]['Cost Basis'].sum() if 'Cost Basis' in csv_df.columns else 0
        supabase_cost = supabase_df[supabase_df['ticker'] == t]['cost_basis'].sum() if 'cost_basis' in supabase_df.columns else 0
        
        if abs(csv_cost - supabase_cost) < 0.01:  # Allow for small floating point differences
            print(f"   ✅ {t}: ${csv_cost:.2f} (match)")
        else:
            print(f"   ❌ {t}: CSV=${csv_cost:.2f}, Supabase=${supabase_cost:.2f}")
    
    # Compare average prices
    print_info(f"\n💵 Average price comparison:")
    for t in csv_tickers.intersection(supabase_tickers):
        csv_avg = csv_df[csv_df['Ticker'] == t]['Average Price'].mean() if 'Average Price' in csv_df.columns else 0
        supabase_avg = supabase_df[supabase_df['ticker'] == t]['price'].mean() if 'price' in supabase_df.columns else 0
        
        if abs(csv_avg - supabase_avg) < 0.01:  # Allow for small floating point differences
            print(f"   ✅ {t}: ${csv_avg:.2f} (match)")
        else:
            print(f"   ❌ {t}: CSV=${csv_avg:.2f}, Supabase=${supabase_avg:.2f}")
    
    # Date range comparison
    print_info(f"\n📅 Date range comparison:")
    if 'Date' in csv_df.columns:
        csv_dates = pd.to_datetime(csv_df['Date'])
        print(f"   CSV date range: {csv_dates.min()} to {csv_dates.max()}")
    
    if 'date' in supabase_df.columns:
        supabase_dates = pd.to_datetime(supabase_df['date'])
        print(f"   Supabase date range: {supabase_dates.min()} to {supabase_dates.max()}")
    
    print_success("\n✅ Portfolio comparison completed!")

def main():
    """Main comparison function"""
    fund_name = "Project Chimera"
    
    if len(sys.argv) > 1:
        fund_name = sys.argv[1]
    
    print_info(f"🔍 Comparing CSV vs Supabase portfolio for fund: {fund_name}")
    
    # Load both datasets
    csv_df = load_csv_portfolio(fund_name)
    supabase_df = load_supabase_portfolio(fund_name)
    
    if csv_df is None or supabase_df is None:
        print_error("❌ Failed to load one or both datasets")
        return False
    
    # Compare the datasets
    compare_portfolios(csv_df, supabase_df, fund_name)
    
    return True

if __name__ == "__main__":
    main()
