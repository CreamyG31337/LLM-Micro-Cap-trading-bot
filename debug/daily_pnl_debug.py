#!/usr/bin/env python3
"""
Daily P&L Debug Script for LLM Micro-Cap Trading Bot

This script helps debug why daily P&L is showing as N/A by:
1. Testing the price data fetching for specific tickers
2. Checking the data structure returned by download_price_data
3. Verifying the daily P&L calculation logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_script import download_price_data, trading_day_window, last_trading_date
import pandas as pd
from datetime import datetime

def debug_daily_pnl_calculation(ticker):
    """
    Debug the daily P&L calculation for a specific ticker
    """
    print(f"🔍 Debugging daily P&L calculation for {ticker}")
    print("=" * 60)
    
    # Get the trading day window
    s, e = trading_day_window()
    print(f"📅 Trading day window: {s} to {e}")
    print(f"📅 Last trading date: {last_trading_date()}")
    print()
    
    # Fetch price data
    print(f"📈 Fetching price data for {ticker}...")
    fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
    
    print(f"📊 Data source: {fetch.source}")
    print(f"📊 DataFrame shape: {fetch.df.shape}")
    print(f"📊 DataFrame columns: {list(fetch.df.columns)}")
    print()
    
    if fetch.df.empty:
        print("❌ No data returned from download_price_data")
        return
    
    print("📈 Price data:")
    print("-" * 40)
    print(fetch.df)
    print()
    
    # Check if we have enough data for daily P&L calculation
    if "Close" in fetch.df.columns:
        print(f"✅ Close column found")
        print(f"📊 Number of rows: {len(fetch.df)}")
        
        if len(fetch.df) > 1:
            current_price = float(fetch.df['Close'].iloc[-1].item())
            prev_price = float(fetch.df['Close'].iloc[-2].item())
            daily_pnl_pct = ((current_price - prev_price) / prev_price) * 100
            
            print(f"💰 Current price: ${current_price:.2f}")
            print(f"💰 Previous price: ${prev_price:.2f}")
            print(f"📈 Daily P&L: {daily_pnl_pct:+.1f}%")
        else:
            print("❌ Not enough data for daily P&L calculation (need at least 2 rows)")
            print("   This is why daily P&L shows as N/A")
    else:
        print("❌ Close column not found in data")
    
    print()
    print("🔍 Analysis:")
    print("-" * 40)
    
    if len(fetch.df) <= 1:
        print("❌ ISSUE FOUND: Not enough historical data")
        print("   The trading_day_window() function might be returning too narrow a range")
        print("   This causes download_price_data to return only 1 day of data")
        print("   Daily P&L calculation requires at least 2 days of data")
    else:
        print("✅ Sufficient data available for daily P&L calculation")

def debug_trading_day_window():
    """
    Debug the trading day window function
    """
    print("🔍 Debugging trading_day_window function")
    print("=" * 60)
    
    s, e = trading_day_window()
    print(f"📅 Start: {s}")
    print(f"📅 End: {e}")
    print(f"📅 Duration: {e - s}")
    print()
    
    # Check if this is too narrow a window
    if (e - s).days < 2:
        print("⚠️  WARNING: Trading day window is too narrow!")
        print("   This might be causing insufficient data for daily P&L calculation")
        print("   Consider expanding the window to include more historical data")

def test_with_expanded_window(ticker):
    """
    Test with an expanded date window to see if we get more data
    """
    print(f"🔍 Testing {ticker} with expanded date window")
    print("=" * 60)
    
    from datetime import timedelta
    
    # Get a wider date range
    end_date = last_trading_date()
    start_date = end_date - timedelta(days=5)  # Go back 5 days
    
    print(f"📅 Expanded window: {start_date} to {end_date}")
    
    fetch = download_price_data(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
    
    print(f"📊 Data source: {fetch.source}")
    print(f"📊 DataFrame shape: {fetch.df.shape}")
    print()
    
    if not fetch.df.empty and "Close" in fetch.df.columns and len(fetch.df) > 1:
        current_price = float(fetch.df['Close'].iloc[-1].item())
        prev_price = float(fetch.df['Close'].iloc[-2].item())
        daily_pnl_pct = ((current_price - prev_price) / prev_price) * 100
        
        print(f"💰 Current price: ${current_price:.2f}")
        print(f"💰 Previous price: ${prev_price:.2f}")
        print(f"📈 Daily P&L: {daily_pnl_pct:+.1f}%")
        print()
        print("✅ SUCCESS: With expanded window, daily P&L calculation works!")
    else:
        print("❌ Still not enough data even with expanded window")

def main():
    """
    Main debug function
    """
    print("🐛 Daily P&L Debug Tool")
    print("=" * 60)
    print()
    
    # Test with the tickers from the portfolio
    tickers = ["TSLA", "VEE.TO"]
    
    for ticker in tickers:
        debug_daily_pnl_calculation(ticker)
        print()
    
    print("🔍 Debugging trading day window...")
    debug_trading_day_window()
    print()
    
    # Test with expanded window
    for ticker in tickers:
        test_with_expanded_window(ticker)
        print()
    
    print("💡 Recommendations:")
    print("-" * 40)
    print("1. The trading_day_window() function returns too narrow a range")
    print("2. This causes download_price_data to return only 1 day of data")
    print("3. Daily P&L calculation needs at least 2 days of data")
    print("4. Consider modifying trading_day_window to include more historical data")
    print("5. Or modify the daily P&L calculation to use a wider date range")

if __name__ == "__main__":
    main()
