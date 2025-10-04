#!/usr/bin/env python3
"""
Test main script repository initialization
"""

import os
import sys
from pathlib import Path

def test_main_script_repo():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Test if the main script repository initialization works
    try:
        from trading_script import initialize_repository
        from config.settings import Settings

        # Create settings
        settings = Settings()

        # Initialize repository
        repository = initialize_repository(settings)

        print(f'Repository type: {type(repository).__name__}')
        print(f'Repository fund: {getattr(repository, "fund", "No fund")}')

        # Test getting current positions
        positions = repository.get_current_positions()
        print(f'Positions found: {len(positions)}')

        if positions:
            pos = positions[0]
            print(f'Sample position PnL: {pos.get("total_pnl", "N/A")}')

            # Calculate total PnL
            total_pnl = sum(float(pos.get('total_pnl', 0)) for pos in positions)
            print(f'Total PnL: ${total_pnl:.2f}')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_main_script_repo()
