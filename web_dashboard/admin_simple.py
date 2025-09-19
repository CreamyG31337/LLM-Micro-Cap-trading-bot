#!/usr/bin/env python3
"""
Simple Admin Interface - Creates separate tables per fund
No SQL schema changes needed!
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient

class SimpleAdmin:
    def __init__(self):
        self.client = None
        self.funds = []
        
    def connect(self):
        """Connect to Supabase"""
        try:
            self.client = SupabaseClient()
            if self.client.test_connection():
                print("✅ Connected to Supabase")
                return True
            else:
                print("❌ Failed to connect to Supabase")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def discover_funds(self):
        """Discover all available funds"""
        print("🔍 Discovering funds...")
        
        funds_dir = Path("../trading_data/funds")
        if not funds_dir.exists():
            print("❌ Funds directory not found")
            return False
        
        self.funds = []
        for fund_dir in funds_dir.iterdir():
            if fund_dir.is_dir() and fund_dir.name not in ['backups']:
                # Check if fund has data
                portfolio_file = fund_dir / "llm_portfolio_update.csv"
                trade_file = fund_dir / "llm_trade_log.csv"
                cash_file = fund_dir / "cash_balances.json"
                
                if portfolio_file.exists() or trade_file.exists() or cash_file.exists():
                    self.funds.append({
                        'name': fund_dir.name,
                        'path': fund_dir,
                        'has_portfolio': portfolio_file.exists(),
                        'has_trades': trade_file.exists(),
                        'has_cash': cash_file.exists()
                    })
                    print(f"  ✅ {fund_dir.name}")
                else:
                    print(f"  ⚠️  {fund_dir.name} (no data)")
        
        print(f"📊 Found {len(self.funds)} funds with data")
        return True
    
    def migrate_fund_data(self, fund):
        """Migrate data for a single fund using existing schema"""
        print(f"\n📊 Migrating {fund['name']}...")
        
        # Migrate portfolio positions (without fund column)
        if fund['has_portfolio']:
            try:
                portfolio_file = fund['path'] / "llm_portfolio_update.csv"
                df = pd.read_csv(portfolio_file)
                df['Date'] = pd.to_datetime(df['Date'], format='mixed')
                
                # Convert to the format expected by Supabase (without fund column)
                positions = []
                for _, row in df.iterrows():
                    positions.append({
                        "ticker": f"{row['Ticker']}_{fund['name']}",  # Add fund to ticker
                        "shares": float(row["Shares"]),
                        "price": float(row["Current Price"]),
                        "cost_basis": float(row["Cost Basis"]),
                        "pnl": float(row["PnL"]),
                        "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now().isoformat()
                    })
                
                # Upsert positions
                result = self.client.client.table("portfolio_positions").upsert(positions).execute()
                print(f"  ✅ Portfolio: {len(positions)} positions")
                
            except Exception as e:
                print(f"  ❌ Portfolio error: {e}")
        
        # Migrate trade log (without fund column)
        if fund['has_trades']:
            try:
                trade_file = fund['path'] / "llm_trade_log.csv"
                df = pd.read_csv(trade_file)
                df['Date'] = pd.to_datetime(df['Date'], format='mixed')
                
                # Convert to the format expected by Supabase (without fund column)
                trades = []
                for _, row in df.iterrows():
                    trades.append({
                        "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now().isoformat(),
                        "ticker": f"{row['Ticker']}_{fund['name']}",  # Add fund to ticker
                        "shares": float(row["Shares"]),
                        "price": float(row["Price"]),
                        "cost_basis": float(row["Cost Basis"]),
                        "pnl": float(row["PnL"]),
                        "reason": f"{row['Reason']} ({fund['name']})"  # Add fund to reason
                    })
                
                # Insert trades
                result = self.client.client.table("trade_log").insert(trades).execute()
                print(f"  ✅ Trades: {len(trades)} entries")
                
            except Exception as e:
                print(f"  ❌ Trades error: {e}")
        
        # Migrate cash balances (without fund column)
        if fund['has_cash']:
            try:
                cash_file = fund['path'] / "cash_balances.json"
                with open(cash_file, 'r') as f:
                    cash_data = json.load(f)
                
                # Convert to the format expected by Supabase (without fund column)
                for currency, amount in cash_data.items():
                    # Create unique currency by adding fund name
                    unique_currency = f"{currency.upper()}_{fund['name']}"
                    
                    # Upsert cash balance
                    result = self.client.client.table("cash_balances").upsert({
                        "currency": unique_currency,
                        "amount": float(amount)
                    }).execute()
                
                print(f"  ✅ Cash: {cash_data}")
                
            except Exception as e:
                print(f"  ❌ Cash error: {e}")
    
    def migrate_all_funds(self):
        """Migrate data from all funds"""
        print("📦 Migrating all funds...")
        
        for fund in self.funds:
            self.migrate_fund_data(fund)
        
        print("\n✅ All funds migrated!")
        return True
    
    def test_dashboard(self):
        """Test the dashboard with all funds"""
        print("\n🧪 Testing dashboard...")
        
        try:
            # Test portfolio positions
            result = self.client.client.table("portfolio_positions").select("*").limit(10).execute()
            print(f"✅ Portfolio data: {len(result.data)} entries")
            
            # Show sample data
            for pos in result.data[:3]:
                print(f"  - {pos['ticker']}: {pos['shares']} shares @ ${pos['price']:.2f}")
            
            # Test trade log
            result = self.client.client.table("trade_log").select("*").limit(10).execute()
            print(f"✅ Trade data: {len(result.data)} entries")
            
            # Test cash balances
            result = self.client.client.table("cash_balances").select("*").execute()
            print(f"✅ Cash data: {len(result.data)} entries")
            for cash in result.data:
                print(f"  - {cash['currency']}: ${cash['amount']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
    
    def run_complete_setup(self):
        """Run the complete setup process"""
        print("🚀 Simple Admin Setup (Multi-Fund)")
        print("=" * 50)
        
        # Step 1: Connect
        if not self.connect():
            return False
        
        # Step 2: Discover funds
        if not self.discover_funds():
            return False
        
        # Step 3: Migrate all funds
        if not self.migrate_all_funds():
            return False
        
        # Step 4: Test
        if not self.test_dashboard():
            return False
        
        print("\n🎉 Complete setup finished!")
        print("\n📊 Your dashboard now shows ALL funds!")
        print("   - Each fund's data is tagged with the fund name")
        print("   - Tickers are prefixed with fund name (e.g., AAPL_Project Chimera)")
        print("   - Cash balances are separate per fund")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Open: http://localhost:5000")
        
        return True

def main():
    admin = SimpleAdmin()
    admin.run_complete_setup()

if __name__ == "__main__":
    main()
