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

# Configure logging for development
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot_dev.log')
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
        parser.add_argument("--data-dir", help="Data directory", default="trading_data/dev")
        parser.add_argument("--asof", help="Treat this YYYY-MM-DD as 'today'")
        parser.add_argument("--force-fallback", action="store_true", help="Force fallback mode")
        parser.add_argument("--colorama-only", action="store_true", help="Force colorama-only mode")
        
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
        
        main()
        
    except Exception as e:
        logging.error(f"Development run failed: {e}", exc_info=True)
        print(f"_safe_emoji('❌') Development run failed: {e}")
        sys.exit(1)
