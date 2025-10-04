#!/usr/bin/env python3
"""
Test main script P&L calculations
"""

import os
import sys
from pathlib import Path

def test_main_script_pnl():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Test the main script repository to verify P&L calculations
    try:
        from trading_script import initialize_repository
        from config.settings import Settings

        settings = Settings()
        repository = initialize_repository(settings)

        print(f'Repository initialized: {type(repository).__name__}')
        print(f'Repository fund: {getattr(repository, "fund", "No fund")}')

        # Test P&L calculations
        positions = repository.get_current_positions()
        print(f'Positions loaded: {len(positions)}')

        if positions:
            total_pnl = sum(float(pos.get('total_pnl', 0)) for pos in positions)
            print(f'Total P&L: ${total_pnl:.2f}')

            # Check individual positions
            sample_pos = positions[0]
            print(f'Sample position PnL: ${sample_pos.get("total_pnl", 0):.2f}')

            # Verify it's not zero
            if total_pnl != 0:
                print('SUCCESS: P&L calculations are working!')
            else:
                print('P&L is still zero')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_main_script_pnl()
