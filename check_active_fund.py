#!/usr/bin/env python3
"""
Check what the current active fund is
"""

import os
import sys
from pathlib import Path

def check_active_fund():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Check what the current active fund is
    from utils.fund_manager import get_fund_manager

    try:
        fund_manager = get_fund_manager()
        active_fund = fund_manager.get_active_fund()
        print(f'Active fund: {active_fund}')
        print(f'Active fund name: {active_fund.name if active_fund else "None"}')
    except Exception as e:
        print(f'Error getting active fund: {e}')

if __name__ == "__main__":
    check_active_fund()
