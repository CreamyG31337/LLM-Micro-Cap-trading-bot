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
        parser.add_argument("--data-dir", help="Data directory", default="my trading")
        parser.add_argument("--asof", help="Treat this YYYY-MM-DD as 'today'")
        parser.add_argument("--force-fallback", action="store_true", help="Force fallback mode")
        parser.add_argument("--colorama-only", action="store_true", help="Force colorama-only mode")
        
        args = parser.parse_args()
        
        print("🔧 Running in DEVELOPMENT MODE with strict checking...")
        print("📝 Logs will be written to trading_bot_dev.log")
        
        main(args.file, Path(args.data_dir) if args.data_dir else None)
        
    except Exception as e:
        logging.error(f"Development run failed: {e}", exc_info=True)
        print(f"❌ Development run failed: {e}")
        sys.exit(1)
