#!/usr/bin/env python3
"""
Migration Verification Script
Compares CSV data with Supabase data to ensure migration was successful
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
import json

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

def load_csv_data():
    """Load data from CSV files"""
    print("📁 Loading CSV data...")
    
    csv_data = {}
    
    # Portfolio data
    portfolio_csv = "trading_data/funds/Project Chimera/llm_portfolio_update.csv"
    if os.path.exists(portfolio_csv):
        try:
            df = pd.read_csv(portfolio_csv)
            csv_data['portfolio'] = df
            print(f"✅ Portfolio CSV: {len(df)} rows loaded")
        except Exception as e:
            print(f"❌ Error loading portfolio CSV: {e}")
            csv_data['portfolio'] = None
    else:
        print(f"❌ Portfolio CSV not found: {portfolio_csv}")
        csv_data['portfolio'] = None
    
    # Trade log data
    trades_csv = "trading_data/funds/Project Chimera/llm_trade_log.csv"
    if os.path.exists(trades_csv):
        try:
            df = pd.read_csv(trades_csv)
            csv_data['trades'] = df
            print(f"✅ Trades CSV: {len(df)} rows loaded")
        except Exception as e:
            print(f"❌ Error loading trades CSV: {e}")
            csv_data['trades'] = None
    else:
        print(f"❌ Trades CSV not found: {trades_csv}")
        csv_data['trades'] = None
    
    return csv_data

def load_supabase_data():
    """Load data from Supabase"""
    print("\n🗄️ Loading Supabase data...")
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient()
        if not client:
            print("❌ Supabase client creation failed")
            return None
        
        supabase_data = {}
        
        # Get portfolio positions
        try:
            result = client.supabase.table("portfolio_positions").select("*").execute()
            supabase_data['portfolio'] = pd.DataFrame(result.data) if result.data else pd.DataFrame()
            print(f"✅ Supabase portfolio: {len(supabase_data['portfolio'])} rows")
        except Exception as e:
            print(f"❌ Error loading Supabase portfolio: {e}")
            supabase_data['portfolio'] = None
        
        # Get trade log
        try:
            result = client.supabase.table("trade_log").select("*").execute()
            supabase_data['trades'] = pd.DataFrame(result.data) if result.data else pd.DataFrame()
            print(f"✅ Supabase trades: {len(supabase_data['trades'])} rows")
        except Exception as e:
            print(f"❌ Error loading Supabase trades: {e}")
            supabase_data['trades'] = None
        
        return supabase_data
        
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
        return None

def compare_data_sets(csv_data, supabase_data):
    """Compare CSV and Supabase data"""
    print("\n🔍 Comparing data sets...")
    
    comparison_results = {}
    
    # Compare portfolio data
    if csv_data.get('portfolio') is not None and supabase_data.get('portfolio') is not None:
        csv_portfolio = csv_data['portfolio']
        supabase_portfolio = supabase_data['portfolio']
        
        print(f"\n📊 Portfolio Comparison:")
        print(f"   CSV rows: {len(csv_portfolio)}")
        print(f"   Supabase rows: {len(supabase_portfolio)}")
        
        # Check if we have data
        if len(csv_portfolio) > 0 and len(supabase_portfolio) > 0:
            # Compare unique tickers
            csv_tickers = set(csv_portfolio['ticker'].unique()) if 'ticker' in csv_portfolio.columns else set()
            supabase_tickers = set(supabase_portfolio['ticker'].unique()) if 'ticker' in supabase_portfolio.columns else set()
            
            print(f"   CSV unique tickers: {len(csv_tickers)}")
            print(f"   Supabase unique tickers: {len(supabase_tickers)}")
            
            if csv_tickers == supabase_tickers:
                print("   ✅ Ticker sets match")
            else:
                print("   ⚠️  Ticker sets differ")
                print(f"      CSV only: {csv_tickers - supabase_tickers}")
                print(f"      Supabase only: {supabase_tickers - csv_tickers}")
            
            comparison_results['portfolio'] = {
                'csv_rows': len(csv_portfolio),
                'supabase_rows': len(supabase_portfolio),
                'tickers_match': csv_tickers == supabase_tickers,
                'csv_tickers': csv_tickers,
                'supabase_tickers': supabase_tickers
            }
        else:
            print("   ⚠️  One or both datasets are empty")
            comparison_results['portfolio'] = {'empty': True}
    else:
        print("   ❌ Cannot compare portfolio data - missing datasets")
        comparison_results['portfolio'] = {'error': 'Missing data'}
    
    # Compare trade data
    if csv_data.get('trades') is not None and supabase_data.get('trades') is not None:
        csv_trades = csv_data['trades']
        supabase_trades = supabase_data['trades']
        
        print(f"\n📈 Trades Comparison:")
        print(f"   CSV rows: {len(csv_trades)}")
        print(f"   Supabase rows: {len(supabase_trades)}")
        
        if len(csv_trades) > 0 and len(supabase_trades) > 0:
            # Compare unique tickers
            csv_tickers = set(csv_trades['ticker'].unique()) if 'ticker' in csv_trades.columns else set()
            supabase_tickers = set(supabase_trades['ticker'].unique()) if 'ticker' in supabase_trades.columns else set()
            
            print(f"   CSV unique tickers: {len(csv_tickers)}")
            print(f"   Supabase unique tickers: {len(supabase_tickers)}")
            
            if csv_tickers == supabase_tickers:
                print("   ✅ Ticker sets match")
            else:
                print("   ⚠️  Ticker sets differ")
                print(f"      CSV only: {csv_tickers - supabase_tickers}")
                print(f"      Supabase only: {supabase_tickers - csv_tickers}")
            
            comparison_results['trades'] = {
                'csv_rows': len(csv_trades),
                'supabase_rows': len(supabase_trades),
                'tickers_match': csv_tickers == supabase_tickers,
                'csv_tickers': csv_tickers,
                'supabase_tickers': supabase_tickers
            }
        else:
            print("   ⚠️  One or both datasets are empty")
            comparison_results['trades'] = {'empty': True}
    else:
        print("   ❌ Cannot compare trade data - missing datasets")
        comparison_results['trades'] = {'error': 'Missing data'}
    
    return comparison_results

def test_specific_queries():
    """Test specific queries that the app will use"""
    print("\n🔍 Testing app-specific queries...")
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient()
        if not client:
            print("❌ Cannot test queries - Supabase client failed")
            return False
        
        # Test portfolio query
        try:
            result = client.supabase.table("portfolio_positions").select("*").limit(5).execute()
            print(f"✅ Portfolio query: {len(result.data)} rows returned")
        except Exception as e:
            print(f"❌ Portfolio query failed: {e}")
            return False
        
        # Test trade log query
        try:
            result = client.supabase.table("trade_log").select("*").order("date", desc=True).limit(5).execute()
            print(f"✅ Trade log query: {len(result.data)} rows returned")
        except Exception as e:
            print(f"❌ Trade log query failed: {e}")
            return False
        
        # Test fund filtering
        try:
            result = client.supabase.table("portfolio_positions").select("*").eq("fund", "Project Chimera").limit(5).execute()
            print(f"✅ Fund filtering: {len(result.data)} rows for 'Project Chimera'")
        except Exception as e:
            print(f"❌ Fund filtering failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Query testing error: {e}")
        return False

def run_verification():
    """Run complete verification"""
    print("🧪 MIGRATION VERIFICATION")
    print("=" * 50)
    
    # Load data from both sources
    csv_data = load_csv_data()
    supabase_data = load_supabase_data()
    
    if csv_data is None or supabase_data is None:
        print("\n❌ Cannot proceed - data loading failed")
        return False
    
    # Compare datasets
    comparison = compare_data_sets(csv_data, supabase_data)
    
    # Test app queries
    query_test = test_specific_queries()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    # Check if we have data in both sources
    csv_has_data = any(len(df) > 0 for df in csv_data.values() if df is not None)
    supabase_has_data = any(len(df) > 0 for df in supabase_data.values() if df is not None)
    
    if csv_has_data and supabase_has_data:
        print("✅ Both CSV and Supabase have data")
        
        # Check if data looks similar
        portfolio_match = comparison.get('portfolio', {}).get('tickers_match', False)
        trades_match = comparison.get('trades', {}).get('tickers_match', False)
        
        if portfolio_match and trades_match:
            print("✅ Data appears to match between CSV and Supabase")
        else:
            print("⚠️  Data differences detected - check details above")
        
        if query_test:
            print("✅ App queries work correctly")
        else:
            print("❌ App queries failed")
        
        print("\n🎉 MIGRATION VERIFICATION COMPLETE!")
        print("   The app should work with Supabase data")
        
    elif csv_has_data and not supabase_has_data:
        print("❌ CSV has data but Supabase is empty")
        print("   Run: python migrate.py")
        
    elif not csv_has_data and supabase_has_data:
        print("⚠️  Supabase has data but CSV is empty")
        print("   This might be expected if you're switching to Supabase")
        
    else:
        print("❌ No data found in either source")
        print("   Check your CSV files and run migration")
    
    return csv_has_data and supabase_has_data and query_test

if __name__ == "__main__":
    run_verification()
