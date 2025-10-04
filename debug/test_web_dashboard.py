#!/usr/bin/env python3
"""
Test web dashboard functions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_web_dashboard():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Test the web dashboard load_portfolio_data function
    sys.path.append(str(project_root / 'web_dashboard'))

    from app import load_portfolio_data

    # Test loading Project Chimera data
    print('=== Testing Web Dashboard load_portfolio_data ===')
    try:
        data = load_portfolio_data('Project Chimera')
        print(f'Portfolio shape: {data["portfolio"].shape}')
        print(f'Trades shape: {data["trades"].shape}')
        print(f'Current fund: {data["current_fund"]}')

        if not data['portfolio'].empty:
            # Check if we have the expected columns
            print(f'Portfolio columns: {list(data["portfolio"].columns)}')

            # Try to calculate performance
            if 'total_pnl' in data['portfolio'].columns:
                total_pnl = data['portfolio']['total_pnl'].sum()
                print(f'Total PnL from portfolio: ${total_pnl:.2f}')
            else:
                print('No total_pnl column found')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_dashboard()
