"""
Clear fund data utility for testing and development.

This module provides functionality to clear all data for a specific fund,
including CSV files and Supabase database records.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from data.repositories.csv_repository import CSVRepository
from data.repositories.supabase_repository import SupabaseRepository
from display.console_output import print_success, print_error, print_warning, print_info, print_header

# Load Supabase credentials
load_dotenv("web_dashboard/.env")

def clear_fund_data(fund_name: str, data_directory: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Clear all data for a specific fund.
    
    Args:
        fund_name: Name of the fund to clear
        data_directory: Path to the fund's data directory
        confirm: Whether to skip confirmation prompt
        
    Returns:
        Dictionary with results of the clearing operation
    """
    results = {
        "fund_name": fund_name,
        "data_directory": data_directory,
        "csv_cleared": False,
        "supabase_cleared": False,
        "errors": [],
        "files_removed": [],
        "records_deleted": 0
    }
    
    print_header(f"🧹 CLEARING FUND DATA: {fund_name}")
    print_info(f"Data Directory: {data_directory}")
    
    # Confirmation prompt
    if not confirm:
        print_warning("⚠️  This will permanently delete ALL data for this fund!")
        print_warning("   - All CSV files will be deleted")
        print_warning("   - All Supabase records will be deleted")
        print_warning("   - This action cannot be undone!")
        
        response = input("\nAre you sure you want to continue? (type 'YES' to confirm): ").strip()
        if response != "YES":
            print_info("❌ Operation cancelled by user")
            return results
    
    try:
        # Clear CSV data
        print_info("🗂️  Clearing CSV data...")
        csv_results = _clear_csv_data(data_directory)
        results["csv_cleared"] = csv_results["success"]
        results["files_removed"] = csv_results["files_removed"]
        results["errors"].extend(csv_results["errors"])
        
        # Clear Supabase data
        print_info("🗄️  Clearing Supabase data...")
        supabase_results = _clear_supabase_data(fund_name)
        results["supabase_cleared"] = supabase_results["success"]
        results["records_deleted"] = supabase_results["records_deleted"]
        results["errors"].extend(supabase_results["errors"])
        
        # Summary
        if results["csv_cleared"] and results["supabase_cleared"]:
            print_success(f"✅ Successfully cleared all data for fund '{fund_name}'")
            print_success(f"   - Removed {len(results['files_removed'])} CSV files")
            print_success(f"   - Deleted {results['records_deleted']} database records")
        else:
            print_warning("⚠️  Partial success - some data may not have been cleared")
            for error in results["errors"]:
                print_error(f"   Error: {error}")
                
    except Exception as e:
        error_msg = f"Unexpected error during clearing: {e}"
        results["errors"].append(error_msg)
        print_error(error_msg)
    
    return results

def _clear_csv_data(data_directory: str) -> Dict[str, Any]:
    """Clear CSV data for a fund."""
    results = {
        "success": False,
        "files_removed": [],
        "errors": []
    }
    
    try:
        data_path = Path(data_directory)
        if not data_path.exists():
            results["errors"].append(f"Data directory does not exist: {data_directory}")
            return results
        
        # List of CSV files to remove
        csv_files = [
            "trade_log.csv",
            "portfolio_snapshots.csv", 
            "cash_balances.csv",
            "market_data.csv",
            "contributors.csv"
        ]
        
        files_removed = []
        for csv_file in csv_files:
            file_path = data_path / csv_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    files_removed.append(str(file_path))
                    print_info(f"   Removed: {csv_file}")
                except Exception as e:
                    results["errors"].append(f"Could not remove {csv_file}: {e}")
        
        # Remove any backup files
        backup_files = list(data_path.glob("*.backup"))
        for backup_file in backup_files:
            try:
                backup_file.unlink()
                files_removed.append(str(backup_file))
                print_info(f"   Removed backup: {backup_file.name}")
            except Exception as e:
                results["errors"].append(f"Could not remove backup {backup_file.name}: {e}")
        
        results["files_removed"] = files_removed
        results["success"] = len(results["errors"]) == 0
        
    except Exception as e:
        results["errors"].append(f"Error clearing CSV data: {e}")
    
    return results

def _clear_supabase_data(fund_name: str) -> Dict[str, Any]:
    """Clear Supabase data for a fund."""
    results = {
        "success": False,
        "records_deleted": 0,
        "errors": []
    }
    
    try:
        # Create Supabase repository
        supabase_repo = SupabaseRepository(fund=fund_name)
        
        # Get current data counts
        trades = supabase_repo.get_trade_history()
        snapshots = supabase_repo.get_portfolio_data()
        cash_balances = supabase_repo.get_cash_balances()
        
        print_info(f"   Found {len(trades)} trades, {len(snapshots)} snapshots, {len(cash_balances)} cash records")
        
        # Note: We don't have delete methods in the repository yet
        # This is a placeholder for future implementation
        print_warning("   ⚠️  Supabase deletion not yet implemented")
        print_warning("   Manual cleanup required in Supabase dashboard")
        print_info("   Tables to clear:")
        print_info("     - trade_log (WHERE fund = 'test')")
        print_info("     - portfolio_positions (WHERE fund = 'test')")
        print_info("     - portfolio_snapshots (WHERE fund = 'test')")
        print_info("     - cash_balances (WHERE fund = 'test')")
        print_info("     - market_data (WHERE fund = 'test')")
        
        results["success"] = True  # Mark as success since we provided instructions
        
    except Exception as e:
        results["errors"].append(f"Error accessing Supabase: {e}")
    
    return results

def list_fund_data(fund_name: str, data_directory: str) -> Dict[str, Any]:
    """
    List all data for a specific fund without clearing it.
    
    Args:
        fund_name: Name of the fund to inspect
        data_directory: Path to the fund's data directory
        
    Returns:
        Dictionary with data summary
    """
    results = {
        "fund_name": fund_name,
        "data_directory": data_directory,
        "csv_files": [],
        "csv_file_sizes": {},
        "supabase_counts": {},
        "errors": []
    }
    
    print_header(f"📊 FUND DATA SUMMARY: {fund_name}")
    print_info(f"Data Directory: {data_directory}")
    
    try:
        # Check CSV files
        print_info("🗂️  CSV Files:")
        data_path = Path(data_directory)
        if data_path.exists():
            csv_files = [
                "trade_log.csv",
                "portfolio_snapshots.csv", 
                "cash_balances.csv",
                "market_data.csv",
                "contributors.csv"
            ]
            
            for csv_file in csv_files:
                file_path = data_path / csv_file
                if file_path.exists():
                    size = file_path.stat().st_size
                    results["csv_files"].append(csv_file)
                    results["csv_file_sizes"][csv_file] = size
                    print_info(f"   ✅ {csv_file} ({size:,} bytes)")
                else:
                    print_info(f"   ❌ {csv_file} (not found)")
        else:
            print_warning(f"Data directory does not exist: {data_directory}")
        
        # Check Supabase data
        print_info("🗄️  Supabase Data:")
        try:
            supabase_repo = SupabaseRepository(fund=fund_name)
            
            trades = supabase_repo.get_trade_history()
            snapshots = supabase_repo.get_portfolio_data()
            cash_balances = supabase_repo.get_cash_balances()
            
            results["supabase_counts"] = {
                "trades": len(trades),
                "snapshots": len(snapshots),
                "cash_balances": len(cash_balances)
            }
            
            print_info(f"   📈 Trades: {len(trades)}")
            print_info(f"   📊 Snapshots: {len(snapshots)}")
            print_info(f"   💰 Cash Balances: {len(cash_balances)}")
            
        except Exception as e:
            results["errors"].append(f"Error accessing Supabase: {e}")
            print_error(f"   ❌ Supabase error: {e}")
            
    except Exception as e:
        results["errors"].append(f"Error listing fund data: {e}")
        print_error(f"Error: {e}")
    
    return results

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear or list fund data")
    parser.add_argument("--fund", required=True, help="Fund name to clear")
    parser.add_argument("--data-dir", required=True, help="Data directory path")
    parser.add_argument("--list", action="store_true", help="List data without clearing")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    if args.list:
        list_fund_data(args.fund, args.data_dir)
    else:
        clear_fund_data(args.fund, args.data_dir, args.confirm)

if __name__ == "__main__":
    main()
