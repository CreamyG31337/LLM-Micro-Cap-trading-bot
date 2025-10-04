#!/usr/bin/env python3
"""
Test repository fund handling
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_repository_fund():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    from data.repositories.repository_factory import RepositoryFactory

    # Load environment variables
    load_dotenv(Path('web_dashboard') / '.env')

    # Create repository for Project Chimera
    repository = RepositoryFactory.create_repository(
        'supabase',
        url=os.getenv('SUPABASE_URL'),
        key=os.getenv('SUPABASE_ANON_KEY'),
        fund='Project Chimera'
    )

    print('=== Testing Repository Fund Handling ===')
    print(f'Repository fund: {repository.fund}')

    # Test get_current_positions without fund parameter (should use repository fund)
    try:
        positions = repository.get_current_positions()
        print(f'Positions without fund param: {len(positions)}')
        if positions:
            pos = positions[0]
            print(f'Sample fund: {pos.get("fund")}')

            # Calculate totals
            total_pnl = sum(float(pos.get('total_pnl', 0)) for pos in positions)
            total_market_value = sum(float(pos.get('total_market_value', 0)) for pos in positions)
            total_cost_basis = sum(float(pos.get('total_cost_basis', 0)) for pos in positions)

            print(f'Total PnL: ${total_pnl:.2f}')
            print(f'Total Market Value: ${total_market_value:.2f}')
            print(f'Total Cost Basis: ${total_cost_basis:.2f}')

            if total_cost_basis > 0:
                performance_pct = (total_pnl / total_cost_basis * 100)
                print(f'Performance: {performance_pct:.2f}%')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_repository_fund()
