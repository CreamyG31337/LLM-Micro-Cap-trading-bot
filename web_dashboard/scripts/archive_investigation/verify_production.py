import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*70)
print("PRODUCTION TABLE VERIFICATION")
print("="*70)

# 1. Count check
result = client.supabase.table('congress_trades')\
    .select('*', count='exact')\
    .execute()

trades = result.data
print(f"\n1. TOTAL COUNT")
print(f"   Expected: 28,302")
print(f"   Actual:   {result.count}")
print(f"   Status:   {'✅ PASS' if result.count == 28302 else '❌ FAIL'}")

# 2. Check for duplicates
print(f"\n2. DUPLICATE CHECK")
groups = defaultdict(list)
for trade in trades:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount'],
        trade.get('owner') or 'Not-Disclosed'
    )
    groups[key].append(trade['id'])

duplicates = {k: v for k, v in groups.items() if len(v) > 1}
print(f"   Duplicate groups: {len(duplicates)}")
print(f"   Status: {'✅ PASS - No duplicates' if len(duplicates) == 0 else '❌ FAIL - Has duplicates'}")

if duplicates:
    print(f"\n   First 3 duplicate groups:")
    for i, (key, ids) in enumerate(list(duplicates.items())[:3]):
        print(f"      {i+1}. {key[0]:20s} | {key[1]:6s} | {key[2]} - IDs: {ids}")

# 3. Check Angus King party fix
print(f"\n3. ANGUS KING PARTY FIX")
angus_trades = [t for t in trades if t['politician'] == 'Angus King']
if angus_trades:
    missing_party = [t for t in angus_trades if not t.get('party')]
    print(f"   Angus King trades: {len(angus_trades)}")
    print(f"   Missing party: {len(missing_party)}")
    print(f"   Status: {'✅ PASS - All have party' if len(missing_party) == 0 else '❌ FAIL - Some missing party'}")
    if len(angus_trades) > 0:
        print(f"   Party value: {angus_trades[0].get('party', 'NULL')}")
else:
    print(f"   No Angus King trades found")

# 4. Data completeness
print(f"\n4. DATA COMPLETENESS")
missing_party = sum(1 for t in trades if not t.get('party'))
missing_state = sum(1 for t in trades if not t.get('state'))
missing_owner = sum(1 for t in trades if not t.get('owner'))

print(f"   Missing party: {missing_party}")
print(f"   Missing state: {missing_state}")
print(f"   Missing owner: {missing_owner}")
print(f"   Status: {'✅ PASS' if missing_party == 0 and missing_state == 0 else '⚠️  WARNING'}")

# 5. Sample data
print(f"\n5. SAMPLE RECENT TRADES")
recent = sorted(trades, key=lambda x: x['transaction_date'], reverse=True)[:5]
for t in recent:
    print(f"   {t['transaction_date']} | {t['politician']:25s} | {t['ticker']:6s} | {t['type']:8s} | {t.get('party', 'NULL'):10s}")

# 6. Check for specific politicians
print(f"\n6. SPOT CHECKS")
dwight = [t for t in trades if 'Dwight' in t['politician'] and 'Evans' in t['politician']]
print(f"   Dwight Evans trades: {len(dwight)}")

rohit = [t for t in trades if 'Rohit' in t['politician'] and 'Khanna' in t['politician']]
print(f"   Rohit Khanna trades: {len(rohit)}")

print(f"\n" + "="*70)
if result.count == 28302 and len(duplicates) == 0 and missing_party == 0:
    print("✅ ALL CHECKS PASSED - Migration successful!")
else:
    print("⚠️  Some issues found - review above")
print("="*70)
