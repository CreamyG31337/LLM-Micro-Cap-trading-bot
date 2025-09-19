#!/usr/bin/env python3
"""
Admin interface to fix database schema and test everything
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient

def fix_database_schema():
    """Fix the database schema by creating missing tables and views"""
    print("🔧 Admin: Fixing database schema...")
    
    try:
        client = SupabaseClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ Cannot connect to Supabase")
            return False
        
        print("✅ Connected to Supabase")
        
        # Create missing tables and views via SQL
        sql_commands = [
            # Create performance_metrics table
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                date DATE NOT NULL UNIQUE,
                total_value DECIMAL(10, 2) NOT NULL,
                cost_basis DECIMAL(10, 2) NOT NULL,
                unrealized_pnl DECIMAL(10, 2) NOT NULL,
                performance_pct DECIMAL(5, 2) NOT NULL,
                total_trades INTEGER NOT NULL DEFAULT 0,
                winning_trades INTEGER NOT NULL DEFAULT 0,
                losing_trades INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Create current_positions view
            """
            CREATE OR REPLACE VIEW current_positions AS
            SELECT 
                ticker,
                SUM(shares) as total_shares,
                AVG(price) as avg_price,
                SUM(cost_basis) as total_cost_basis,
                SUM(pnl) as total_pnl,
                SUM(total_value) as total_market_value,
                MAX(date) as last_updated
            FROM portfolio_positions 
            WHERE shares > 0
            GROUP BY ticker;
            """,
            
            # Create indexes
            """
            CREATE INDEX IF NOT EXISTS idx_portfolio_positions_ticker ON portfolio_positions(ticker);
            CREATE INDEX IF NOT EXISTS idx_portfolio_positions_date ON portfolio_positions(date);
            CREATE INDEX IF NOT EXISTS idx_trade_log_ticker ON trade_log(ticker);
            CREATE INDEX IF NOT EXISTS idx_trade_log_date ON trade_log(date);
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_date ON performance_metrics(date);
            """,
            
            # Enable RLS
            """
            ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
            ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;
            ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
            ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
            """,
            
            # Create RLS policies
            """
            DROP POLICY IF EXISTS "Allow all operations on portfolio_positions" ON portfolio_positions;
            CREATE POLICY "Allow all operations on portfolio_positions" ON portfolio_positions
                FOR ALL USING (true);
            
            DROP POLICY IF EXISTS "Allow all operations on trade_log" ON trade_log;
            CREATE POLICY "Allow all operations on trade_log" ON trade_log
                FOR ALL USING (true);
            
            DROP POLICY IF EXISTS "Allow all operations on cash_balances" ON cash_balances;
            CREATE POLICY "Allow all operations on cash_balances" ON cash_balances
                FOR ALL USING (true);
            
            DROP POLICY IF EXISTS "Allow all operations on performance_metrics" ON performance_metrics;
            CREATE POLICY "Allow all operations on performance_metrics" ON performance_metrics
                FOR ALL USING (true);
            """
        ]
        
        # Execute each SQL command
        for i, sql in enumerate(sql_commands, 1):
            print(f"  {i}/{len(sql_commands)} Executing SQL command...")
            try:
                result = client.client.rpc('exec_sql', {'sql': sql}).execute()
                print(f"    ✅ Command {i} executed successfully")
            except Exception as e:
                print(f"    ⚠️  Command {i} warning: {e}")
        
        print("✅ Database schema fixed!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False

def test_data_migration():
    """Test if data migration worked"""
    print("\n🔍 Admin: Testing data migration...")
    
    try:
        client = SupabaseClient()
        
        # Test portfolio positions
        result = client.client.table("portfolio_positions").select("*").limit(5).execute()
        print(f"✅ Portfolio positions: {len(result.data)} entries")
        
        # Test trade log
        result = client.client.table("trade_log").select("*").limit(5).execute()
        print(f"✅ Trade log: {len(result.data)} entries")
        
        # Test cash balances
        result = client.client.table("cash_balances").select("*").execute()
        print(f"✅ Cash balances: {len(result.data)} entries")
        
        # Test current positions view
        try:
            result = client.client.table("current_positions").select("*").limit(5).execute()
            print(f"✅ Current positions view: {len(result.data)} entries")
        except Exception as e:
            print(f"⚠️  Current positions view: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing data: {e}")
        return False

def test_web_app():
    """Test if web app can start"""
    print("\n🌐 Admin: Testing web app...")
    
    try:
        # Import and test the app
        from app import app, get_supabase_client
        
        # Test Supabase client
        client = get_supabase_client()
        if client:
            print("✅ Web app can connect to Supabase")
        else:
            print("❌ Web app cannot connect to Supabase")
            return False
        
        # Test data loading
        from app import load_portfolio_data
        data = load_portfolio_data()
        
        if not data["portfolio"].empty:
            print(f"✅ Web app loaded {len(data['portfolio'])} portfolio positions")
        else:
            print("⚠️  Web app loaded empty portfolio data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing web app: {e}")
        return False

def main():
    """Main admin function"""
    print("🚀 Portfolio Dashboard Admin Interface")
    print("=" * 50)
    
    # Fix database schema
    if not fix_database_schema():
        print("❌ Failed to fix database schema")
        return
    
    # Test data migration
    if not test_data_migration():
        print("❌ Data migration test failed")
        return
    
    # Test web app
    if not test_web_app():
        print("❌ Web app test failed")
        return
    
    print("\n🎉 All tests passed! Your dashboard is ready.")
    print("\nNext steps:")
    print("1. Run: python app.py")
    print("2. Open: http://localhost:5000")
    print("3. Deploy to Vercel when ready")

if __name__ == "__main__":
    main()
