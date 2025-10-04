#!/usr/bin/env python3
"""
Check what happened to October 1st data
"""

import pandas as pd
from pathlib import Path

def check_oct1_data():
    # Load CSV data
    csv_file = Path('trading_data/funds/Project Chimera/llm_portfolio_update.csv')
    df = pd.read_csv(csv_file)
    
    # Check for October 1st data
    oct_1_data = df[df['Date'].str.contains('2025-10-01')]
    print(f'October 1st entries in CSV: {len(oct_1_data)}')
    
    if len(oct_1_data) > 0:
        print('October 1st data exists in CSV!')
        print(f'Sample: {oct_1_data.iloc[0]["Date"]} - {oct_1_data.iloc[0]["Ticker"]}')
    else:
        print('No October 1st data in CSV either!')
        
    # Check what the last few dates are
    print('\nLast 10 dates in CSV:')
    last_dates = df['Date'].tail(10).tolist()
    for i, date in enumerate(last_dates):
        print(f'{i+1}: {date}')
    
    # Check if there's a gap between Sept 30 and Oct 2
    sept_30_data = df[df['Date'].str.contains('2025-09-30')]
    oct_2_data = df[df['Date'].str.contains('2025-10-02')]
    
    print(f'\nSept 30 entries: {len(sept_30_data)}')
    print(f'Oct 2 entries: {len(oct_2_data)}')
    
    if len(sept_30_data) > 0 and len(oct_2_data) > 0:
        print('There is indeed a gap - no data for Oct 1st!')

if __name__ == "__main__":
    check_oct1_data()
