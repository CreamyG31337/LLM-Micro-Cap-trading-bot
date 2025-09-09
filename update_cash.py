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
from pathlib import Path

# Add the project directory to the path so we can import modules
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

try:
    from dual_currency import load_cash_balances, save_cash_balances, CashBalances
    from trading_script import DATA_DIR, set_data_dir, DEFAULT_DATA_DIR, calculate_fund_contributions_total
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you're running this script from the project directory.")
    sys.exit(1)


def main():
    """Main function to update cash balances"""
    print("💰 Cash Balance Update Utility")
    print("=" * 40)
    
    # Set up data directory
    set_data_dir(DEFAULT_DATA_DIR)
    data_dir = DATA_DIR
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        print("Make sure you have a 'my trading' directory with your trading data.")
        sys.exit(1)
    
    try:
        # Load current balances
        cash_balances = load_cash_balances(data_dir)
        print(f"\n💰 Current Cash Balances:")
        print(f"   CAD: ${cash_balances.cad:,.2f}")
        print(f"   USD: ${cash_balances.usd:,.2f}")
        print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
        
        # Display fund contributions total
        fund_total = calculate_fund_contributions_total(str(data_dir))
        print(f"💵 Fund contributions total: ${fund_total:,.2f}")
        
        while True:
            # Get user input
            print("\nOptions:")
            print("  'c' = add/remove CAD")
            print("  'u' = add/remove USD") 
            print("  's' = set exact amounts")
            print("  'v' = view current balances")
            print("  'q' = quit")
            
            action = input("\nWhat would you like to do? ").strip().lower()
            
            if action == 'q':
                print("👋 Goodbye!")
                break
                
            elif action == 'v':
                print(f"\n💰 Current Cash Balances:")
                print(f"   CAD: ${cash_balances.cad:,.2f}")
                print(f"   USD: ${cash_balances.usd:,.2f}")
                print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
                
                # Display fund contributions total
                fund_total = calculate_fund_contributions_total(str(data_dir))
                print(f"💵 Fund contributions total: ${fund_total:,.2f}")
                continue
                
            elif action == 'c':
                try:
                    amount = float(input("Enter CAD amount (positive to add, negative to remove): $"))
                    if amount >= 0:
                        cash_balances.add_cad(amount)
                        print(f"✅ Added ${amount:,.2f} CAD")
                    else:
                        if cash_balances.can_afford_cad(abs(amount)):
                            cash_balances.spend_cad(abs(amount))
                            print(f"✅ Removed ${abs(amount):,.2f} CAD")
                        else:
                            print(f"❌ Cannot remove ${abs(amount):,.2f} CAD - insufficient balance")
                            continue
                except ValueError:
                    print("❌ Invalid amount entered")
                    continue
                    
            elif action == 'u':
                try:
                    amount = float(input("Enter USD amount (positive to add, negative to remove): $"))
                    if amount >= 0:
                        cash_balances.add_usd(amount)
                        print(f"✅ Added ${amount:,.2f} USD")
                    else:
                        if cash_balances.can_afford_usd(abs(amount)):
                            cash_balances.spend_usd(abs(amount))
                            print(f"✅ Removed ${abs(amount):,.2f} USD")
                        else:
                            print(f"❌ Cannot remove ${abs(amount):,.2f} USD - insufficient balance")
                            continue
                except ValueError:
                    print("❌ Invalid amount entered")
                    continue
                    
            elif action == 's':
                try:
                    cad_amount = float(input("Enter exact CAD balance: $"))
                    usd_amount = float(input("Enter exact USD balance: $"))
                    if cad_amount < 0 or usd_amount < 0:
                        print("❌ Balances cannot be negative")
                        continue
                    cash_balances.cad = cad_amount
                    cash_balances.usd = usd_amount
                    print(f"✅ Set balances to CAD ${cad_amount:,.2f} and USD ${usd_amount:,.2f}")
                except ValueError:
                    print("❌ Invalid amounts entered")
                    continue
            else:
                print("❌ Invalid option")
                continue
            
            # Save the updated balances after each successful operation
            save_cash_balances(cash_balances, data_dir)
            
            # Show updated balances
            print(f"\n💰 Updated Cash Balances:")
            print(f"   CAD: ${cash_balances.cad:,.2f}")
            print(f"   USD: ${cash_balances.usd:,.2f}")
            print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
            
            # Display fund contributions total
            fund_total = calculate_fund_contributions_total(str(data_dir))
            print(f"💵 Fund contributions total: ${fund_total:,.2f}")
            
    except Exception as e:
        print(f"❌ Error updating cash balances: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
