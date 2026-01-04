#!/usr/bin/env python3
"""
Quick test to verify congress_trades_analysis data in PostgreSQL
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def main():
    print("Checking congress_trades_analysis table...")
    
    try:
        client = PostgresClient()
        
        # Count total records
        result = client.execute_query("SELECT COUNT(*) as count FROM congress_trades_analysis")
        count = result[0]['count'] if result else 0
        print(f"\nTotal analyses: {count}")
        
        if count > 0:
            # Get latest 5 records
            latest = client.execute_query("""
                SELECT trade_id, conflict_score, 
                       LEFT(reasoning, 100) as reasoning_preview,
                       model_used, analyzed_at
                FROM congress_trades_analysis
                ORDER BY analyzed_at DESC
                LIMIT 5
            """)
            
            print("\n[LATEST ANALYSES]")
            for row in latest:
                print(f"\n  Trade ID: {row['trade_id']}")
                print(f"  Score: {row['conflict_score']}")
                print(f"  Model: {row['model_used']}")
                print(f"  Analyzed: {row['analyzed_at']}")
                print(f"  Reasoning: {row['reasoning_preview']}...")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
