import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Checking for trades with NULL owner values that could be duplicates...")
print("="*80)

# Get trades with NULL owner
result = client.supabase.table('congress_trades')\
    .select('*')\
    .is_('owner', 'null')\
    .execute()

print(f"\nTrades with NULL owner: {len(result.data)}")

if len(result.data) > 0:
    from collections import defaultdict
    seen = defaultdict(list)
    
    for trade in result.data:
        key = (
            trade['politician'], 
            trade['ticker'], 
            str(trade['transaction_date']), 
            trade['amount'],
            trade['type']
        )
        seen[key].append(trade)
    
    # Find where there are multiple records with same key and NULL owner
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    
    if duplicates:
        print(f"\n⚠️ FOUND {len(duplicates)} GROUPS WITH DUPLICATE NULL OWNER RECORDS!\n")
        
        for i, (key, trades) in enumerate(list(duplicates.items())[:15]):
            print(f"\n{i+1}. {key[0]} | {key[1]} | {key[2]} | {key[4]}")
            print("   " + "-"*76)
            for t in sorted(trades, key=lambda x: x['id']):
                print(f"   ID: {t['id']:6d} | State: {str(t.get('state') or 'NULL'):4s} | "
                      f"Party: {str(t.get('party') or 'NULL'):12s} | "
                      f"Created: {str(t['created_at'])[:19]}")
        
        total = sum(len(v) for v in duplicates.values())
        print(f"\n\nTotal records in duplicate groups: {total}")
        print(f"These should be de-duplicated!")
    else:
        print("\n✅ No duplicates found in NULL owner records")
else:
    print("\n✅ No trades with NULL owner")
