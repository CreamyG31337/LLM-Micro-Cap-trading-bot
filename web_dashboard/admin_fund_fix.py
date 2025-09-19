#!/usr/bin/env python3
"""
Fix multi-fund support with proper ticker abbreviations
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

class FundFixer:
    def __init__(self):
        self.client = None
        # Map fund names to short abbreviations
        self.fund_abbrevs = {
            'Project Chimera': 'PC',
            'RRSP Lance Webull': 'RLW',
            'TEST': 'TEST',
            'TFSA': 'TFSA',
            'RRSP': 'RRSP'
        }

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

    def clear_existing_data(self):
        """Clear existing data to start fresh"""
        print("🧹 Clearing existing data...")
        try:
            # Clear all tables
            self.client.client.table("portfolio_positions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            self.client.client.table("trade_log").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            self.client.client.table("cash_balances").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print("✅ Existing data cleared")
            return True
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
            return False

    def discover_funds(self):
        """Discover all available funds"""
        print("🔍 Discovering funds...")
        funds_dir = Path("../trading_data/funds")
        self.funds = []

        if not funds_dir.exists():
            print("❌ Funds directory not found")
            return False

        for fund_dir in funds_dir.iterdir():
            if fund_dir.is_dir() and fund_dir.name not in ['backups']:
                # Check if fund has data
                portfolio_file = fund_dir / "llm_portfolio_update.csv"
                trade_file = fund_dir / "llm_trade_log.csv"
                cash_file = fund_dir / "cash_balances.json"

                if portfolio_file.exists() or trade_file.exists() or cash_file.exists():
                    fund_abbrev = self.fund_abbrevs.get(fund_dir.name, fund_dir.name[:3].upper())
                    self.funds.append({
                        'name': fund_dir.name,
                        'abbrev': fund_abbrev,
                        'path': fund_dir,
                        'has_portfolio': portfolio_file.exists(),
                        'has_trades': trade_file.exists(),
                        'has_cash': cash_file.exists()
                    })
                    print(f"  ✅ {fund_dir.name} → {fund_abbrev}")
                else:
                    print(f"  ⚠️  {fund_dir.name} (no data)")

        print(f"📊 Found {len(self.funds)} funds with data")
        return True

    def migrate_fund_data(self, fund):
        """Migrate data for a single fund using abbreviations"""
        print(f"\n📊 Migrating {fund['name']} ({fund['abbrev']})...")

        # Migrate portfolio positions
        if fund['has_portfolio']:
            try:
                portfolio_file = fund['path'] / "llm_portfolio_update.csv"
                df = pd.read_csv(portfolio_file)
                df['Date'] = pd.to_datetime(df['Date'], format='mixed')

                # Convert to the format expected by Supabase with abbreviated fund name
                positions = []
                for _, row in df.iterrows():
                    # Create ticker with abbreviation: AAPL_PC
                    ticker_with_fund = f"{row['Ticker']}_{fund['abbrev']}"
                    positions.append({
                        "ticker": ticker_with_fund,
                        "shares": float(row["Shares"]),
                        "price": float(row["Current Price"]),
                        "cost_basis": float(row["Cost Basis"]),
                        "pnl": float(row["PnL"]),
                        "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now().isoformat()
                    })

                # Upsert positions
                result = self.client.client.table("portfolio_positions").upsert(positions).execute()
                print(f"  ✅ Portfolio: {len(positions)} positions")
                # Show sample
                for pos in positions[:2]:
                    print(f"    - {pos['ticker']}: {pos['shares']} shares")

            except Exception as e:
                print(f"  ❌ Portfolio error: {e}")

        # Migrate trade log
        if fund['has_trades']:
            try:
                trade_file = fund['path'] / "llm_trade_log.csv"
                df = pd.read_csv(trade_file)
                df['Date'] = pd.to_datetime(df['Date'], format='mixed')

                # Convert to the format expected by Supabase with abbreviated fund name
                trades = []
                for _, row in df.iterrows():
                    # Create ticker with abbreviation
                    ticker_with_fund = f"{row['Ticker']}_{fund['abbrev']}"
                    trades.append({
                        "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now().isoformat(),
                        "ticker": ticker_with_fund,
                        "shares": float(row["Shares"]),
                        "price": float(row["Price"]),
                        "cost_basis": float(row["Cost Basis"]),
                        "pnl": float(row["PnL"]),
                        "reason": f"{row['Reason']} ({fund['name']})"
                    })

                # Insert trades
                result = self.client.client.table("trade_log").insert(trades).execute()
                print(f"  ✅ Trades: {len(trades)} entries")

            except Exception as e:
                print(f"  ❌ Trades error: {e}")

        # Migrate cash balances
        if fund['has_cash']:
            try:
                cash_file = fund['path'] / "cash_balances.json"
                with open(cash_file, 'r') as f:
                    cash_data = json.load(f)

                # Convert to the format expected by Supabase with abbreviated fund name
                for currency, amount in cash_data.items():
                    # Create currency with abbreviation: CAD_PC
                    currency_with_fund = f"{currency.upper()}_{fund['abbrev']}"

                    # Upsert cash balance
                    result = self.client.client.table("cash_balances").upsert({
                        "currency": currency_with_fund,
                        "amount": float(amount)
                    }).execute()

                print(f"  ✅ Cash: {cash_data}")

            except Exception as e:
                print(f"  ❌ Cash error: {e}")

    def migrate_all_funds(self):
        """Migrate data from all funds"""
        print("📦 Migrating all funds with abbreviations...")

        for fund in self.funds:
            self.migrate_fund_data(fund)

        print("\n✅ All funds migrated with abbreviations!")
        return True

    def test_dashboard(self):
        """Test the dashboard with all funds"""
        print("\n🧪 Testing dashboard...")

        try:
            # Test portfolio positions
            result = self.client.client.table("portfolio_positions").select("*").limit(10).execute()
            print(f"✅ Portfolio data: {len(result.data)} entries")

            # Show sample with fund abbreviations
            for pos in result.data[:5]:
                ticker_parts = pos['ticker'].rsplit('_', 1)
                if len(ticker_parts) == 2:
                    ticker, fund_abbrev = ticker_parts
                    fund_name = [f['name'] for f in self.funds if f['abbrev'] == fund_abbrev][0]
                    print(f"  - {ticker} ({fund_name}): {pos['shares']} shares @ ${pos['price']:.2f}")
                else:
                    print(f"  - {pos['ticker']}: {pos['shares']} shares @ ${pos['price']:.2f}")

            # Test trade log
            result = self.client.client.table("trade_log").select("*").limit(10).execute()
            print(f"✅ Trade data: {len(result.data)} entries")

            # Test cash balances
            result = self.client.client.table("cash_balances").select("*").execute()
            print(f"✅ Cash data: {len(result.data)} entries")
            for cash in result:
                currency_parts = cash['currency'].rsplit('_', 1)
                if len(currency_parts) == 2:
                    currency, fund_abbrev = currency_parts
                    fund_name = [f['name'] for f in self.funds if f['abbrev'] == fund_abbrev][0]
                    print(f"  - {currency} ({fund_name}): ${cash['amount']}")

            return True

        except Exception as e:
            print(f"❌ Test error: {e}")
            return False

    def run_complete_fix(self):
        """Run the complete fix process"""
        print("🔧 Multi-Fund Fix with Abbreviations")
        print("=" * 50)

        # Step 1: Connect
        if not self.connect():
            return False

        # Step 2: Clear existing data
        if not self.clear_existing_data():
            return False

        # Step 3: Discover funds
        if not self.discover_funds():
            return False

        # Step 4: Migrate all funds with abbreviations
        if not self.migrate_all_funds():
            return False

        # Step 5: Test
        if not self.test_dashboard():
            return False

        print("\n🎉 Multi-fund fix completed!")
        print("\n📊 Fund abbreviations used:")
        for fund in self.funds:
            print(f"  - {fund['name']} → {fund['abbrev']}")

        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Open: http://localhost:5000")
        print("3. Your dashboard now shows ALL funds with short ticker names!")

        return True

def main():
    fixer = FundFixer()
    fixer.run_complete_fix()

if __name__ == "__main__":
    main()
