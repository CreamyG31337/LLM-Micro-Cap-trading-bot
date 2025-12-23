import os
import sys
import pandas as pd
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_date_gaps():
    client = SupabaseClient()
    
    # Get all unique dates
    response = client.supabase.table("portfolio_positions") \
        .select("date") \
        .eq("fund", "Project Chimera") \
        .execute()
    
    df = pd.DataFrame(response.data)
    df['date'] = pd.to_datetime(df['date'])
    unique_dates = sorted(df['date'].dt.date.unique())
    
    print(f"Total unique dates: {len(unique_dates)}")
    print(f"Date range: {unique_dates[0]} to {unique_dates[-1]}")
    
    # Find gaps
    print("\n=== DATE GAPS ===")
    current = unique_dates[0]
    end = unique_dates[-1]
    
    gaps = []
    while current < end:
        next_day = current + timedelta(days=1)
        if next_day not in unique_dates:
            # Start of a gap
            gap_start = next_day
            while next_day not in unique_dates and next_day <= end:
                next_day += timedelta(days=1)
            gap_end = next_day - timedelta(days=1)
            gap_days = (gap_end - gap_start).days + 1
            gaps.append((gap_start, gap_end, gap_days))
            current = next_day
        else:
            current = next_day
    
    if gaps:
        print(f"\nFound {len(gaps)} gaps:")
        for gap_start, gap_end, days in gaps:
            if days > 5:  # Only show significant gaps
                print(f"  {gap_start} to {gap_end}: {days} days missing")
    
    # Show recent dates
    print(f"\n=== RECENT 15 DATES ===")
    for d in unique_dates[-15:]:
        print(f"  {d}")

if __name__ == "__main__":
    check_date_gaps()
