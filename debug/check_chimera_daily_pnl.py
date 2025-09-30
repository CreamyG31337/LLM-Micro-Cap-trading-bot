#!/usr/bin/env python3
"""Check daily P&L calculation for Project Chimera positions."""

import sys
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    csv_path = Path("trading_data/funds/Project Chimera/llm_portfolio_update.csv")
    
    # Load CSV directly
    df = pd.read_csv(csv_path)
    print(f"📊 Total rows in CSV: {len(df)}")
    print(f"📊 Columns: {list(df.columns)}")
    
    # Parse dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # Show date range
    print(f"\n📊 Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    # Group by date
    dates = df['Date'].dt.date.unique()
    print(f"📊 Unique dates: {len(dates)}")
    print(f"📊 Dates: {sorted(dates)}")
    
    # Check the last few days
    print(f"\n🔍 Last 3 dates in CSV:")
    last_dates = sorted(df['Date'].dt.date.unique())[-3:]
    for date in last_dates:
        day_data = df[df['Date'].dt.date == date]
        print(f"\n   {date}: {len(day_data)} positions")
        
        # Show first position for this date
        if not day_data.empty:
            first_row = day_data.iloc[0]
            print(f"      Example: {first_row['Ticker']} - ${first_row['Current Price']}")
    
    # Check if Friday->Monday exists
    print(f"\n🔍 Looking for weekend gap (Friday->Monday):")
    sorted_dates = sorted(df['Date'].dt.date.unique())
    for i in range(1, len(sorted_dates)):
        prev_date = sorted_dates[i-1]
        curr_date = sorted_dates[i]
        gap_days = (curr_date - prev_date).days
        
        if gap_days > 1:
            print(f"   Gap found: {prev_date} ({prev_date.strftime('%A')}) -> {curr_date} ({curr_date.strftime('%A')}) = {gap_days} days")
            
            # Show a ticker's price change over the gap
            test_ticker = 'CTRN'  # Pick a ticker
            prev_data = df[(df['Date'].dt.date == prev_date) & (df['Ticker'] == test_ticker)]
            curr_data = df[(df['Date'].dt.date == curr_date) & (df['Ticker'] == test_ticker)]
            
            if not prev_data.empty and not curr_data.empty:
                prev_price = prev_data.iloc[0]['Current Price']
                curr_price = curr_data.iloc[0]['Current Price']
                price_change = curr_price - prev_price
                print(f"      {test_ticker}: ${prev_price} -> ${curr_price} = ${price_change:.2f}")

if __name__ == "__main__":
    main()