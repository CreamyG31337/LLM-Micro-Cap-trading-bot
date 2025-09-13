#!/usr/bin/env python3
"""
Validate Decimal Precision in CSV Files

This script validates that all numeric values in the portfolio CSV files
have appropriate decimal precision to prevent float precision issues.

Usage:
    python debug/validate_decimal_precision.py
    python debug/validate_decimal_prices.py test_data
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decimal_formatter import validate_decimal_precision, format_price, format_shares

def validate_csv_precision(csv_file: str) -> dict:
    """
    Validate decimal precision in a CSV file.
    
    Args:
        csv_file: Path to CSV file to validate
        
    Returns:
        Dictionary with validation results
    """
    if not os.path.exists(csv_file):
        return {'error': f'File not found: {csv_file}'}
    
    try:
        df = pd.read_csv(csv_file)
        issues = []
        
        # Define precision requirements for each column
        precision_requirements = {
            'Shares': 4,  # 4 decimal places for shares
            'Average Price': 2,  # 2 decimal places for prices
            'Cost Basis': 2,
            'Stop Loss': 2,
            'Current Price': 2,
            'Total Value': 2,
            'PnL': 2
        }
        
        for col_name, expected_precision in precision_requirements.items():
            if col_name in df.columns:
                for idx, value in df[col_name].items():
                    if pd.notna(value) and value != 'NO DATA':
                        try:
                            float_value = float(value)
                            if not validate_decimal_precision(float_value, expected_precision):
                                issues.append({
                                    'row': idx + 1,  # 1-based row number
                                    'column': col_name,
                                    'value': value,
                                    'expected_precision': expected_precision,
                                    'actual_precision': len(f"{float_value:.10f}".rstrip('0').rstrip('.').split('.')[-1]) if '.' in f"{float_value:.10f}".rstrip('0').rstrip('.') else 0
                                })
                        except (ValueError, TypeError):
                            issues.append({
                                'row': idx + 1,
                                'column': col_name,
                                'value': value,
                                'expected_precision': expected_precision,
                                'error': 'Invalid numeric value'
                            })
        
        return {
            'file': csv_file,
            'total_rows': len(df),
            'total_issues': len(issues),
            'issues': issues,
            'status': 'PASS' if len(issues) == 0 else 'FAIL'
        }
        
    except Exception as e:
        return {'error': f'Error reading CSV file: {str(e)}'}

def fix_csv_precision(csv_file: str, backup: bool = True) -> dict:
    """
    Fix decimal precision issues in a CSV file.
    
    Args:
        csv_file: Path to CSV file to fix
        backup: Whether to create a backup before fixing
        
    Returns:
        Dictionary with fix results
    """
    if not os.path.exists(csv_file):
        return {'error': f'File not found: {csv_file}'}
    
    try:
        df = pd.read_csv(csv_file)
        original_df = df.copy()
        
        # Define precision requirements for each column
        precision_requirements = {
            'Shares': 4,  # 4 decimal places for shares
            'Average Price': 2,  # 2 decimal places for prices
            'Cost Basis': 2,
            'Stop Loss': 2,
            'Current Price': 2,
            'Total Value': 2,
            'PnL': 2
        }
        
        fixes_applied = 0
        
        for col_name, expected_precision in precision_requirements.items():
            if col_name in df.columns:
                for idx, value in df[col_name].items():
                    if pd.notna(value) and value != 'NO DATA':
                        try:
                            float_value = float(value)
                            if not validate_decimal_precision(float_value, expected_precision):
                                # Fix the precision
                                if expected_precision == 4:  # Shares
                                    fixed_value = format_shares(float_value)
                                else:  # Prices
                                    fixed_value = format_price(float_value)
                                
                                df.at[idx, col_name] = fixed_value
                                fixes_applied += 1
                        except (ValueError, TypeError):
                            # Skip invalid values
                            continue
        
        if fixes_applied > 0:
            if backup:
                # Create backup
                backup_file = f"{csv_file}.backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
                original_df.to_csv(backup_file, index=False)
                print(f"💾 Created backup: {backup_file}")
            
            # Save fixed data
            df.to_csv(csv_file, index=False)
            print(f"💾 Saved fixed data to: {csv_file}")
        
        return {
            'file': csv_file,
            'fixes_applied': fixes_applied,
            'status': 'FIXED' if fixes_applied > 0 else 'NO_ISSUES'
        }
        
    except Exception as e:
        return {'error': f'Error fixing CSV file: {str(e)}'}

def main():
    """Main function to validate and fix decimal precision"""
    print("🔍 Validating Decimal Precision in CSV Files")
    print("=" * 50)
    
    # Check if data directory argument provided
    data_dir = "my trading"
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    print(f"📁 Using data directory: {data_dir}")
    
    # Files to validate
    files_to_check = [
        os.path.join(data_dir, "llm_portfolio_update.csv"),
        os.path.join(data_dir, "llm_trade_log.csv")
    ]
    
    total_issues = 0
    
    for csv_file in files_to_check:
        if os.path.exists(csv_file):
            print(f"\n📊 Validating {os.path.basename(csv_file)}...")
            
            # Validate precision
            validation_result = validate_csv_precision(csv_file)
            
            if 'error' in validation_result:
                print(f"❌ Error: {validation_result['error']}")
                continue
            
            print(f"   Status: {validation_result['status']}")
            print(f"   Total rows: {validation_result['total_rows']}")
            print(f"   Issues found: {validation_result['total_issues']}")
            
            if validation_result['total_issues'] > 0:
                total_issues += validation_result['total_issues']
                
                # Show first few issues
                print("   Issues:")
                for issue in validation_result['issues'][:5]:
                    if 'error' in issue:
                        print(f"     Row {issue['row']}, {issue['column']}: {issue['error']}")
                    else:
                        print(f"     Row {issue['row']}, {issue['column']}: {issue['value']} "
                              f"(expected {issue['expected_precision']} decimals, got {issue['actual_precision']})")
                
                if len(validation_result['issues']) > 5:
                    print(f"     ... and {len(validation_result['issues']) - 5} more issues")
                
                # Ask if user wants to fix
                print(f"\n🔧 Found {validation_result['total_issues']} precision issues in {os.path.basename(csv_file)}")
                print("   Run with --fix to automatically fix these issues")
        else:
            print(f"⚠️  File not found: {csv_file}")
    
    if total_issues == 0:
        print("\n✅ All CSV files have proper decimal precision!")
    else:
        print(f"\n❌ Found {total_issues} total precision issues across all files")
        print("💡 Use --fix flag to automatically fix these issues")

if __name__ == "__main__":
    main()
