#!/usr/bin/env python3
"""Command-line tool to add trades from email notifications.

This script allows you to quickly add trades to your trading system by pasting
email trade notifications. It parses the email text and automatically extracts
trade information.

Usage:
    python add_trade_from_email.py
    python add_trade_from_email.py --text "Your order has been filled..."
    python add_trade_from_email.py --file email.txt
    python add_trade_from_email.py --interactive
"""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.email_trade_parser import parse_trade_from_email, add_trade_from_email


def main():
    """Main entry point for the email trade parser CLI."""
    parser = argparse.ArgumentParser(
        description="Add trades from email notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - paste email text when prompted
  python add_trade_from_email.py

  # Parse from command line text
  python add_trade_from_email.py --text "Your order has been filled..."

  # Parse from file
  python add_trade_from_email.py --file email.txt

  # Test mode - just parse without adding to system
  python add_trade_from_email.py --test --text "Your order has been filled..."
        """
    )
    
    parser.add_argument(
        '--text', '-t',
        help='Email text to parse (if not provided, will prompt for input)'
    )
    
    parser.add_argument(
        '--file', '-f',
        help='File containing email text to parse'
    )
    
    parser.add_argument(
        '--data-dir', '-d',
        default='my trading',
        help='Directory containing trading data files (default: "my trading")'
    )
    
    parser.add_argument(
        '--test', '--dry-run',
        action='store_true',
        help='Test mode - parse and display trade without adding to system'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode - prompt for email text input'
    )
    
    args = parser.parse_args()
    
    # Get email text
    email_text = None
    
    if args.text:
        email_text = args.text
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                email_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found")
            return 1
        except Exception as e:
            print(f"Error reading file: {e}")
            return 1
    elif args.interactive or (not args.text and not args.file):
        # Interactive mode
        print("Paste your email trade notification below (press Ctrl+D or Ctrl+Z when done):")
        print("=" * 60)
        try:
            email_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
    else:
        print("Error: No email text provided. Use --text, --file, or --interactive")
        return 1
    
    if not email_text or not email_text.strip():
        print("Error: No email text provided")
        return 1
    
    # Parse the trade
    print("Parsing email trade...")
    trade = parse_trade_from_email(email_text)
    
    if not trade:
        print("❌ Failed to parse trade from email text")
        print("\nMake sure your email contains:")
        print("- Symbol/Ticker")
        print("- Number of shares")
        print("- Price per share")
        print("- Buy/Sell action")
        print("- Optional: timestamp, total cost")
        return 1
    
    # Display parsed trade
    print("✅ Successfully parsed trade:")
    print(f"   Symbol: {trade.ticker}")
    print(f"   Action: {trade.action}")
    print(f"   Shares: {trade.shares}")
    print(f"   Price: ${trade.price}")
    print(f"   Total Cost: ${trade.cost_basis}")
    print(f"   Timestamp: {trade.timestamp}")
    print(f"   Reason: {trade.reason}")
    
    if args.test:
        print("\n🧪 Test mode - trade not added to system")
        return 0
    
    # Confirm before adding
    print(f"\nAdd this trade to your trading system? (y/N): ", end='')
    try:
        response = input().strip().lower()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0
    
    if response not in ['y', 'yes']:
        print("Trade not added.")
        return 0
    
    # Add the trade
    print("Adding trade to system...")
    success = add_trade_from_email(email_text, args.data_dir)
    
    if success:
        print("✅ Trade successfully added to your trading system!")
        return 0
    else:
        print("❌ Failed to add trade to system")
        return 1


if __name__ == "__main__":
    sys.exit(main())
