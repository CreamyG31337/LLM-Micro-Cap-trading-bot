#!/usr/bin/env python3
"""
Update database schema to support multiple funds
"""

import os
from dotenv import load_dotenv
from supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

def update_schema_for_multi_fund():
    """Add fund column to existing tables"""
    print("🔧 Updating schema for multiple funds...")
    
    try:
        client = SupabaseClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ Cannot connect to Supabase")
            return False
        
        print("✅ Connected to Supabase")
        
        # SQL commands to add fund column to existing tables
        sql_commands = [
            # Add fund column to portfolio_positions
            """
            ALTER TABLE portfolio_positions 
            ADD COLUMN IF NOT EXISTS fund VARCHAR(50) DEFAULT 'Project Chimera';
            """,
            
            # Add fund column to trade_log
            """
            ALTER TABLE trade_log 
            ADD COLUMN IF NOT EXISTS fund VARCHAR(50) DEFAULT 'Project Chimera';
            """,
            
            # Add fund column to cash_balances
            """
            ALTER TABLE cash_balances 
            ADD COLUMN IF NOT EXISTS fund VARCHAR(50) DEFAULT 'Project Chimera';
            """,
            
            # Add fund column to performance_metrics
            """
            ALTER TABLE performance_metrics 
            ADD COLUMN IF NOT EXISTS fund VARCHAR(50) DEFAULT 'Project Chimera';
            """,
            
            # Update the current_positions view to include fund
            """
            CREATE OR REPLACE VIEW current_positions AS
            SELECT 
                fund,
                ticker,
                SUM(shares) as total_shares,
                AVG(price) as avg_price,
                SUM(cost_basis) as total_cost_basis,
                SUM(pnl) as total_pnl,
                SUM(total_value) as total_market_value,
                MAX(date) as last_updated
            FROM portfolio_positions 
            WHERE shares > 0
            GROUP BY fund, ticker;
            """,
            
            # Create indexes for fund column
            """
            CREATE INDEX IF NOT EXISTS idx_portfolio_positions_fund ON portfolio_positions(fund);
            CREATE INDEX IF NOT EXISTS idx_trade_log_fund ON trade_log(fund);
            CREATE INDEX IF NOT EXISTS idx_cash_balances_fund ON cash_balances(fund);
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_fund ON performance_metrics(fund);
            """
        ]
        
        print("📝 Executing schema updates...")
        print("⚠️  Note: You'll need to run these SQL commands manually in Supabase SQL Editor:")
        print()
        
        for i, sql in enumerate(sql_commands, 1):
            print(f"-- Command {i}:")
            print(sql)
            print()
        
        print("📋 Manual steps:")
        print("1. Go to https://supabase.com/dashboard/project/injqbxdqyxfvannygadt")
        print("2. Click 'SQL Editor' → 'New query'")
        print("3. Copy and paste each SQL command above")
        print("4. Click 'Run' for each command")
        print("5. Then run: python migrate_all_funds.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    update_schema_for_multi_fund()
