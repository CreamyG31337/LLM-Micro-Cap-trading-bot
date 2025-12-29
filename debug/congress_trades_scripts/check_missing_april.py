import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Checking Dwight Evans NVDA trades...")
print("="*80)

result = client.supabase.table('congress_trades')\
    .select('*')\
    .eq('politician', 'Dwight Evans')\
    .eq('ticker', 'NVDA')\
    .order('transaction_date')\
    .execute()

print(f"\nTotal NVDA trades: {len(result.data)}\n")

for t in result.data:
    print(f"{t['transaction_date']} | {t['type']:10s} | {t['amount']:20s} | "
          f"ID:{t['id']:6d} | Party:{str(t.get('party') or 'NULL'):10s}")

print("\n" + "="*80)
print("Checking for April 2025 specifically...")
print("="*80)

result = client.supabase.table('congress_trades')\
    .select('*')\
    .eq('politician', 'Dwight Evans')\
    .gte('transaction_date', '2025-04-01')\
    .lte('transaction_date', '2025-04-30')\
    .execute()

print(f"\nDwight Evans trades in April 2025: {len(result.data)}\n")

if result.data:
    for t in sorted(result.data, key=lambda x: x['transaction_date']):
        print(f"{t['transaction_date']} | {t['ticker']:6s} | {t['type']:10s} | {t['amount']:20s}")
else:
    print("⚠️ NO TRADES FOUND IN APRIL 2025!")
    print("\nThis suggests the April data was never scraped or was blocked during insert.")
