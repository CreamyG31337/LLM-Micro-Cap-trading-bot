#!/usr/bin/env python3
"""
Fix Company Names in Portfolio CSV

This script updates existing portfolio CSV files to replace "Unknown" company names
with proper company names using our improved ticker lookup logic.
"""

import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.ticker_utils import get_company_name
from display.console_output import print_success, print_error, print_warning, print_info


def fix_portfolio_company_names(csv_file_path: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Fix company names in portfolio CSV file.
    
    Args:
        csv_file_path: Path to the portfolio CSV file
        dry_run: If True, only preview changes without applying them
        
    Returns:
        Dictionary with statistics about the fixes applied
    """
    csv_path = Path(csv_file_path)
    if not csv_path.exists():
        print_error(f"CSV file not found: {csv_file_path}")
        return {"error": 1}
    
    # Read the CSV file
    rows = []
    unknown_tickers = set()
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            
            if 'Company' not in fieldnames or 'Ticker' not in fieldnames:
                print_error("CSV file must have 'Company' and 'Ticker' columns")
                return {"error": 1}
            
            for row in reader:
                rows.append(row)
                if row.get('Company', '').strip().lower() in ['unknown', '']:
                    unknown_tickers.add(row['Ticker'])
    
    except Exception as e:
        print_error(f"Error reading CSV file: {e}")
        return {"error": 1}
    
    if not unknown_tickers:
        print_info("No 'Unknown' company names found in the CSV file")
        return {"no_changes": 1}
    
    print_info(f"Found {len(unknown_tickers)} tickers with 'Unknown' company names:")
    for ticker in sorted(unknown_tickers):
        print(f"  • {ticker}")
    
    # Look up company names for unknown tickers
    ticker_to_company = {}
    successful_lookups = 0
    failed_lookups = 0
    
    print_info("Looking up company names...")
    for ticker in sorted(unknown_tickers):
        print(f"Looking up {ticker}...", end=" ")
        company_name = get_company_name(ticker)
        
        if company_name and company_name != 'Unknown' and company_name != ticker:
            ticker_to_company[ticker] = company_name
            successful_lookups += 1
            print(f"✅ {company_name}")
        else:
            failed_lookups += 1
            print(f"❌ Still unknown")
    
    if not ticker_to_company:
        print_warning("No company names could be resolved")
        return {"failed_lookups": failed_lookups}
    
    # Update the rows
    updated_rows = 0
    for row in rows:
        ticker = row['Ticker']
        if ticker in ticker_to_company:
            old_company = row.get('Company', '')
            if old_company.strip().lower() in ['unknown', '']:
                row['Company'] = ticker_to_company[ticker]
                updated_rows += 1
    
    if dry_run:
        print_info(f"DRY RUN: Would update {updated_rows} rows with company names")
        print_info("Use --apply to actually make the changes")
        return {
            "dry_run": 1,
            "would_update": updated_rows,
            "successful_lookups": successful_lookups,
            "failed_lookups": failed_lookups
        }
    
    # Write the updated CSV file
    backup_path = csv_path.with_suffix('.backup' + csv_path.suffix)
    
    try:
        # Create backup
        import shutil
        shutil.copy2(csv_path, backup_path)
        print_info(f"Created backup: {backup_path}")
        
        # Write updated file
        with open(csv_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print_success(f"Updated {updated_rows} rows with company names")
        print_success(f"Successfully looked up {successful_lookups} company names")
        
        if failed_lookups > 0:
            print_warning(f"{failed_lookups} tickers still have unknown company names")
        
        return {
            "success": 1,
            "updated_rows": updated_rows,
            "successful_lookups": successful_lookups,
            "failed_lookups": failed_lookups,
            "backup_created": str(backup_path)
        }
        
    except Exception as e:
        print_error(f"Error writing updated CSV file: {e}")
        return {"error": 1}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix company names in portfolio CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without applying them
  python fix_company_names.py portfolio.csv
  
  # Actually apply the fixes
  python fix_company_names.py portfolio.csv --apply
  
  # Fix specific fund's portfolio
  python fix_company_names.py "trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv" --apply
        """
    )
    
    parser.add_argument(
        "csv_file",
        help="Path to the portfolio CSV file to fix"
    )
    
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the fixes (default is dry run)"
    )
    
    args = parser.parse_args()
    
    print_info(f"Fixing company names in: {args.csv_file}")
    
    if not args.apply:
        print_warning("This is a DRY RUN - no changes will be made")
        print_warning("Use --apply to actually fix the company names")
    
    result = fix_portfolio_company_names(args.csv_file, dry_run=not args.apply)
    
    if result.get("error"):
        sys.exit(1)
    elif result.get("success"):
        print_success("Company name fix completed successfully!")
    elif result.get("dry_run"):
        print_info("Dry run completed - use --apply to make changes")


if __name__ == "__main__":
    main()
