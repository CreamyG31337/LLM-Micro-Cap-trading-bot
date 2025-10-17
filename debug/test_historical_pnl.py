#!/usr/bin/env python3
"""Test historical P&L calculations (7-day and 30-day)."""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
# Use environment variable instead of hardcoded key
    # # Use environment variable instead of hardcoded key
    # os.environ["SUPABASE_ANON_KEY"] = "your-key-here"  # REMOVED FOR SECURITY  # REMOVED FOR SECURITY

from supabase import create_client

def test_historical_pnl():
    """Test historical P&L calculations."""
    print("🧪 Testing Historical P&L Calculations")
    print("=" * 50)
    
    # Initialize Supabase
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    
    # Get current portfolio value
    print("\n📊 Getting current portfolio value...")
    current_result = supabase.table('portfolio_positions').select('*').eq('fund', 'TEST').gte('date', '2025-10-04T00:00:00Z').execute()
    
    if not current_result.data:
        print("❌ No current data found")
        return False
    
    current_data = current_result.data
    current_value = sum(float(pos['shares']) * float(pos['price']) for pos in current_data)
    print(f"   Current portfolio value: ${current_value:,.2f}")
    
    # Get 7 days ago portfolio value
    print("\n📊 Getting 7-day ago portfolio value...")
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    print(f"   Looking for data around: {seven_days_ago}")
    
    # Find the closest date to 7 days ago
    all_dates_result = supabase.table('portfolio_positions').select('date').eq('fund', 'TEST').order('date', desc=True).execute()
    all_dates = [pos['date'][:10] for pos in all_dates_result.data]
    unique_dates = sorted(list(set(all_dates)), reverse=True)
    
    print(f"   Available dates: {unique_dates[:5]}...")
    
    # Find 7-day ago data
    seven_day_data = None
    for date in unique_dates:
        if date <= seven_days_ago:
            seven_day_result = supabase.table('portfolio_positions').select('*').eq('fund', 'TEST').gte('date', f'{date}T00:00:00Z').lt('date', f'{date}T23:59:59Z').execute()
            if seven_day_result.data:
                seven_day_data = seven_day_result.data
                print(f"   Found 7-day ago data: {date} ({len(seven_day_data)} positions)")
                break
    
    if seven_day_data:
        seven_day_value = sum(float(pos['shares']) * float(pos['price']) for pos in seven_day_data)
        seven_day_pnl = current_value - seven_day_value
        seven_day_pct = (seven_day_pnl / seven_day_value * 100) if seven_day_value > 0 else 0
        
        print(f"\n📈 7-Day P&L Calculation:")
        print(f"   Current value: ${current_value:,.2f}")
        print(f"   7-day ago value: ${seven_day_value:,.2f}")
        print(f"   7-day P&L: ${seven_day_pnl:,.2f}")
        print(f"   7-day return: {seven_day_pct:.2f}%")
    else:
        print("   ❌ No 7-day ago data found")
        seven_day_pnl = 0
        seven_day_pct = 0
    
    # Get 30 days ago portfolio value (if available)
    print("\n📊 Getting 30-day ago portfolio value...")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"   Looking for data around: {thirty_days_ago}")
    
    thirty_day_data = None
    for date in unique_dates:
        if date <= thirty_days_ago:
            thirty_day_result = supabase.table('portfolio_positions').select('*').eq('fund', 'TEST').gte('date', f'{date}T00:00:00Z').lt('date', f'{date}T23:59:59Z').execute()
            if thirty_day_result.data:
                thirty_day_data = thirty_day_result.data
                print(f"   Found 30-day ago data: {date} ({len(thirty_day_data)} positions)")
                break
    
    if thirty_day_data:
        thirty_day_value = sum(float(pos['shares']) * float(pos['price']) for pos in thirty_day_data)
        thirty_day_pnl = current_value - thirty_day_value
        thirty_day_pct = (thirty_day_pnl / thirty_day_value * 100) if thirty_day_value > 0 else 0
        
        print(f"\n📈 30-Day P&L Calculation:")
        print(f"   Current value: ${current_value:,.2f}")
        print(f"   30-day ago value: ${thirty_day_value:,.2f}")
        print(f"   30-day P&L: ${thirty_day_pnl:,.2f}")
        print(f"   30-day return: {thirty_day_pct:.2f}%")
    else:
        print("   ❌ No 30-day ago data found (insufficient historical data)")
        thirty_day_pnl = 0
        thirty_day_pct = 0
    
    # Summary
    print(f"\n" + "=" * 50)
    print(f"📋 HISTORICAL P&L SUMMARY")
    print(f"=" * 50)
    print(f"Current Portfolio Value: ${current_value:,.2f}")
    print(f"7-Day P&L: ${seven_day_pnl:,.2f} ({seven_day_pct:.2f}%)")
    print(f"30-Day P&L: ${thirty_day_pnl:,.2f} ({thirty_day_pct:.2f}%)")
    
    if seven_day_pnl != 0:
        print(f"\n✅ 7-day P&L calculation successful!")
    else:
        print(f"\n⚠️  7-day P&L calculation failed - insufficient data")
    
    if thirty_day_pnl != 0:
        print(f"✅ 30-day P&L calculation successful!")
    else:
        print(f"⚠️  30-day P&L calculation failed - insufficient data")
    
    return True

if __name__ == "__main__":
    test_historical_pnl()
