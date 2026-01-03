"""Investigate the RRSP Lance Webull fund error."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'web_dashboard') not in sys.path:
    sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
from utils.market_holidays import MarketHolidays
from decimal import Decimal

def main():
    fund_name = "RRSP Lance Webull"
    print(f"\n{'='*80}")
    print(f"INVESTIGATING: {fund_name} - Bad Request Error")
    print(f"{'='*80}\n")
    
    client = SupabaseClient(use_service_role=True)
    market_holidays = MarketHolidays()
    
    # 1. Check fund exists and is production
    print("1. Checking fund status...")
    try:
        fund_result = client.supabase.table("funds")\
            .select("name, is_production, base_currency")\
            .eq("name", fund_name)\
            .execute()
        
        if not fund_result.data:
            print(f"   [FAIL] Fund '{fund_name}' NOT FOUND!")
            return
        
        fund = fund_result.data[0]
        print(f"   [OK] Fund found: {fund_name}")
        print(f"   Production: {fund.get('is_production', False)}")
        print(f"   Base currency: {fund.get('base_currency', 'CAD')}")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return
    
    # 2. Check trades
    print(f"\n2. Checking trades...")
    try:
        trades_result = client.supabase.table("trade_log")\
            .select("*")\
            .eq("fund", fund_name)\
            .order("date")\
            .execute()
        
        if not trades_result.data:
            print(f"   [WARNING] No trades found!")
            return
        
        print(f"   [OK] Found {len(trades_result.data)} trades")
        
        # Check for problematic data
        print(f"\n   Checking for problematic trade data...")
        for i, trade in enumerate(trades_result.data[:10]):  # Check first 10
            ticker = trade.get('ticker', '')
            shares = trade.get('shares')
            price = trade.get('price')
            currency = trade.get('currency')
            date_val = trade.get('date')
            
            issues = []
            if shares is None:
                issues.append("shares is None")
            elif not isinstance(shares, (int, float)):
                issues.append(f"shares is {type(shares)}: {shares}")
            
            if price is None:
                issues.append("price is None")
            elif not isinstance(price, (int, float)):
                issues.append(f"price is {type(price)}: {price}")
            
            if currency and not isinstance(currency, str):
                issues.append(f"currency is {type(currency)}: {currency}")
            
            if issues:
                print(f"      Trade {i+1} ({ticker}): {', '.join(issues)}")
        
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Try to simulate what the job does - build positions
    print(f"\n3. Simulating position building...")
    try:
        from collections import defaultdict
        
        running_positions = defaultdict(lambda: {
            'shares': Decimal('0'),
            'cost': Decimal('0'),
            'currency': 'USD'
        })
        
        for trade in trades_result.data:
            ticker = trade['ticker']
            shares = Decimal(str(trade.get('shares', 0) or 0))
            price = Decimal(str(trade.get('price', 0) or 0))
            cost = shares * price
            reason = str(trade.get('reason', '')).upper()
            
            if 'SELL' in reason:
                if running_positions[ticker]['shares'] > 0:
                    cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                    running_positions[ticker]['shares'] -= shares
                    running_positions[ticker]['cost'] -= shares * cost_per_share
            else:
                running_positions[ticker]['shares'] += shares
                running_positions[ticker]['cost'] += cost
                currency = trade.get('currency', 'USD')
                if currency and isinstance(currency, str):
                    currency_upper = currency.strip().upper()
                    if currency_upper and currency_upper not in ('NAN', 'NONE', 'NULL', ''):
                        running_positions[ticker]['currency'] = currency_upper
        
        current_holdings = {
            ticker: pos for ticker, pos in running_positions.items()
            if pos['shares'] > 0
        }
        
        print(f"   [OK] Built {len(current_holdings)} positions")
        
        # Check for problematic values
        print(f"\n   Checking position values...")
        for ticker, holding in list(current_holdings.items())[:10]:
            shares = holding['shares']
            cost = holding['cost']
            currency = holding['currency']
            
            issues = []
            if shares.is_nan() or shares.is_infinite():
                issues.append(f"shares is {shares}")
            if cost.is_nan() or cost.is_infinite():
                issues.append(f"cost is {cost}")
            if not isinstance(currency, str):
                issues.append(f"currency is {type(currency)}")
            
            if issues:
                print(f"      {ticker}: {', '.join(issues)}")
            else:
                print(f"      {ticker}: OK (shares={shares}, cost={cost}, currency={currency})")
        
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Try to create a test position record
    print(f"\n4. Testing position record creation...")
    try:
        test_date = date(2026, 1, 2)
        et_tz = __import__('pytz').timezone('America/New_York')
        et_datetime = et_tz.localize(datetime.combine(test_date, datetime.min.time().replace(hour=16)))
        utc_datetime = et_datetime.astimezone(__import__('pytz').UTC)
        
        # Try to create a minimal test record
        test_record = {
            'fund': fund_name,
            'ticker': 'TEST',
            'shares': 1.0,
            'price': 100.0,
            'cost_basis': 100.0,
            'pnl': 0.0,
            'currency': 'USD',
            'date': utc_datetime.isoformat(),
            'base_currency': fund.get('base_currency', 'CAD'),
            'total_value_base': 100.0,
            'cost_basis_base': 100.0,
            'pnl_base': 0.0,
            'exchange_rate': 1.0
        }
        
        print(f"   Testing insert with minimal record...")
        result = client.supabase.table("portfolio_positions")\
            .insert(test_record)\
            .execute()
        
        print(f"   [OK] Test insert succeeded!")
        
        # Clean up test record
        if result.data:
            test_id = result.data[0].get('id')
            if test_id:
                client.supabase.table("portfolio_positions")\
                    .delete()\
                    .eq("id", test_id)\
                    .execute()
                print(f"   [OK] Test record cleaned up")
        
    except Exception as e:
        print(f"   [FAIL] Test insert failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Check existing portfolio positions for this fund
    print(f"\n5. Checking existing portfolio positions...")
    try:
        positions_result = client.supabase.table("portfolio_positions")\
            .select("*")\
            .eq("fund", fund_name)\
            .order("date", desc=True)\
            .limit(5)\
            .execute()
        
        if positions_result.data:
            print(f"   [OK] Found {len(positions_result.data)} recent positions")
            print(f"   Checking for problematic values...")
            
            for pos in positions_result.data:
                issues = []
                for key, value in pos.items():
                    if value is None and key not in ['company']:  # company can be None
                        issues.append(f"{key} is None")
                    elif isinstance(value, float):
                        if pd.isna(value):
                            issues.append(f"{key} is NaN")
                        elif not (-1e10 < value < 1e10):  # Reasonable range
                            issues.append(f"{key} is {value} (out of range)")
                
                if issues:
                    print(f"      Position {pos.get('id')}: {', '.join(issues)}")
        else:
            print(f"   [INFO] No existing positions found")
            
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

