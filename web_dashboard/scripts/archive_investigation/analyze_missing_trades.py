import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("="*70)
print("ANALYZING MISSING TRADES")
print("="*70)

# Check staging total
staging_count = client.supabase.table('congress_trades_staging')\
    .select('id', count='exact')\
    .execute()

# Check production total
prod_count = client.supabase.table('congress_trades')\
    .select('id', count='exact')\
    .execute()

print(f"\nSource website: 35,640 trades")
print(f"Staging total:  {staging_count.count:,} trades")
print(f"Production:     {prod_count.count:,} trades")
print(f"\nMissing from staging: {35640 - staging_count.count:,} trades")
print(f"Lost in migration:    {staging_count.count - prod_count.count:,} trades")

# Check date ranges
staging_dates = client.supabase.table('congress_trades_staging')\
    .select('transaction_date')\
    .order('transaction_date')\
    .limit(1)\
    .execute()

staging_dates_max = client.supabase.table('congress_trades_staging')\
    .select('transaction_date')\
    .order('transaction_date', desc=True)\
    .limit(1)\
    .execute()

print(f"\nStaging date range:")
if staging_dates.data and staging_dates_max.data:
    print(f"  Oldest: {staging_dates.data[0]['transaction_date']}")
    print(f"  Newest: {staging_dates_max.data[0]['transaction_date']}")

print(f"\n💡 Likely reason for missing ~7k trades:")
print(f"   The scraper may have stopped early or hit a limit")
print(f"   Check if scraper job is still running or errored out")
