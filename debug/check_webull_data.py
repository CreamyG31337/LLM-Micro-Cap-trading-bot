"""Check what data is being generated for RRSP Lance Webull fund."""
import sys
from pathlib import Path
from datetime import datetime, date, time as dt_time
from decimal import Decimal
import math

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'web_dashboard') not in sys.path:
    sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
import pytz

def check_value(value, name):
    """Check if a value is valid for database insertion."""
    if value is None:
        return f"{name} is None"
    if isinstance(value, float):
        if math.isnan(value):
            return f"{name} is NaN"
        if math.isinf(value):
            return f"{name} is Infinity"
        if abs(value) > 1e15:
            return f"{name} is too large: {value}"
    if isinstance(value, Decimal):
        if value.is_nan():
            return f"{name} is NaN (Decimal)"
        if value.is_infinite():
            return f"{name} is Infinity (Decimal)"
    return None

def main():
    fund_name = "RRSP Lance Webull"
    print(f"\n{'='*80}")
    print(f"CHECKING DATA FOR: {fund_name}")
    print(f"{'='*80}\n")
    
    client = SupabaseClient(use_service_role=True)
    
    # Get fund info
    fund_result = client.supabase.table("funds")\
        .select("name, base_currency")\
        .eq("name", fund_name)\
        .execute()
    
    if not fund_result.data:
        print(f"[FAIL] Fund not found!")
        return
    
    fund = fund_result.data[0]
    base_currency = fund.get('base_currency', 'CAD')
    print(f"Fund: {fund_name}")
    print(f"Base currency: {base_currency}\n")
    
    # Get trades
    trades_result = client.supabase.table("trade_log")\
        .select("*")\
        .eq("fund", fund_name)\
        .order("date")\
        .execute()
    
    if not trades_result.data:
        print("[FAIL] No trades found!")
        return
    
    print(f"Found {len(trades_result.data)} trades\n")
    
    # Build positions like the job does
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
    
    print(f"Current holdings: {len(current_holdings)} positions\n")
    
    # Simulate creating position records for a test date
    test_date = date(2026, 1, 2)
    et_tz = pytz.timezone('America/New_York')
    et_datetime = et_tz.localize(datetime.combine(test_date, dt_time(16, 0)))
    utc_datetime = et_datetime.astimezone(pytz.UTC)
    
    # Get exchange rate (simplified - just use 1.35 for CAD)
    exchange_rate = Decimal('1.35') if base_currency != 'USD' else Decimal('1.0')
    
    print(f"Test date: {test_date}")
    print(f"Exchange rate: {exchange_rate}\n")
    
    # Create sample position records
    sample_positions = []
    issues_found = []
    
    for ticker, holding in list(current_holdings.items())[:20]:  # Check first 20
        shares = holding['shares']
        cost_basis = holding['cost']
        # Use dummy price for testing
        current_price = Decimal('100.0')
        market_value = shares * current_price
        unrealized_pnl = market_value - cost_basis
        
        position_currency = holding['currency']
        if position_currency == 'USD' and base_currency != 'USD':
            market_value_base = market_value * exchange_rate
            cost_basis_base = cost_basis * exchange_rate
            pnl_base = unrealized_pnl * exchange_rate
            conversion_rate = exchange_rate
        elif position_currency == base_currency:
            market_value_base = market_value
            cost_basis_base = cost_basis
            pnl_base = unrealized_pnl
            conversion_rate = Decimal('1.0')
        else:
            market_value_base = market_value
            cost_basis_base = cost_basis
            pnl_base = unrealized_pnl
            conversion_rate = Decimal('1.0')
        
        position = {
            'fund': fund_name,
            'ticker': ticker,
            'shares': float(shares),
            'price': float(current_price),
            'cost_basis': float(cost_basis),
            'pnl': float(unrealized_pnl),
            'currency': holding['currency'],
            'date': utc_datetime.isoformat(),
            'base_currency': base_currency,
            'total_value_base': float(market_value_base),
            'cost_basis_base': float(cost_basis_base),
            'pnl_base': float(pnl_base),
            'exchange_rate': float(conversion_rate)
        }
        
        # Check all values
        for key, value in position.items():
            issue = check_value(value, key)
            if issue:
                issues_found.append(f"{ticker}: {issue}")
        
        sample_positions.append(position)
    
    print(f"Created {len(sample_positions)} sample position records\n")
    
    if issues_found:
        print("ISSUES FOUND:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("No obvious data issues found in sample positions")
    
    # Try to insert one position
    print(f"\n{'='*80}")
    print("TESTING INSERT WITH ONE POSITION...")
    print(f"{'='*80}\n")
    
    if sample_positions:
        test_pos = sample_positions[0]
        print(f"Ticker: {test_pos['ticker']}")
        print(f"Fund: {test_pos['fund']}")
        print(f"Date: {test_pos['date']}")
        print(f"Shares: {test_pos['shares']}")
        print(f"Price: {test_pos['price']}")
        print(f"Cost basis: {test_pos['cost_basis']}")
        print(f"Currency: {test_pos['currency']}")
        print(f"Base currency: {test_pos['base_currency']}")
        print()
        
        try:
            result = client.supabase.table("portfolio_positions")\
                .insert(test_pos)\
                .execute()
            
            print("[OK] Single position insert succeeded!")
            
            # Clean up
            if result.data:
                test_id = result.data[0].get('id')
                if test_id:
                    client.supabase.table("portfolio_positions")\
                        .delete()\
                        .eq("id", test_id)\
                        .execute()
                    print("[OK] Test record cleaned up")
        except Exception as e:
            print(f"[FAIL] Single position insert failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

