#!/usr/bin/env python3
"""
Check P&L values in Supabase data
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

def check_supabase_pnl():
    # Load environment variables
    load_dotenv(Path('web_dashboard') / '.env')

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print('Missing Supabase credentials')
        return

    supabase = create_client(supabase_url, supabase_key)

    # Check recent portfolio data
    result = supabase.table('portfolio_positions').select('*').order('date', desc=True).limit(10).execute()

    print('=== Latest Supabase Portfolio Data ===')
    for row in result.data:
        print(f'Date: {row["date"]}')
        print(f'Ticker: {row["ticker"]}')
        print(f'Shares: {row["shares"]}')
        print(f'Price: ${row["price"]}')
        print(f'Cost Basis: ${row["cost_basis"]}')
        print(f'PnL: ${row["pnl"]}')
        if 'total_value' in row:
            print(f'Total Value: ${row["total_value"]}')
        print('---')

if __name__ == "__main__":
    check_supabase_pnl()
