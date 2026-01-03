import sys
import os
import pandas as pd
from datetime import datetime

# Explicitly add the web_dashboard directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assumes script is in web_dashboard/debug/
web_dashboard_dir = os.path.abspath(os.path.join(current_dir, '..'))

if web_dashboard_dir not in sys.path:
    sys.path.append(web_dashboard_dir)

try:
    from supabase_client import SupabaseClient
    from dotenv import load_dotenv
except ImportError as e:
    # Try adding one level up just in case
    root_dir = os.path.abspath(os.path.join(web_dashboard_dir, '..'))
    sys.path.append(root_dir)
    from web_dashboard.supabase_client import SupabaseClient
    from dotenv import load_dotenv

load_dotenv()

def deep_dive():
    try:
        client = SupabaseClient(use_service_role=True)
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    print("\n--- SCANNING ALL PORTFOLIO POSITIONS (STABLE SORT) ---")
    
    try:
        all_rows = []
        batch_size = 1000 
        offset = 0
        
        while True:
            # Select minimal columns AND ORDER BY ID for stability
            res = client.supabase.table("portfolio_positions")\
                .select("id, fund, ticker, date, shares")\
                .order("id")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not res.data:
                break
            
            all_rows.extend(res.data)
            
            if len(res.data) < batch_size:
                break
            
            offset += batch_size
            print(f"  Fetched {len(all_rows)} rows...", end='\r')
        
        print(f"  Total rows scanned: {len(all_rows)}")
        
        if not all_rows:
            print("  No positions found in database.")
            return

        df = pd.DataFrame(all_rows)
        df['date_key'] = df['date'].astype(str).str[:10]
        
        # Verify no ID duplicates (sanity check for pagination)
        id_dups = df[df.duplicated(subset=['id'])]
        if not id_dups.empty:
            print(f"  WARNING: Script still fetched {len(id_dups)} duplicate IDs! Pagination sort failed?")
            # Drop them to be safe
            df = df.drop_duplicates(subset=['id'])
        
        # Group by fund
        funds_found = df['fund'].unique()
        print(f"Funds found in positions: {funds_found}")
        
        for fund in funds_found:
            print(f"\n--- ANALYZING: {fund} ---")
            fund_df = df[df['fund'] == fund].copy()
            print(f"  Rows: {len(fund_df)}")
            
            # Check duplicates (Different IDs, same ticker/date)
            duplicates = fund_df[fund_df.duplicated(subset=['date_key', 'ticker'], keep=False)]
            
            if not duplicates.empty:
                print(f"  ⚠️  CRITICAL: Found {len(duplicates)} duplicates for {fund}!")
                
                # Sort to show pairs together
                dup_view = duplicates.sort_values(['ticker', 'date_key'])
                print(dup_view[['date_key', 'ticker', 'shares', 'id']].head(10).to_string(index=False))
                
                # Check if IDs are different (Real DB duplicates)
                if duplicates['id'].nunique() == len(duplicates):
                     print("  CONFIRMED: All duplicates have distinct IDs. These are REAL database duplicates.")
                else:
                     print("  WARNING: IDs match? This shouldn't happen after drop_duplicates.")
            else:
                print(f"  ✅ No duplicates found for {fund}.")
                
    except Exception as e:
        print(f"Error scanning positions: {e}")

if __name__ == "__main__":
    deep_dive()
