#!/usr/bin/env python3
"""
Standalone Cash Balance Update Utility

This script allows you to easily update your cash balances without 
running the full trading script. Useful for:
- Adding deposits/withdrawals
- Correcting cash balance errors
- Quick balance adjustments

Usage: python update_cash.py
"""

import sys
import argparse
from pathlib import Path

# Modular startup check - handles path setup and dependency checking
try:
    from utils.script_startup import startup_check
    startup_check("update_cash.py")
except ImportError:
    # Fallback for minimal dependency checking if script_startup isn't available
    # Add the project directory to the path so we can import modules
    project_dir = Path(__file__).parent
    sys.path.insert(0, str(project_dir))
    try:
        import pandas
    except ImportError:
        print("\n❌ Missing Dependencies (update_cash.py)")
        print("Required packages not found. Please activate virtual environment:")
        import os
        if os.name == 'nt':  # Windows
            print("  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print("  source venv/bin/activate")
        print("  python update_cash.py")
        print("\n💡 TIP: Use 'python run.py' and select option 'u' to avoid dependency issues")
        sys.exit(1)

try:
    from dual_currency import load_cash_balances, save_cash_balances, CashBalances
    from config.constants import DEFAULT_DATA_DIR
    from portfolio.position_calculator import PositionCalculator
    from data.repositories.csv_repository import CSVRepository
except ImportError as e:
    print(f"_safe_emoji('❌') Error importing required modules: {e}")
    print("Make sure you're running this script from the project directory.")
    sys.exit(1)


def calculate_fund_contributions_total(data_dir: Path) -> float:
    """Calculate total fund contributions from CSV file."""
    try:
        fund_file = data_dir / "fund_contributions.csv"
        if not fund_file.exists():
            return 0.0
        
        import pandas as pd
        df = pd.read_csv(fund_file)
        total = 0.0
        
        for _, row in df.iterrows():
            amount = float(row.get('Amount', 0))
            contrib_type = row.get('Type', 'CONTRIBUTION')
            if contrib_type.upper() == 'CONTRIBUTION':
                total += amount
            elif contrib_type.upper() == 'WITHDRAWAL':
                total -= amount
        
        return total
    except Exception:
        return 0.0


def main():
    """Main function to update cash balances"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Update cash balances")
    parser.add_argument("--data-dir", type=str, help="Data directory path")
    args = parser.parse_args()
    
    from display.console_output import _safe_emoji, print_environment_banner
    print(f"{_safe_emoji('💰')} Cash Balance Update Utility")
    print("=" * 40)
    
    # Show environment banner
    print_environment_banner(args.data_dir)
    
    # Set up data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = Path(DEFAULT_DATA_DIR)
    
    if not data_dir.exists():
        print(f"_safe_emoji('❌') Data directory not found: {data_dir}")
        print("Make sure you have a 'my trading' directory with your trading data.")
        sys.exit(1)
    
    try:
        # Load current balances
        cash_balances = load_cash_balances(data_dir)
        print(f"\n_safe_emoji('💰') Current Cash Balances:")
        print(f"   CAD: ${cash_balances.cad:,.2f}")
        print(f"   USD: ${cash_balances.usd:,.2f}")
        print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
        
        # Display fund contributions total
        fund_total = calculate_fund_contributions_total(data_dir)
        print(f"_safe_emoji('💵') Fund contributions total: ${fund_total:,.2f}")
        
        while True:
            # Get user input
            print("\nOptions:")
            print("  'c' = add/remove CAD")
            print("  'u' = add/remove USD") 
            print("  's' = set exact amounts")
            print("  'v' = view current balances")
            print("  'n' = toggle negative balance mode")
            print("  'q' = quit")
            
            action = input("\nWhat would you like to do? ").strip().lower()
            
            if action == 'q':
                print("👋 Goodbye!")
                break
                
            elif action == 'v':
                print(f"\n_safe_emoji('💰') Current Cash Balances:")
                print(f"   CAD: ${cash_balances.cad:,.2f}")
                print(f"   USD: ${cash_balances.usd:,.2f}")
                print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
                
                # Display fund contributions total
                fund_total = calculate_fund_contributions_total(data_dir)
                print(f"_safe_emoji('💵') Fund contributions total: ${fund_total:,.2f}")
                continue
                
            elif action == 'c':
                try:
                    amount = float(input("Enter CAD amount (positive to add, negative to remove): $"))
                    if amount >= 0:
                        cash_balances.add_cad(amount)
                        print(f"_safe_emoji('✅') Added ${amount:,.2f} CAD")
                    else:
                        if cash_balances.can_afford_cad(abs(amount)):
                            cash_balances.spend_cad(abs(amount))
                            print(f"_safe_emoji('✅') Removed ${abs(amount):,.2f} CAD")
                        else:
                            print(f"_safe_emoji('❌') Cannot remove ${abs(amount):,.2f} CAD - insufficient balance")
                            continue
                except ValueError:
                    print("_safe_emoji('❌') Invalid amount entered")
                    continue
                    
            elif action == 'u':
                try:
                    amount = float(input("Enter USD amount (positive to add, negative to remove): $"))
                    if amount >= 0:
                        cash_balances.add_usd(amount)
                        print(f"_safe_emoji('✅') Added ${amount:,.2f} USD")
                    else:
                        if cash_balances.can_afford_usd(abs(amount)):
                            cash_balances.spend_usd(abs(amount))
                            print(f"_safe_emoji('✅') Removed ${abs(amount):,.2f} USD")
                        else:
                            print(f"_safe_emoji('❌') Cannot remove ${abs(amount):,.2f} USD - insufficient balance")
                            continue
                except ValueError:
                    print("_safe_emoji('❌') Invalid amount entered")
                    continue
                    
            elif action == 's':
                try:
                    cad_amount = float(input("Enter exact CAD balance: $"))
                    usd_amount = float(input("Enter exact USD balance: $"))
                    if cad_amount < 0 or usd_amount < 0:
                        print("_safe_emoji('❌') Balances cannot be negative")
                        continue
                    cash_balances.cad = cad_amount
                    cash_balances.usd = usd_amount
                    print(f"_safe_emoji('✅') Set balances to CAD ${cad_amount:,.2f} and USD ${usd_amount:,.2f}")
                except ValueError:
                    print("_safe_emoji('❌') Invalid amounts entered")
                    continue
                    
            elif action == 'n':
                # Negative balance mode is now always enabled
                print(f"\n🔧 Negative Balance Mode: Always enabled")
                print("All trades can proceed even with insufficient funds,")
                print("resulting in negative balances that can be corrected later.")
                print("_safe_emoji('✅') Negative balance mode is permanently enabled")
                    
            else:
                print("_safe_emoji('❌') Invalid option")
                continue
            
            # Save the updated balances after each successful operation
            save_cash_balances(cash_balances, data_dir)
            
            # Show updated balances
            print(f"\n_safe_emoji('💰') Updated Cash Balances:")
            print(f"   CAD: ${cash_balances.cad:,.2f}")
            print(f"   USD: ${cash_balances.usd:,.2f}")
            print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
            
            # Display fund contributions total
            fund_total = calculate_fund_contributions_total(data_dir)
            print(f"_safe_emoji('💵') Fund contributions total: ${fund_total:,.2f}")
            
    except Exception as e:
        print(f"_safe_emoji('❌') Error updating cash balances: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
