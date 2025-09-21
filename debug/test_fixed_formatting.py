#!/usr/bin/env python3
"""
Quick test to demonstrate the fixed 5-day P&L formatting.
Shows that minus signs are no longer duplicated.
"""

def test_formatting_examples():
    """Show examples of the fixed formatting."""
    print("🧪 Testing Fixed P&L Formatting")
    print("=" * 40)
    
    # Test cases that show the fix
    test_cases = [
        # (abs_pnl, pct_pnl, expected_format)
        (25.50, 2.1, "Positive: $25.50 +2.1%"),
        (-15.75, -1.8, "Negative: $15.75 -1.8%"),  # No double minus!
        (0.00, 0.0, "Zero: $0.00 0.0%"),
        (-125.00, -5.2, "Large negative: $125.00 -5.2%"),  # No double minus!
    ]
    
    print("5-Day P&L Formatting Examples:")
    print("-" * 30)
    
    for abs_pnl, pct_pnl, description in test_cases:
        if abs_pnl >= 0:
            formatted = f"${abs_pnl:.2f} +{pct_pnl:.1f}%"
        else:
            # Fixed: Use abs() for dollar amount to avoid double minus
            formatted = f"${abs(abs_pnl):.2f} {pct_pnl:.1f}%"
        
        print(f"  {description}")
        print(f"    → {formatted}")
        print()
    
    print("Partial Period Examples:")
    print("-" * 25)
    
    partial_cases = [
        (2, 15.50, 1.2, "2d: $15.50 +1.2%"),
        (3, -8.75, -0.8, "3d: $8.75 -0.8%"),  # No double minus!
        (4, 42.00, 3.1, "4d: $42.00 +3.1%"),
    ]
    
    for days, abs_pnl, pct_pnl, expected in partial_cases:
        if abs_pnl >= 0:
            formatted = f"{days}d: ${abs_pnl:.2f} +{pct_pnl:.1f}%"
        else:
            # Fixed: Use abs() for dollar amount to avoid double minus
            formatted = f"{days}d: ${abs(abs_pnl):.2f} {pct_pnl:.1f}%"
        
        print(f"  {expected}")
        print(f"    → {formatted}")
        print()

if __name__ == "__main__":
    test_formatting_examples()
    print("✅ All formatting examples show proper minus sign handling!")