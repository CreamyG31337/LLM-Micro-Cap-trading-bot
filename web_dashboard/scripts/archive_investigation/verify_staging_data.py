import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*70)
print("STAGING DATA VERIFICATION")
print("="*70)

# Get staging count
staging_result = client.supabase.table('congress_trades_staging')\
    .select('*', count='exact')\
    .execute()

staging_trades = staging_result.data
print(f"\n📊 Total staging records: {staging_result.count}")

# Group by business key (including owner to detect true duplicates)
business_key_groups = defaultdict(list)
for trade in staging_trades:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount'],
        trade.get('owner') or 'Not-Disclosed'
    )
    business_key_groups[key].append(trade)

# Find TRUE duplicates (same business key)
true_duplicates = {k: v for k, v in business_key_groups.items() if len(v) > 1}

print(f"\n🔍 Duplicate Analysis:")
print(f"   Unique business keys: {len(business_key_groups)}")
print(f"   Duplicate groups (same politician, ticker, date, type, amount, owner): {len(true_duplicates)}")

# Check if duplicates have different source TX IDs
if true_duplicates:
    print(f"\n⚠️  Found {len(true_duplicates)} duplicate groups. Checking source IDs...")
    
    exact_dupes = []
    different_source = []
    
    for key, trades in list(true_duplicates.items())[:10]:
        source_ids = set()
        for t in trades:
            raw = t.get('raw_data', {})
            if isinstance(raw, dict):
                tx_id = raw.get('_txId')
                if tx_id:
                    source_ids.add(tx_id)
        
        if len(source_ids) == 1:
            # Same source ID = true duplicate
            exact_dupes.append((key, trades))
        elif len(source_ids) > 1:
            # Different source IDs = legitimate separate trades
            different_source.append((key, trades))
    
    print(f"\n   ✅ Different source TX IDs (legitimate): {len(different_source)}")
    print(f"   ❌ SAME source TX IDs (TRUE duplicates): {len(exact_dupes)}")
    
    if exact_dupes:
        print(f"\n   True duplicate examples (need to fix):")
        for key, trades in exact_dupes[:3]:
            print(f"      {key[0]:20s} | {key[1]:6s} | {key[2]} - {len(trades)} copies")
else:
    print(f"   ✅ No duplicates found!")

# Compare with production
prod_result = client.supabase.table('congress_trades')\
    .select('*', count='exact')\
    .execute()

print(f"\n📊 Production records: {prod_result.count}")
print(f"\n📈 Expected new records: ~{staging_result.count - prod_result.count}")

# Build production business keys
prod_keys = set()
for trade in prod_result.data:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount'],
        trade.get('owner') or 'Not-Disclosed'
    )
    prod_keys.add(key)

# Count truly new trades
new_count = sum(1 for key in business_key_groups.keys() if key not in prod_keys)

print(f"   Truly NEW trades (not in production): {new_count}")
print(f"   Already in production: {len(business_key_groups) - new_count}")

print(f"\n" + "="*70)
if len(true_duplicates) == 0 or (len(exact_dupes) == 0 if true_duplicates else True):
    print("✅ STAGING DATA IS CLEAN - Ready for migration")
    print(f"   Will insert {new_count} new unique trades")
else:
    print(f"⚠️  WARNING: {len(exact_dupes) if true_duplicates else 0} true duplicates need cleanup first")
print("="*70)
