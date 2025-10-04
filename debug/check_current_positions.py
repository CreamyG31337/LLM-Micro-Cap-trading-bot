#!/usr/bin/env python3
"""
Check current_positions view in Supabase
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

def check_current_positions():
    # Load environment variables
    load_dotenv(Path('web_dashboard') / '.env')

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print('Missing Supabase credentials')
        return

    supabase = create_client(supabase_url, supabase_key)

    # Check if current_positions view exists
    try:
        result = supabase.table('current_positions').select('*').limit(1).execute()
        print('✅ current_positions view exists')

        if result.data:
            row = result.data[0]
            print(f'Columns: {list(row.keys())}')
            print('Sample data:')
            print(f'  Fund: {row.get("fund")}')
            print(f'  Ticker: {row.get("ticker")}')
            print(f'  Total PnL: {row.get("total_pnl")}')
            print(f'  Total Market Value: {row.get("total_market_value")}')
            print(f'  Total Cost Basis: {row.get("total_cost_basis")}')
        else:
            print('No data in current_positions view')

    except Exception as e:
        print(f'❌ current_positions view error: {e}')

if __name__ == "__main__":
    check_current_positions()
