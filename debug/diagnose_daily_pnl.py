"""Diagnose why daily P&L is $0.00 on Dec 23"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import get_supabase_client

def main():
    client = get_supabase_client()
    if not client:
        print("Failed to connect to database")
        return
    
    fund = "Project Chimera"
    
    # Get latest 5 dates with position data
    print(f"\n=== Latest position dates for {fund} ===")
    result = client.supabase.table('portfolio_positions')\
        .select('date')\
        .eq('fund', fund)\
        .order('date', desc=True)\
        .limit(100)\
        .execute()
    
    if not result.data:
        print("No positions found!")
        return
    
    # Get unique dates
    dates = sorted(set([row['date'] for row in result.data]), reverse=True)[:7]
    print(f"Last 7 position dates: {dates}")
    
    latest_date = dates[0]
    print(f"\nLatest position date: {latest_date}")
    
    # Check if there's a gap
    if len(dates) > 1:
        second_latest = dates[1]
        print(f"Previous position date: {second_latest}")
        
        # Check gap
        from datetime import datetime
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        second_dt = datetime.strptime(second_latest, '%Y-%m-%d')
        gap = (latest_dt - second_dt).days
        print(f"Gap between latest two dates: {gap} days")
        
        if gap > 1:
            print(f"WARNING: Gap of {gap} days - this will cause daily_pnl to be NULL!")
    
    # Check what latest_positions view returns for daily_pnl
    print(f"\n=== Checking latest_positions view ===")
    lp_result = client.supabase.table('latest_positions')\
        .select('ticker, date, current_price, yesterday_price, yesterday_date, daily_pnl')\
        .eq('fund', fund)\
        .limit(5)\
        .execute()
    
    if lp_result.data:
        for row in lp_result.data:
            ticker = row.get('ticker')
            date = row.get('date')
            current = row.get('current_price')
            yesterday = row.get('yesterday_price')
            yesterday_date = row.get('yesterday_date')
            dpnl = row.get('daily_pnl')
            
            print(f"{ticker}: date={date}, current=${current}, yesterday=${yesterday} (from {yesterday_date}), daily_pnl=${dpnl}")
            
            if yesterday is None:
                print(f"  ^ NULL yesterday_price - this is why daily_pnl is NULL/0!")
    else:
        print("No data from latest_positions view")
    
    # Check total daily P&L
    print(f"\n=== Total Daily P&L ===")
    total_pnl = sum([row.get('daily_pnl', 0) or 0 for row in lp_result.data])
    print(f"Sum of daily_pnl for first 5 positions: ${total_pnl:.2f}")
    
    if total_pnl == 0:
        print("\nCONCLUSION: daily_pnl is 0 or NULL because:")
        print("1. Yesterday's position data doesn't exist in the database")
        print("2. The latest_positions view can't find 'yesterday_price'")
        print("3. Without yesterday_price, daily_pnl = NULL, which displays as $0.00")
        print(f"\nSOLUTION: Ensure portfolio positions exist for {dates[1] if len(dates) > 1 else 'the day before ' + latest_date}")

if __name__ == '__main__':
    main()
