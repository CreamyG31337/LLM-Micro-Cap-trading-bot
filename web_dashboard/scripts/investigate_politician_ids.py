#!/usr/bin/env python3
"""
Investigate why politician_id values are invalid
Check when these trades were created and if politician_id was set incorrectly
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient

# Problematic politician IDs from debug output
problematic_ids = [
    5411, 5414, 5434, 5453, 5449, 5489, 5446, 5447, 5487, 5456,
    5406, 5436, 5457, 5445, 5439, 5471, 5421, 5475, 5417, 5431,
    5430, 5442, 5412, 5443, 5423, 5452, 5407, 5428, 5438, 5448,
    5479, 5466, 5467, 5427, 5451, 5413, 5437, 5440, 5484, 5418,
    5422, 5469, 5409, 5491
]

def main():
    print("Investigating Invalid Politician IDs")
    print("=" * 70)
    
    supabase = SupabaseClient()
    
    # Get sample trades with these politician_ids
    print("\n1. Checking sample trades with invalid politician_id values...")
    sample_trades = supabase.supabase.table('congress_trades_enriched')\
        .select('id, politician, politician_id, ticker, transaction_date, created_at')\
        .in_('politician_id', problematic_ids[:10])\
        .order('created_at', desc=False)\
        .limit(20)\
        .execute()
    
    if sample_trades.data:
        print(f"\n   Found {len(sample_trades.data)} sample trades")
        print("\n   First few trades (oldest first):")
        for trade in sample_trades.data[:5]:
            created = trade.get('created_at', 'Unknown')
            tx_date = trade.get('transaction_date', 'Unknown')
            print(f"      Trade ID {trade['id']}: {trade.get('politician')} (politician_id={trade.get('politician_id')})")
            print(f"         Created: {created}, Transaction: {tx_date}")
        
        print("\n   Last few trades (newest first):")
        for trade in sample_trades.data[-5:]:
            created = trade.get('created_at', 'Unknown')
            tx_date = trade.get('transaction_date', 'Unknown')
            print(f"      Trade ID {trade['id']}: {trade.get('politician')} (politician_id={trade.get('politician_id')})")
            print(f"         Created: {created}, Transaction: {tx_date}")
    
    # Check date range
    print("\n2. Checking date range of trades with invalid politician_id...")
    date_range = supabase.supabase.table('congress_trades')\
        .select('created_at, transaction_date')\
        .in_('politician_id', problematic_ids)\
        .order('created_at', desc=False)\
        .limit(1)\
        .execute()
    
    if date_range.data:
        oldest = date_range.data[0].get('created_at')
        print(f"   Oldest trade created_at: {oldest}")
    
    date_range_newest = supabase.supabase.table('congress_trades')\
        .select('created_at, transaction_date')\
        .in_('politician_id', problematic_ids)\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    if date_range_newest.data:
        newest = date_range_newest.data[0].get('created_at')
        print(f"   Newest trade created_at: {newest}")
    
    # Check if politician names exist in database with different IDs
    print("\n3. Checking if these politician names exist with different IDs...")
    politician_names = [
        "Joshua Gottheimer", "Thomas Kean Jr", "William Keating", "Michael Burgess",
        "Earl Blumenauer"
    ]
    
    for name in politician_names:
        # Get trades for this politician
        trades = supabase.supabase.table('congress_trades_enriched')\
            .select('politician, politician_id')\
            .eq('politician', name)\
            .limit(1)\
            .execute()
        
        if trades.data:
            pol_id = trades.data[0].get('politician_id')
            print(f"   {name}: politician_id = {pol_id}")
            
            # Check if this ID exists in politicians table
            if pol_id:
                pol_check = supabase.supabase.table('politicians')\
                    .select('id, name')\
                    .eq('id', pol_id)\
                    .execute()
                
                if pol_check.data:
                    print(f"      -> ID {pol_id} EXISTS in politicians table: {pol_check.data[0].get('name')}")
                else:
                    print(f"      -> ID {pol_id} DOES NOT EXIST in politicians table")
    
    # Check what the highest valid politician ID is
    print("\n4. Checking valid politician ID range...")
    max_id_result = supabase.supabase.table('politicians')\
        .select('id')\
        .order('id', desc=True)\
        .limit(1)\
        .execute()
    
    if max_id_result.data:
        max_valid_id = max_id_result.data[0]['id']
        print(f"   Highest valid politician ID: {max_valid_id}")
        print(f"   Problematic IDs range: {min(problematic_ids)} to {max(problematic_ids)}")
        
        if max(problematic_ids) > max_valid_id:
            print(f"   [WARNING] Some problematic IDs are HIGHER than max valid ID!")
        if min(problematic_ids) < max_valid_id:
            print(f"   [INFO] Some problematic IDs are within valid range (but don't exist)")
    
    # Check if there are any trades with NULL politician_id
    print("\n5. Checking trades with NULL politician_id...")
    null_count = supabase.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .is_('politician_id', 'null')\
        .execute()
    
    if hasattr(null_count, 'count'):
        print(f"   Trades with NULL politician_id: {null_count.count}")
    else:
        # Try alternative query
        null_trades = supabase.supabase.table('congress_trades')\
            .select('id')\
            .limit(1000)\
            .execute()
        null_count_manual = sum(1 for t in null_trades.data if t.get('politician_id') is None)
        print(f"   Sample of trades with NULL politician_id: {null_count_manual} (checked first 1000)")

if __name__ == "__main__":
    main()

