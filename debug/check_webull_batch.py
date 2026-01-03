"""Check if batch insert for RRSP Lance Webull has problematic values."""
import sys
from pathlib import Path
from datetime import datetime, date, time as dt_time
from decimal import Decimal
import math
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'web_dashboard') not in sys.path:
    sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
import pytz

def is_valid_for_json(value):
    """Check if value can be serialized to JSON."""
    if value is None:
        return True  # None is OK
    if isinstance(value, float):
        if math.isnan(value):
            return False
        if math.isinf(value):
            return False
    if isinstance(value, Decimal):
        return False  # Decimal needs conversion
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False

def main():
    fund_name = "RRSP Lance Webull"
    print(f"\n{'='*80}")
    print(f"CHECKING BATCH DATA FOR: {fund_name}")
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
    
    # Get trades and build positions (simplified)
    from collections import defaultdict
    
    trades_result = client.supabase.table("trade_log")\
        .select("*")\
        .eq("fund", fund_name)\
        .order("date")\
        .execute()
    
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
    
    print(f"Fund: {fund_name}")
    print(f"Base currency: {base_currency}")
    print(f"Positions: {len(current_holdings)}\n")
    
    # Create positions for multiple dates (like backfill does)
    test_dates = [date(2025, 12, 17), date(2025, 12, 18), date(2025, 12, 19)]
    exchange_rate = Decimal('1.35') if base_currency != 'USD' else Decimal('1.0')
    
    all_positions = []
    issues = []
    
    for target_date in test_dates:
        et_tz = pytz.timezone('America/New_York')
        et_datetime = et_tz.localize(datetime.combine(target_date, dt_time(16, 0)))
        utc_datetime = et_datetime.astimezone(pytz.UTC)
        
        for ticker, holding in current_holdings.items():
            shares = holding['shares']
            cost_basis = holding['cost']
            current_price = Decimal('100.0')  # Dummy price
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
            
            # Convert to float (like the job does)
            try:
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
                
                # Check each value
                for key, value in position.items():
                    if not is_valid_for_json(value):
                        issues.append(f"{ticker} {target_date} {key}: {value} (invalid)")
                    elif isinstance(value, float):
                        if math.isnan(value):
                            issues.append(f"{ticker} {target_date} {key}: NaN")
                        elif math.isinf(value):
                            issues.append(f"{ticker} {target_date} {key}: Infinity")
                
                all_positions.append(position)
            except Exception as e:
                issues.append(f"{ticker} {target_date}: Error creating position - {e}")
    
    print(f"Created {len(all_positions)} position records\n")
    
    if issues:
        print(f"FOUND {len(issues)} ISSUES:")
        for issue in issues[:20]:  # Show first 20
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("No JSON serialization issues found")
    
    # Try to serialize to JSON (like Supabase does)
    print(f"\n{'='*80}")
    print("TESTING JSON SERIALIZATION...")
    print(f"{'='*80}\n")
    
    try:
        json_str = json.dumps(all_positions)
        print(f"[OK] JSON serialization succeeded ({len(json_str)} bytes)")
    except Exception as e:
        print(f"[FAIL] JSON serialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Try a smaller batch (like chunking)
    print(f"\n{'='*80}")
    print("TESTING SMALLER BATCH (100 positions)...")
    print(f"{'='*80}\n")
    
    small_batch = all_positions[:100]
    try:
        json_str = json.dumps(small_batch)
        print(f"[OK] Small batch JSON serialization succeeded ({len(json_str)} bytes)")
        
        # Try actual insert
        print("\nTrying actual insert...")
        result = client.supabase.table("portfolio_positions")\
            .insert(small_batch)\
            .execute()
        print(f"[OK] Small batch insert succeeded!")
    except Exception as e:
        print(f"[FAIL] Small batch failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

