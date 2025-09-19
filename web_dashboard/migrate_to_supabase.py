#!/usr/bin/env python3
"""
Migration script to move CSV data to Supabase
Run this once to migrate your existing trading data
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

def load_csv_data(data_dir: str = "../trading_data/funds/Project Chimera") -> dict:
    """Load data from CSV files"""
    data_dir = Path(data_dir)
    
    # Load portfolio data
    portfolio_file = data_dir / "llm_portfolio_update.csv"
    if portfolio_file.exists():
        portfolio_df = pd.read_csv(portfolio_file)
        portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'], format='mixed')
        logger.info(f"✅ Loaded portfolio data: {len(portfolio_df)} entries")
    else:
        portfolio_df = pd.DataFrame()
        logger.warning(f"⚠️  Portfolio file not found: {portfolio_file}")
    
    # Load trade log
    trade_file = data_dir / "llm_trade_log.csv"
    if trade_file.exists():
        trade_df = pd.read_csv(trade_file)
        trade_df['Date'] = pd.to_datetime(trade_df['Date'], format='mixed')
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

def migrate_data():
    """Migrate CSV data to Supabase"""
    logger.info("🚀 Starting data migration to Supabase...")
    
    # Check environment variables
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        logger.error("❌ SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
        logger.error("   Set them in your .env file or environment")
        return False
    
    try:
        # Initialize Supabase client
        client = SupabaseClient()
        
        # Test connection
        if not client.test_connection():
            logger.error("❌ Failed to connect to Supabase")
            return False
        
        # Load CSV data
        data = load_csv_data()
        
        # Migrate portfolio positions
        if not data["portfolio"].empty:
            logger.info("📊 Migrating portfolio positions...")
            if client.upsert_portfolio_positions(data["portfolio"]):
                logger.info("✅ Portfolio positions migrated successfully")
            else:
                logger.error("❌ Failed to migrate portfolio positions")
                return False
        else:
            logger.info("ℹ️  No portfolio data to migrate")
        
        # Migrate trade log
        if not data["trades"].empty:
            logger.info("📋 Migrating trade log...")
            if client.upsert_trade_log(data["trades"]):
                logger.info("✅ Trade log migrated successfully")
            else:
                logger.error("❌ Failed to migrate trade log")
                return False
        else:
            logger.info("ℹ️  No trade log data to migrate")
        
        # Migrate cash balances
        logger.info("💰 Migrating cash balances...")
        if client.upsert_cash_balances(data["cash_balances"]):
            logger.info("✅ Cash balances migrated successfully")
        else:
            logger.error("❌ Failed to migrate cash balances")
            return False
        
        # Verify migration
        logger.info("🔍 Verifying migration...")
        
        positions = client.get_current_positions()
        trades = client.get_trade_log(limit=10)
        balances = client.get_cash_balances()
        metrics = client.get_performance_metrics()
        
        logger.info(f"✅ Verification complete:")
        logger.info(f"   - Current positions: {len(positions)}")
        logger.info(f"   - Recent trades: {len(trades)}")
        logger.info(f"   - Cash balances: {balances}")
        logger.info(f"   - Total value: ${metrics['total_value']}")
        logger.info(f"   - Performance: {metrics['performance_pct']}%")
        
        logger.info("🎉 Data migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def create_env_template():
    """Create .env template file"""
    env_template = """# Supabase Configuration
# Get these values from your Supabase project settings
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Optional: Set to 'true' for debug logging
DEBUG=false
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_template)
        logger.info("📝 Created .env template file")
        logger.info("   Please fill in your Supabase credentials")
    else:
        logger.info("ℹ️  .env file already exists")

def main():
    """Main migration function"""
    print("🚀 Portfolio Data Migration to Supabase\n")
    
    # Create .env template if it doesn't exist
    create_env_template()
    
    # Check if .env file exists and has required variables
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found. Please create it with your Supabase credentials.")
        print("   See the .env template that was just created.")
        return False
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("⚠️  python-dotenv not installed. Install it with: pip install python-dotenv")
        logger.info("   Or set environment variables manually")
    
    # Run migration
    success = migrate_data()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("   Your data is now stored securely in Supabase")
        print("   You can now deploy to Vercel without exposing CSV files")
    else:
        print("\n❌ Migration failed. Please check the logs and try again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
