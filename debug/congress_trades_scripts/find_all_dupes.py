import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("="*80)
print("CONGRESS TRADES DUPLICATE ANALYSIS")
print("="*80)
print()

# Get ALL trades
result = client.supabase.table('congress_trades')\
    .select('*')\
    .execute()

print(f"Total trades in database: {len(result.data)}\n")

# Check for duplicates across ALL politicians
from collections import defaultdict
seen = defaultdict(list)

for trade in result.data:
    # The unique constraint is on: politician, ticker, transaction_date, amount, type, owner
    key = (
        trade['politician'], 
        trade['ticker'], 
        str(trade['transaction_date']), 
        trade['amount'],
        trade['type'],
        trade.get('owner')  # Can be None
    )
    seen[key].append(trade)

# Find ANY duplicates
duplicates = {k: v for k, v in seen.items() if len(v) > 1}

print(f"Total duplicate groups found: {len(duplicates)}\n")

if duplicates:
    print("DUPLICATES FOUND:")
    print("="*80)
    
    for key, trades in list(duplicates.items())[:10]:  # Show first 10
        print(f"\n{key[0]} | {key[1]} | {key[2]} | {key[4]} | {key[3]}")
        print("-"*80)
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"  ID: {t['id']:6d} | State: {str(t.get('state') or 'NULL'):4s} | "
                  f"Party: {str(t.get('party') or 'NULL'):12s} | "
                  f"Owner: {str(t.get('owner') or 'NULL'):15s}")
    
    # Count total duplicate records
    total_dupes = sum(len(v) for v in duplicates.values())
    print(f"\nTotal duplicate records: {total_dupes}")
    print(f"(including all instances of each duplicate group)")
    
    # Analyze missing data
    print("\n" + "="*80)
    print("MISSING DATA ANALYSIS IN DUPLICATES")
    print("="*80)
    
    all_dupe_records = [t for trades in duplicates.values() for t in trades]
    missing_state = [t for t in all_dupe_records if not t.get('state')]
    missing_party = [t for t in all_dupe_records if not t.get('party')]
    missing_owner = [t for t in all_dupe_records if not t.get('owner')]
    
    print(f"Records missing 'state': {len(missing_state)}")
    print(f"Records missing 'party': {len(missing_party)}")
    print(f"Records missing 'owner': {len(missing_owner)}")
    
    if len(missing_state) > 0:
        print(f"\nExample IDs missing state: {[t['id'] for t in missing_state[:10]]}")
    if len(missing_party) > 0:
        print(f"Example IDs missing party: {[t['id'] for t in missing_party[:10]]}")
    if len(missing_owner) > 0:
        print(f"Example IDs missing owner: {[t['id'] for t in missing_owner[:10]]}")
        
else:
    print("✅ NO DUPLICATES FOUND!")
    print("\nThe unique constraint is working correctly:")
    print("  (politician, ticker, transaction_date, amount, type, owner)")
    print("\nAll trades are unique based on this constraint.")
