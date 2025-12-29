import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Checking for April 2025 trades...")
print("="*80)

result = client.supabase.table('congress_trades')\
    .select('politician,ticker,transaction_date,type')\
    .gte('transaction_date', '2025-04-01')\
    .lte('transaction_date', '2025-04-30')\
    .execute()

print(f"\nTotal trades in April 2025: {len(result.data)}\n")

if result.data:
    print("Sample April trades:")
    for t in sorted(result.data, key=lambda x: x['transaction_date'])[:20]:
        print(f"{t['transaction_date']} | {t['politician']:25s} | {t['ticker']:6s} | {t['type']}")
else:
    print("⚠️ NO TRADES IN APRIL 2025 AT ALL!")
    print("This suggests scraper may have skipped this month or data source is missing it.")
