#!/usr/bin/env python3
"""
Debug script to test P&L calculation issues for US vs Canadian stocks.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from decimal import Decimal
from financial.pnl_calculator import calculate_daily_pnl_from_snapshots

def test_pnl_calculation():
    """Test P&L calculation for different tickers."""
    print("🔍 Testing P&L Calculation Issues")
    print("=" * 50)
    
    # Load portfolio data
    try:
        df = pd.read_csv('trading_data/funds/TEST/llm_portfolio_update.csv')
        print(f"✅ Loaded portfolio data: {len(df)} entries")
        
        # Get unique tickers
        tickers = df['Ticker'].unique()
        print(f"📊 Found {len(tickers)} unique tickers")
        
        # Test a few specific tickers (with .TO suffix for Canadian ones)
        test_tickers = ['VFV.TO', 'XIC.TO', 'DOL.TO', 'NXTG', 'KEY']
        
        for ticker in test_tickers:
            if ticker in tickers:
                print(f"\n🔍 Testing {ticker}:")
                
                # Get latest entry for this ticker
                ticker_data = df[df['Ticker'] == ticker].iloc[-1]
                
                print(f"  Company: {ticker_data['Company']}")
                print(f"  Currency: {ticker_data['Currency']}")
                print(f"  Current Price: ${ticker_data['Current Price']}")
                print(f"  Shares: {ticker_data['Shares']}")
                print(f"  Avg Price: ${ticker_data['Average Price']}")
                
                # Check if this is a Canadian ticker
                is_canadian = ticker.endswith('.TO') or ticker.endswith('.V') or ticker.endswith('.CN')
                print(f"  Is Canadian: {is_canadian}")
                
                # Check for any obvious data issues
                current_price = Decimal(str(ticker_data['Current Price']))
                avg_price = Decimal(str(ticker_data['Average Price']))
                shares = Decimal(str(ticker_data['Shares']))
                
                if current_price <= 0:
                    print(f"  ⚠️  WARNING: Invalid current price: {current_price}")
                if avg_price <= 0:
                    print(f"  ⚠️  WARNING: Invalid avg price: {avg_price}")
                if shares <= 0:
                    print(f"  ⚠️  WARNING: Invalid shares: {shares}")
                
                # Calculate basic P&L
                total_cost = avg_price * shares
                current_value = current_price * shares
                basic_pnl = current_value - total_cost
                basic_pnl_pct = (basic_pnl / total_cost * 100) if total_cost > 0 else 0
                
                print(f"  Basic P&L: ${basic_pnl:.2f} ({basic_pnl_pct:.1f}%)")
                
                # Check for impossible values
                if abs(basic_pnl) > total_cost * 2:  # More than 200% gain/loss
                    print(f"  🚨 IMPOSSIBLE P&L: {basic_pnl:.2f} is more than 200% of cost basis!")
                
            else:
                print(f"❌ Ticker {ticker} not found in portfolio")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pnl_calculation()
