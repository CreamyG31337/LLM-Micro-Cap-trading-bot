#!/usr/bin/env python3
"""
Admin script to copy fund data from one fund to another.

SAFETY: Production funds can only be copied to non-production funds.

Usage:
    python debug/copy_fund_data.py "Project Chimera" "TEST"
    python debug/copy_fund_data.py "Project Chimera" "TEST" --dry-run
"""

import sys
from pathlib import Path

# Add web_dashboard to path
project_root = Path(__file__).parent.parent
web_dashboard_path = project_root / "web_dashboard"
sys.path.insert(0, str(web_dashboard_path))

from admin_utils import copy_fund_data

def main():
    if len(sys.argv) < 3:
        print("Usage: python copy_fund_data.py <source_fund> <dest_fund> [--dry-run]")
        print("Example: python copy_fund_data.py 'Project Chimera' 'TEST'")
        sys.exit(1)
    
    source_fund = sys.argv[1]
    dest_fund = sys.argv[2]
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")
    
    success = copy_fund_data(source_fund, dest_fund, dry_run=dry_run)
    
    if success:
        if dry_run:
            print("\nDry run complete - use without --dry-run to perform actual copy")
        else:
            print("\nFund copy completed successfully!")
    else:
        print("\nFund copy failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

