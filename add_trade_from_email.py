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

from utils.email_trade_parser import parse_trade_from_email
from data.repositories.csv_repository import CSVRepository
from portfolio.trade_processor import TradeProcessor
from debug.rebuild_portfolio_from_scratch import rebuild_portfolio_from_scratch


def main():
    """Main entry point for the email trade parser CLI."""
    parser = argparse.ArgumentParser(
        description="Add trades from email notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multi-email mode (default) - paste multiple emails separated by blank lines
  python add_trade_from_email.py

  # Parse from command line text
  python add_trade_from_email.py --text "Your order has been filled..."

  # Parse from file
  python add_trade_from_email.py --file email.txt

  # Interactive mode - single email input
  python add_trade_from_email.py --interactive

  # Test mode - just parse without adding to system
  python add_trade_from_email.py --test --multi
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
        default='trading_data/prod',
        help='Directory containing trading data files (default: "trading_data/prod")'
    )
    
    parser.add_argument(
        '--test', '--dry-run',
        action='store_true',
        help='Test mode - parse and display trade without adding to system'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode - prompt for email text input (single email)'
    )
    
    parser.add_argument(
        '--multi', '-m',
        action='store_true',
        help='Multi-email mode - paste multiple emails separated by blank lines, press Enter 3 times when done'
    )
    
    args = parser.parse_args()
    
    # Helper: add a single parsed trade to trade log only
    def _save_trade_only(trade_obj) -> bool:
        try:
            repo = CSVRepository(args.data_dir)
            # Idempotency guard: avoid duplicates
            from utils.email_trade_parser import is_duplicate_trade
            if is_duplicate_trade(trade_obj, repo):
                print("ℹ️  Duplicate trade detected; skipping insert.")
                return True
            # Save trade; do not update portfolio here
            repo.save_trade(trade_obj)
            return True
        except Exception as ex:
            print(f"❌ Failed to save trade: {ex}")
            return False
    
    def _print_trade(trade_obj) -> None:
        print("✅ Parsed trade:")
        print(f"   Symbol: {trade_obj.ticker}")
        print(f"   Action: {trade_obj.action}")
        print(f"   Shares: {trade_obj.shares}")
        print(f"   Price: ${trade_obj.price}")
        print(f"   Total Cost: ${trade_obj.cost_basis}")
        print(f"   Timestamp: {trade_obj.timestamp}")
        print(f"   Reason: {trade_obj.reason}")
        print(f"   Currency: {trade_obj.currency}")
    
    # Multi-email interactive mode by default when no --text/--file provided
    if args.multi or (not args.text and not args.file and not args.interactive):
        print("📧 Multi-email mode: Paste multiple trade emails separated by blank lines.")
        print("Press Enter 3 times when you're done pasting all emails.")
        print("=" * 60)
        
        # Collect all input lines
        all_lines = []
        empty_line_count = 0
        
        try:
            while True:
                line = input()
                all_lines.append(line)
                
                # Count consecutive empty lines
                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        # Two consecutive empty lines means we're done
                        break
                else:
                    empty_line_count = 0
                    
        except EOFError:
            # User pressed Ctrl+D/Ctrl+Z
            pass
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
        
        # Split emails by double newlines (empty lines)
        email_blocks = []
        current_block = []
        
        for line in all_lines:
            if line.strip() == "":
                if current_block:  # Only add if we have content
                    email_blocks.append("\n".join(current_block))
                    current_block = []
            else:
                current_block.append(line)
        
        # Add the last block if it exists
        if current_block:
            email_blocks.append("\n".join(current_block))
        
        if not email_blocks:
            print("No email content provided.")
            return 0
        
        print(f"\n📊 Found {len(email_blocks)} email(s) to process...")
        saved_count = 0
        
        for i, email_text in enumerate(email_blocks, 1):
            if not email_text.strip():
                continue
                
            print(f"\n--- Processing email {i}/{len(email_blocks)} ---")
            print("Parsing email trade...")
            
            trade = parse_trade_from_email(email_text)
            if not trade:
                print("❌ Failed to parse trade from email text")
                continue
                
            _print_trade(trade)
            
            if args.test:
                print("🧪 Test mode - not saving trade")
            else:
                resp = input("Add this trade? (y/N): ").strip().lower()
                if resp in ('y','yes'):
                    if _save_trade_only(trade):
                        print("✅ Trade saved to trade log.")
                        saved_count += 1
                    else:
                        print("❌ Failed to save trade.")
                else:
                    print("Trade not saved.")
        
        # After processing all emails, optionally rebuild
        if saved_count > 0 and not args.test:
            resp = input(f"\nRebuild portfolio CSV from trade log now? ({saved_count} trades added) (Y/n): ").strip().lower()
            if resp in ('', 'y', 'yes'):
                print("\n🔄 Rebuilding portfolio from trade log...")
                ok = rebuild_portfolio_from_scratch(args.data_dir)
                if ok:
                    print("✅ Portfolio rebuilt successfully.")
                else:
                    print("❌ Failed to rebuild portfolio.")
        elif saved_count == 0 and not args.test:
            print("\nℹ️  No trades were added to the system.")
        
        return 0
    
    # Single-email paths
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
    elif args.interactive:
        print("Paste your email trade notification below (Ctrl+D/Ctrl+Z to finish):")
        print("=" * 60)
        try:
            email_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
    else:
        print("Error: No email text provided. Use --text, --file, --interactive, or --multi")
        return 1
    
    if not email_text or not email_text.strip():
        print("Error: No email text provided")
        return 1
    
    print("Parsing email trade...")
    trade = parse_trade_from_email(email_text)
    if not trade:
        print("❌ Failed to parse trade from email text")
        return 1
    _print_trade(trade)
    if args.test:
        print("\n🧪 Test mode - trade not added to system")
        return 0
    response = input("\nAdd this trade to your trading system? (y/N): ").strip().lower()
    if response not in ('y','yes'):
        print("Trade not added.")
        return 0
    if _save_trade_only(trade):
        print("✅ Trade successfully added to your trade log!")
        rebuild = input("Rebuild portfolio CSV now? (Y/n): ").strip().lower()
        if rebuild in ('', 'y', 'yes'):
            ok = rebuild_portfolio_from_scratch(args.data_dir)
            if ok:
                print("✅ Portfolio rebuilt successfully.")
            else:
                print("❌ Failed to rebuild portfolio.")
        return 0
    else:
        print("❌ Failed to add trade to system")
        return 1


if __name__ == "__main__":
    sys.exit(main())
