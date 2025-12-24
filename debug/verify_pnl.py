
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.supabase_client import SupabaseClient

def verify_pnl():
    client = SupabaseClient()
    
    # Query latest positions for RRSP Lance Webull
    query = """
    SELECT 
        ticker,
        date,
        shares,
        current_price,
        yesterday_price,
        daily_pnl,
        daily_pnl_pct
    FROM latest_positions
    WHERE fund = 'RRSP Lance Webull'
    ORDER BY market_value DESC
    LIMIT 10;
    """
    
    try:
        print(f"Checking latest dates for ALL funds...")
        # We can't easily do a GROUP BY via the simple client without RPC, 
        # so we'll fetch distinct fund names first or just fetch recent rows and aggregate in Python
        # Fetching latest 1000 rows should give us a good sample of recent activity
        response = client.supabase.table('portfolio_positions') \
            .select('fund,date') \
            .order('date', desc=True) \
            .limit(2000) \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            # Find max date per fund
            latest_dates = df.groupby('fund')['date'].max()
            print("\nLatest Data by Fund:")
            print(latest_dates)
            
            # Check specifically for today (2025-12-23)
            today_str = '2025-12-23'
            for fund, date_str in latest_dates.items():
                if today_str in date_str:
                    print(f"✅ {fund}: Has data for today")
                else:
                    print(f"❌ {fund}: Latest data is {date_str} (Misssing today?)")
        else:
            print("No data found in portfolio_positions")
            
    except Exception as e:
        print(f"Error querying Supabase: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_pnl()
