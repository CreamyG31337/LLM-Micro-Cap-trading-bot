#!/usr/bin/env python3
"""
Sync trading data from local CSV files to Supabase
This script can be run from your local trading bot to update the web dashboard
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_local_data(data_dir: str = "../trading_data/prod") -> dict:
    """Load data from local CSV files"""
    data_dir = Path(data_dir)
    
    # Load portfolio data
    portfolio_file = data_dir / "llm_portfolio_update.csv"
    if portfolio_file.exists():
        portfolio_df = pd.read_csv(portfolio_file)
        portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'])
        logger.info(f"✅ Loaded portfolio data: {len(portfolio_df)} entries")
    else:
        portfolio_df = pd.DataFrame()
        logger.warning(f"⚠️  Portfolio file not found: {portfolio_file}")
    
    # Load trade log
    trade_file = data_dir / "llm_trade_log.csv"
    if trade_file.exists():
        trade_df = pd.read_csv(trade_file)
        trade_df['Date'] = pd.to_datetime(trade_df['Date'])
        logger.info(f"✅ Loaded trade log: {len(trade_df)} entries")
    else:
        trade_df = pd.DataFrame()
        logger.warning(f"⚠️  Trade log file not found: {trade_file}")
    
    # Load cash balances
    cash_file = data_dir / "cash_balances.json"
    if cash_file.exists():
        with open(cash_file, 'r') as f:
            cash_balances = json.load(f)
        logger.info(f"✅ Loaded cash balances: {cash_balances}")
    else:
        cash_balances = {"CAD": 0.0, "USD": 0.0}
        logger.warning(f"⚠️  Cash balances file not found: {cash_file}")
    
    return {
        "portfolio": portfolio_df,
        "trades": trade_df,
        "cash_balances": cash_balances
    }

def sync_to_supabase(data_dir: str = "../trading_data/prod") -> bool:
    """Sync local trading data to Supabase"""
    logger.info("🚀 Starting sync to Supabase...")
    
    # Check environment variables
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        logger.error("❌ SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
        return False
    
    try:
        # Initialize Supabase client
        client = SupabaseClient()
        
        # Test connection
        if not client.test_connection():
            logger.error("❌ Failed to connect to Supabase")
            return False
        
        # Load local data
        data = load_local_data(data_dir)
        
        # Sync portfolio positions
        if not data["portfolio"].empty:
            logger.info("📊 Syncing portfolio positions...")
            if client.upsert_portfolio_positions(data["portfolio"]):
                logger.info("✅ Portfolio positions synced successfully")
            else:
                logger.error("❌ Failed to sync portfolio positions")
                return False
        else:
            logger.info("ℹ️  No portfolio data to sync")
        
        # Sync trade log
        if not data["trades"].empty:
            logger.info("📋 Syncing trade log...")
            if client.upsert_trade_log(data["trades"]):
                logger.info("✅ Trade log synced successfully")
            else:
                logger.error("❌ Failed to sync trade log")
                return False
        else:
            logger.info("ℹ️  No trade log data to sync")
        
        # Sync cash balances
        logger.info("💰 Syncing cash balances...")
        if client.upsert_cash_balances(data["cash_balances"]):
            logger.info("✅ Cash balances synced successfully")
        else:
            logger.error("❌ Failed to sync cash balances")
            return False
        
        # Verify sync
        logger.info("🔍 Verifying sync...")
        positions = client.get_current_positions()
        trades = client.get_trade_log(limit=5)
        balances = client.get_cash_balances()
        
        logger.info(f"✅ Sync verification complete:")
        logger.info(f"   - Current positions: {len(positions)}")
        logger.info(f"   - Recent trades: {len(trades)}")
        logger.info(f"   - Cash balances: {balances}")
        
        logger.info("🎉 Sync to Supabase completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        return False

def main():
    """Main sync function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync trading data to Supabase")
    parser.add_argument("--data-dir", default="../trading_data/prod", 
                       help="Path to trading data directory")
    parser.add_argument("--env-file", help="Path to .env file with Supabase credentials")
    
    args = parser.parse_args()
    
    # Load environment variables
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    else:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("⚠️  python-dotenv not installed. Install it with: pip install python-dotenv")
            logger.info("   Or set environment variables manually")
    
    # Run sync
    success = sync_to_supabase(args.data_dir)
    
    if success:
        print("\n🎉 Sync completed successfully!")
        print("   Your web dashboard will now show the latest data")
    else:
        print("\n❌ Sync failed. Please check the logs and try again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
