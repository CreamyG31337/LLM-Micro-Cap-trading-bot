#!/usr/bin/env python3
"""
Check data for specific dates to understand why graph shows same values
"""

import pandas as pd
from pathlib import Path

def check_date_data():
    # Load the CSV data
    csv_file = Path('trading_data/funds/Project Chimera/llm_portfolio_update.csv')
    df = pd.read_csv(csv_file)
    
    print("=== Checking Date Data ===")
    print(f"Total entries: {len(df)}")
    
    # Filter for the specific dates
    sept_30 = df[df['Date'].str.contains('2025-09-30')]
    oct_1 = df[df['Date'].str.contains('2025-10-01')]
    
    print('\n=== Sept 30 Data ===')
    print(f'Entries: {len(sept_30)}')
    if len(sept_30) > 0:
        print(f'Date range: {sept_30["Date"].min()} to {sept_30["Date"].max()}')
        print(f'Sample dates: {sept_30["Date"].head(3).tolist()}')
        # Check if there are any unique dates
        unique_dates = sept_30['Date'].unique()
        print(f'Unique dates: {len(unique_dates)}')
        print(f'Unique date values: {unique_dates[:5]}')
    
    print('\n=== Oct 1 Data ===')
    print(f'Entries: {len(oct_1)}')
    if len(oct_1) > 0:
        print(f'Date range: {oct_1["Date"].min()} to {oct_1["Date"].max()}')
        print(f'Sample dates: {oct_1["Date"].head(3).tolist()}')
        # Check if there are any unique dates
        unique_dates = oct_1['Date'].unique()
        print(f'Unique dates: {len(unique_dates)}')
        print(f'Unique date values: {unique_dates[:5]}')
    else:
        print('No data found for Oct 1!')
    
    # Check what the last few dates are
    print('\n=== Last 10 Dates in Dataset ===')
    last_dates = df['Date'].tail(10).tolist()
    for i, date in enumerate(last_dates):
        print(f'{i+1}: {date}')
    
    # Check if there's any data after Sept 30
    print('\n=== Data After Sept 30 ===')
    after_sept_30 = df[df['Date'] > '2025-09-30']
    print(f'Entries after Sept 30: {len(after_sept_30)}')
    if len(after_sept_30) > 0:
        print(f'Date range: {after_sept_30["Date"].min()} to {after_sept_30["Date"].max()}')

if __name__ == "__main__":
    check_date_data()
