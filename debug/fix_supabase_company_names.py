"""Fix company names in Supabase based on correct ticker detection."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Initialize Supabase client
client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# Tickers to fix
tickers_to_fix = {
    'CTRN': 'Citi Trends, Inc.',
    'DRX.TO': 'ADF Group Inc.',
    'VEE.TO': 'Vanguard FTSE Emerging Markets All Cap Index ETF',
    'XMA.TO': 'iShares S&P/TSX Capped Materials Index ETF'
}

print("Fixing company names in Supabase...")
print("=" * 60)

for ticker, correct_name in tickers_to_fix.items():
    print(f"\n{ticker}:")
    
    # Get all records for this ticker
    result = client.table("portfolio_positions")\
        .select("id, company")\
        .eq("fund", "Project Chimera")\
        .eq("ticker", ticker)\
        .execute()
    
    if result.data:
        print(f"  Found {len(result.data)} records")
        print(f"  Current name: {result.data[0]['company']}")
        print(f"  Correct name: {correct_name}")
        
        # Update all records
        update_result = client.table("portfolio_positions")\
            .update({"company": correct_name})\
            .eq("fund", "Project Chimera")\
            .eq("ticker", ticker)\
            .execute()
        
        print(f"  ✅ Updated {len(result.data)} records")
    else:
        print(f"  ⚠️  No records found")

print("\n" + "=" * 60)
print("✅ Done! Company names fixed in Supabase")

