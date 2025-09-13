#!/usr/bin/env python3
"""
Fix Decimal Prices in Portfolio CSV

This script fixes the portfolio CSV to store prices as clean decimals instead of floats.
It rounds all price-related columns to 2 decimal places for better readability and consistency.

Usage:
    python debug/fix_decimal_prices.py
    python debug/fix_decimal_prices.py test_data
"""

import pandas as pd
import os
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decimal_formatter import format_price, format_shares

def fix_decimal_prices(data_dir: str = "my trading"):
    """
    Fix decimal prices in the portfolio CSV by rounding to 2 decimal places.
    
    Args:
        data_dir: Directory containing the portfolio CSV
    """
    portfolio_file = os.path.join(data_dir, "llm_portfolio_update.csv")
    
    if not os.path.exists(portfolio_file):
        print(f"❌ Portfolio file not found: {portfolio_file}")
        return False
    
    try:
        # Read the portfolio data
        df = pd.read_csv(portfolio_file)
        original_df = df.copy()
        
        print(f"📊 Loaded portfolio with {len(df)} records")
        
        # Columns that contain prices and should be rounded to 2 decimal places
        price_columns = [
            'Average Price',
            'Cost Basis', 
            'Stop Loss',
            'Current Price',
            'Total Value',
            'PnL'
        ]
        
        # Columns that contain shares and should be rounded to 4 decimal places
        share_columns = ['Shares']
        
        changes_made = 0
        changes_log = []
        
        print("🔧 Fixing decimal precision...")
        
        # Fix price columns (2 decimal places)
        for col in price_columns:
            if col in df.columns:
                for idx, value in df[col].items():
                    if pd.notna(value) and value != 'NO DATA':
                        try:
                            # Convert to float first, then format properly
                            old_value = float(value)
                            new_value = format_price(old_value)
                            
                            if abs(old_value - new_value) > 0.001:  # Only log if significant change
                                changes_log.append({
                                    'row': idx,
                                    'column': col,
                                    'old_value': old_value,
                                    'new_value': new_value
                                })
                                changes_made += 1
                            
                            df.at[idx, col] = new_value
                            
                        except (ValueError, TypeError):
                            # Skip non-numeric values
                            continue
        
        # Fix share columns (4 decimal places)
        for col in share_columns:
            if col in df.columns:
                for idx, value in df[col].items():
                    if pd.notna(value):
                        try:
                            old_value = float(value)
                            new_value = format_shares(old_value)
                            
                            if abs(old_value - new_value) > 0.0001:  # Only log if significant change
                                changes_log.append({
                                    'row': idx,
                                    'column': col,
                                    'old_value': old_value,
                                    'new_value': new_value
                                })
                                changes_made += 1
                            
                            df.at[idx, col] = new_value
                            
                        except (ValueError, TypeError):
                            # Skip non-numeric values
                            continue
        
        # Show changes made
        if changes_made > 0:
            print(f"\n📝 Made {changes_made} decimal precision fixes:")
            for change in changes_log[:10]:  # Show first 10 changes
                print(f"   Row {change['row']}, {change['column']}: {change['old_value']} → {change['new_value']}")
            
            if len(changes_log) > 10:
                print(f"   ... and {len(changes_log) - 10} more changes")
        else:
            print("✅ No decimal precision fixes needed - all values are already properly formatted")
        
        # Create backup
        backup_file = f"{portfolio_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        original_df.to_csv(backup_file, index=False)
        print(f"💾 Created backup: {backup_file}")
        
        # Save the fixed data
        df.to_csv(portfolio_file, index=False)
        print(f"💾 Saved fixed portfolio to: {portfolio_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing decimal prices: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to fix decimal prices"""
    print("🔧 Fixing Decimal Prices in Portfolio CSV")
    print("=" * 50)
    
    # Check if data directory argument provided
    data_dir = "my trading"
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    print(f"📁 Using data directory: {data_dir}")
    
    success = fix_decimal_prices(data_dir)
    
    if success:
        print("\n🎉 Decimal prices fixed successfully!")
        print("   All prices are now stored as clean decimals (2 decimal places)")
        print("   All shares are now stored as clean decimals (4 decimal places)")
    else:
        print("\n❌ Failed to fix decimal prices")
        sys.exit(1)

if __name__ == "__main__":
    main()
