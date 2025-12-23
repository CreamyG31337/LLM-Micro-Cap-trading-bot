"""Check NAV calculation for September 7-8, 2025"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from portfolio.supabase_client import SupabaseClient

def main():
    client = SupabaseClient()
    supabase = client.get_client()
    
    fund = "Project Chimera"
    
    # Check portfolio positions for Sept 7-8
    print("\n=== Portfolio Positions Sept 7-8 ===")
    positions = supabase.table('portfolio_positions')\
        .select('*')\
        .eq('fund', fund)\
        .gte('date', '2025-09-07')\
        .lte('date', '2025-09-08')\
        .order('date')\
        .execute()
    
    for pos in positions.data:
        print(f"{pos['date']}: {pos['ticker']} - {pos['shares']} shares @ ${pos['price']:.2f} = ${pos['value']:.2f}")
    
    # Check total value by date
    print("\n=== Total Portfolio Value by Date ===")
    dates = ['2025-09-07', '2025-09-08']
    for date in dates:
        day_positions = [p for p in positions.data if p['date'] == date]
        total_value = sum(p['value'] for p in day_positions)
        print(f"{date}: ${total_value:.2f} ({len(day_positions)} positions)")
    
    # Check contributions
    print("\n=== Contributions Sept 7-8 ===")
    contribs = supabase.table('fund_contributions')\
        .select('*')\
        .eq('fund', fund)\
        .gte('timestamp', '2025-09-07')\
        .lt('timestamp', '2025-09-09')\
        .order('timestamp')\
        .execute()
    
    for c in contribs.data:
        date = c['timestamp'][:10]
        print(f"{date} {c['timestamp'][11:19]}: {c['contributor']} - ${c['amount']}")
    
    # Calculate expected NAV for Day 2
    print("\n=== NAV Analysis ===")
    day1_total = sum(p['value'] for p in positions.data if p['date'] == '2025-09-07')
    day2_total = sum(p['value'] for p in positions.data if p['date'] == '2025-09-08')
    
    day1_contribs = [c for c in contribs.data if c['timestamp'].startswith('2025-09-07')]
    day1_contrib_total = sum(c['amount'] for c in day1_contribs)
    
    print(f"Day 1 (2025-09-07):")
    print(f"  Contributions: ${day1_contrib_total:.2f}")
    print(f"  Portfolio Value: ${day1_total:.2f}")
    print(f"  Expected units issued: {day1_contrib_total / 1.0:.2f} (at NAV=1.0)")
    
    if day1_total > 0:
        print(f"\nDay 2 (2025-09-08):")
        print(f"  Portfolio Value: ${day2_total:.2f}")
        print(f"  WRONG: Using same-day NAV = ${day2_total / day1_contrib_total:.4f}")
        print(f"  CORRECT: Should use prev-day NAV = ${day1_total / day1_contrib_total:.4f}")
    else:
        print(f"\nDay 1 has NO portfolio data - this is the issue!")
        print(f"Day 2 contributions are using same-day NAV which is inflated")

if __name__ == '__main__':
    main()
