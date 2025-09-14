#!/usr/bin/env python3
"""Quick trade adder - simple interactive tool for adding trades from emails.

This is a simplified version of add_trade_from_email.py that's easier to use
for quick trade additions.

Usage:
    python quick_add_trade.py
    python quick_add_trade.py --data-dir trading_data/dev
"""

import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.email_trade_parser import parse_trade_from_email, add_trade_from_email


def main():
    """Simple interactive trade adder."""
    parser = argparse.ArgumentParser(description="Quick trade adder from email notifications")
    parser.add_argument(
        '--data-dir', '-d',
        default='trading_data/prod',
        help='Directory containing trading data files (default: "trading_data/prod")'
    )
    
    args = parser.parse_args()
    
    print("🚀 Quick Trade Adder")
    print("=" * 50)
    print("Paste your email trade notification below and press Enter twice when done:")
    print()
    
    # Collect multi-line input
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "" and lines:  # Empty line after content
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return 0
    except EOFError:
        pass  # Ctrl+D pressed
    
    email_text = "\n".join(lines)
    
    if not email_text.strip():
        print("No email text provided.")
        return 0
    
    print("\n" + "=" * 50)
    print("Parsing trade...")
    
    # Parse the trade
    trade = parse_trade_from_email(email_text)
    
    if not trade:
        print("❌ Could not parse trade from email text")
        print("\nMake sure your email contains:")
        print("• Symbol/Ticker (e.g., VEE, AAPL)")
        print("• Number of shares (e.g., 4, 100)")
        print("• Price per share (e.g., $44.59)")
        print("• Buy/Sell action")
        print("• Optional: timestamp, total cost")
        return 1
    
    # Show parsed trade
    print("✅ Parsed trade:")
    print(f"   {trade.action} {trade.shares} shares of {trade.ticker} @ ${trade.price}")
    print(f"   Total: ${trade.cost_basis}")
    print(f"   Time: {trade.timestamp}")
    
    # Add to system
    print("\nAdding to trading system...")
    success = add_trade_from_email(email_text, args.data_dir)
    
    if success:
        print("✅ Trade added successfully!")
    else:
        print("❌ Failed to add trade")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
