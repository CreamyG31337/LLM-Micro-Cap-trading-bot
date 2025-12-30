#!/usr/bin/env python3
"""
Check if politician IDs from congress trades actually exist in the politicians table
"""

import sys
from pathlib import Path

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

# Politician IDs from the debug output
problematic_ids = [
    5411, 5414, 5434, 5453, 5449, 5489, 5446, 5447, 5487, 5456,
    5406, 5436, 5457, 5445, 5439, 5471, 5421, 5475, 5417, 5431,
    5430, 5442, 5412, 5443, 5423, 5452, 5407, 5428, 5438, 5448,
    5479, 5466, 5467, 5427, 5451, 5413, 5437, 5440, 5484, 5418,
    5422, 5469, 5409, 5491
]

def main():
    print("Checking if politician IDs exist in database...")
    print("=" * 70)
    
    supabase = SupabaseClient()
    
    # Check all IDs at once
    result = supabase.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .in_('id', problematic_ids)\
        .execute()
    
    found_ids = {p['id']: p for p in result.data}
    missing_ids = [pid for pid in problematic_ids if pid not in found_ids]
    
    print(f"\nFound: {len(found_ids)} politicians")
    print(f"Missing: {len(missing_ids)} politicians")
    
    if found_ids:
        print("\n[OK] Politicians that DO exist:")
        for pid, pol in sorted(found_ids.items()):
            print(f"  ID {pid}: {pol['name']} (Bioguide: {pol.get('bioguide_id', 'N/A')})")
    
    if missing_ids:
        print(f"\n[ERROR] Politician IDs that DON'T exist: {missing_ids}")
        
        # Check if these IDs exist in congress_trades
        trades_result = supabase.supabase.table('congress_trades')\
            .select('id, politician_id, ticker, transaction_date')\
            .in_('politician_id', missing_ids)\
            .limit(10)\
            .execute()
        
        if trades_result.data:
            print(f"\n[WARNING] Found {len(trades_result.data)} trades with invalid politician_id references")
            print("Sample trades with invalid politician_id:")
            for trade in trades_result.data[:5]:
                print(f"  Trade ID {trade['id']}: politician_id={trade['politician_id']}, ticker={trade['ticker']}")

if __name__ == "__main__":
    main()

