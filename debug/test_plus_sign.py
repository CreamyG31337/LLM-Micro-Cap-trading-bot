#!/usr/bin/env python3
"""
Test script to verify + sign formatting is working correctly.
This will help us debug if the issue is with caching or something else.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from rich.console import Console
from rich.table import Table

def test_plus_sign_formatting():
    """Test the P&L formatting logic directly."""
    print("Testing + sign formatting...")
    
    console = Console()
    
    # Test data with positive P&L
    test_position = {
        'ticker': 'TEST',
        'company': 'Test Company',
        'unrealized_pnl': 150.50,
        'cost_basis': 1000.00,
        'shares': 100,
        'current_price': 11.50,
        'avg_price': 10.00,
    }
    
    # Simulate the exact logic from table_formatter.py
    unrealized_pnl_raw = test_position.get('unrealized_pnl', 0) or 0
    cost_basis_raw = test_position.get('cost_basis', 0) or 0
    
    # Convert to Decimal
    unrealized_pnl = Decimal(str(unrealized_pnl_raw))
    cost_basis = Decimal(str(cost_basis_raw))
    
    # Calculate P&L percentage 
    if cost_basis > 0:
        total_pnl_pct = float((unrealized_pnl / cost_basis) * 100)
        print(f"Calculated P&L percentage: {total_pnl_pct:.1f}%")
        
        if total_pnl_pct > 0:
            # This should match line 241 in table_formatter.py
            total_pnl_display = f"[green]+${float(abs(unrealized_pnl)):,.2f} +{total_pnl_pct:.1f}%[/green]"
            print(f"Formatted display string: {total_pnl_display}")
            
            # Test Rich rendering
            console.print(f"Rich output: {total_pnl_display}")
            
    # Also test with a simple table
    table = Table(title="P&L Test")
    table.add_column("P&L Display")
    table.add_row(total_pnl_display)
    
    console.print("\nTable test:")
    console.print(table)

if __name__ == "__main__":
    test_plus_sign_formatting()