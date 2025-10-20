#!/usr/bin/env python3
"""
Development runner with stricter checking and better error reporting.
"""

import os
import sys
import logging
from pathlib import Path

# Set development mode
os.environ["TRADING_BOT_DEV"] = "true"

# Configure logging for development with UTF-8 encoding for Windows compatibility
import io

# Create a UTF-8 encoded stdout wrapper for Windows emoji support
utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(utf8_stdout),
        logging.FileHandler('trading_bot_dev.log', encoding='utf-8')
    ]
)

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main script
if __name__ == "__main__":
    try:
        from trading_script import main
        import argparse
        
        parser = argparse.ArgumentParser(description="Trading Bot - Development Mode")
        parser.add_argument("--file", help="Path to portfolio CSV")
        parser.add_argument("--data-dir", help="Data directory", default="trading_data/funds/TEST")
        parser.add_argument("--asof", help="Treat this YYYY-MM-DD as 'today'")
        parser.add_argument("--force-fallback", action="store_true", help="Force fallback mode")
        parser.add_argument("--colorama-only", action="store_true", help="Force colorama-only mode")
        parser.add_argument("--no-menu", action="store_true", help="Skip interactive menu and exit after display")
        
        args = parser.parse_args()
        
        print("🔧 Running in DEVELOPMENT MODE with strict checking...")
        print("📝 Logs will be written to trading_bot_dev.log")
        
        # Show environment banner
        from display.console_output import print_environment_banner
        print_environment_banner(args.data_dir)
        
        # Set up environment variables for the main script
        if args.data_dir:
            os.environ["TRADING_DATA_DIR"] = args.data_dir
        if args.file:
            os.environ["TRADING_FILE"] = args.file
        if args.asof:
            os.environ["TRADING_ASOF"] = args.asof
        if args.force_fallback:
            os.environ["FORCE_FALLBACK"] = "true"
        if args.colorama_only:
            os.environ["FORCE_COLORAMA_ONLY"] = "true"
        if args.no_menu:
            os.environ["NON_INTERACTIVE"] = "true"
        
        # Pass arguments to main script
        import sys
        sys.argv = ['trading_script.py']
        if args.data_dir:
            sys.argv.extend(['--data-dir', args.data_dir])
        if args.file:
            sys.argv.extend(['--file', args.file])
        if args.asof:
            sys.argv.extend(['--asof', args.asof])
        if args.force_fallback:
            sys.argv.append('--force-fallback')
        if args.colorama_only:
            sys.argv.append('--colorama-only')
        if args.no_menu:
            sys.argv.append('--non-interactive')
        
        main()
        
    except Exception as e:
        logging.error(f"Development run failed: {e}", exc_info=True)
        print(f"_safe_emoji('❌') Development run failed: {e}")
        sys.exit(1)
