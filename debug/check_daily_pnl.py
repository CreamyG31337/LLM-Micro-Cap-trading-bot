"""Check why daily_pnl is showing $0.00"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import get_supabase_client

def main():
    client = get_supabase_client()
    if not client:
        print("❌ Failed to connect to database")
        return
    
    # Get latest positions for Project Chimera
    print("\n=== Checking latest_positions view ===")
    result = client.supabase.table('latest_positions')\
        .select('*')\
        .eq('fund', 'Project Chimera')\
        .limit(5)\
        .execute()
    
    if not result.data:
        print("❌ No positions found in latest_positions view")
        return
    
    print(f"✅ Found {len(result.data)} positions")
    
    # Check columns
    first_row = result.data[0]
    print(f"\n📋 Columns in latest_positions: {list(first_row.keys())}")
    
    # Check if daily_pnl exists
    if 'daily_pnl' in first_row:
        daily_pnls = [row.get('daily_pnl') for row in result.data]
        print(f"\n✅ daily_pnl column exists")
        print(f"   Values: {daily_pnls}")
        print(f"   Sum: {sum([v for v in daily_pnls if v is not None])}")
    else:
        print(f"\n❌ daily_pnl column MISSING from latest_positions view!")
        print(f"   Available columns: {list(first_row.keys())}")
    
    # Check if there's portfolio_positions data for today
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n=== Checking portfolio_positions for recent dates ===")
    for date in [today, yesterday]:
        pos = client.supabase.table('portfolio_positions')\
            .select('date, ticker, value')\
            .eq('fund', 'Project Chimera')\
            .eq('date', date)\
            .limit(5)\
            .execute()
        
        if pos.data:
            total_value = sum(p['value'] for p in pos.data)
            print(f"✅ {date}: {len(pos.data)} positions, total value: ${total_value:,.2f}")
        else:
            print(f"⚠️  {date}: No positions found (market closed or no data)")

if __name__ == '__main__':
    main()
