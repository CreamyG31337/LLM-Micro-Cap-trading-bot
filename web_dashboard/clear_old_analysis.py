#!/usr/bin/env python3
"""
Clear old AI analysis data from Supabase congress_trades table
This is safe to do because we've moved AI analysis to PostgreSQL
"""

import sys
import argparse
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from supabase_client import SupabaseClient

def main():
    parser = argparse.ArgumentParser(description='Clear old AI analysis data from Supabase')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("Clearing old AI analysis data from Supabase...")
    print("(AI analysis has been moved to PostgreSQL)")
    
    try:
        client = SupabaseClient(use_service_role=True)
        
        # First, count how many rows will be affected
        result = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .not_.is_('conflict_score', 'null')\
            .execute()
        
        count = result.count if hasattr(result, 'count') else 0
        
        print(f"\n[INFO] Found {count} trades with conflict_score (will clear notes and conflict_score)")
        
        if count == 0:
            print("[OK] No trades to update!")
            return
        
        # Confirm with user (unless --yes flag)
        if not args.yes:
            response = input(f"\nClear notes and conflict_score for {count} trades? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("[CANCELLED] No changes made")
                return
        else:
            print(f"[AUTO-CONFIRMED] Proceeding to clear {count} trades...")
        
        # Update: set notes and conflict_score to NULL where conflict_score IS NOT NULL
        update_result = client.supabase.table('congress_trades')\
            .update({
                'notes': None,
                'conflict_score': None
            })\
            .not_.is_('conflict_score', 'null')\
            .execute()
        
        updated_count = len(update_result.data) if update_result.data else 0
        
        print(f"\n[OK] Cleared {updated_count} trades!")
        print("\n[NEXT STEPS]")
        print("Run the analysis script with --skip-nulls to analyze trades with metadata:")
        print("  python web_dashboard/scripts/analyze_congress_trades_batch.py --skip-nulls --batch-size 10")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
