#!/usr/bin/env python3
"""Delete Dwight Evans duplicate trades with NULL metadata"""

import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# IDs to delete (duplicates with NULL party/state/owner)
ids_to_delete = [106392, 106472, 117354, 117342, 117340, 106391]

print(f"Deleting {len(ids_to_delete)} duplicate Dwight Evans trades...")
print(f"IDs: {ids_to_delete}\n")

try:
    result = client.supabase.table('congress_trades')\
        .delete()\
        .in_('id', ids_to_delete)\
        .execute()
   
    print(f"✅ Deleted {len(ids_to_delete)} duplicate records!")
    print("\nVerifying...")
    
    # Check Dwight Evans trades again
    result = client.supabase.table('congress_trades')\
        .select('id,ticker,transaction_date,type,party,state')\
        .eq('politician', 'Dwight Evans')\
        .eq('transaction_date', '2025-11-21')\
        .execute()
    
    print(f"\nDwight Evans trades on 2025-11-21: {len(result.data)}")
    for trade in sorted(result.data, key=lambda x: x['ticker']):
        print(f"  {trade['ticker']:6s} {trade['type']:10s} - Party:{str(trade.get('party') or 'NULL'):10s} State:{str(trade.get('state') or 'NULL')}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
