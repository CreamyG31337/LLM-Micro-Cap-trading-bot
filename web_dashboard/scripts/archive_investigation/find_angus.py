import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Searching for Angus King...\n")

# Check production
prod_result = client.supabase.table('congress_trades')\
    .select('politician,ticker,transaction_date,party')\
    .or_('politician.ilike.%angus%,politician.ilike.%king%')\
    .execute()

print(f"Production: {len(prod_result.data)} matches")
if prod_result.data:
    for t in prod_result.data[:5]:
        print(f"  {t['politician']:20s} | {t['ticker']:6s} | Party: {t.get('party', 'NULL')}")

# Check staging
staging_result = client.supabase.table('congress_trades_staging')\
    .select('politician,ticker,transaction_date,party')\
    .or_('politician.ilike.%angus%,politician.ilike.%king%')\
    .execute()

print(f"\nStaging: {len(staging_result.data)} matches")
if staging_result.data:
    for t in staging_result.data[:5]:
        print(f"  {t['politician']:20s} | {t['ticker']:6s} | Party: {t.get('party', 'NULL')}")

# Also check unique politicians
print(f"\n\nChecking all unique politicians in production...")
all_trades = client.supabase.table('congress_trades')\
    .select('politician')\
    .execute()

unique_pols = set(t['politician'] for t in all_trades.data)
print(f"Unique politicians: {len(unique_pols)}")

# Check for any King
kings = [p for p in unique_pols if 'king' in p.lower()]
print(f"\nPoliticians with 'King': {len(kings)}")
for k in kings:
    print(f"  - {k}")
