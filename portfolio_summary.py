#!/usr/bin/env python3
"""
Portfolio Summary Display
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

def display_portfolio_summary():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    try:
        # Import repository functionality
        from data.repositories.repository_factory import RepositoryFactory

        # Load environment variables
        load_dotenv(project_root / 'web_dashboard' / '.env')

        # Get active fund name
        try:
            from utils.fund_manager import get_fund_manager
            fm = get_fund_manager()
            active_fund = fm.get_active_fund()
            if not active_fund:
                print('Warning: No active fund set. Using Project Chimera as default.')
                active_fund = 'Project Chimera'
        except ImportError:
            print('Warning: Fund management not available. Using Project Chimera as default.')
            active_fund = 'Project Chimera'

        print(f'Loading portfolio summary for fund: {active_fund}')
        
        # Create repository for active fund
        repository = RepositoryFactory.create_repository(
            'supabase',
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            fund=active_fund
        )

        # Get current positions
        positions = repository.get_current_positions()

        print('=== Portfolio Summary ===')
        print(f'Total positions: {len(positions)}')

        if positions:
            total_value = sum(float(pos.get('total_market_value', 0)) for pos in positions)
            total_cost = sum(float(pos.get('total_cost_basis', 0)) for pos in positions)
            total_pnl = sum(float(pos.get('total_pnl', 0)) for pos in positions)

            print(f'Total Portfolio Value: ${total_value:.2f}')
            print(f'Total Cost Basis: ${total_cost:.2f}')
            print(f'Total P&L: ${total_pnl:.2f}')

            if total_cost > 0:
                pnl_pct = (total_pnl / total_cost * 100)
                print(f'P&L Percentage: {pnl_pct:.2f}%')

            print('\n=== Individual Positions ===')
            for pos in positions[:5]:  # Show first 5
                pnl_pct = (pos['total_pnl'] / pos['total_cost_basis'] * 100) if pos['total_cost_basis'] > 0 else 0
                print(f'{pos["ticker"]}: ${pos["total_pnl"]:.2f} ({pnl_pct:.2f}%)')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    display_portfolio_summary()
