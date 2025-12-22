#!/usr/bin/env python3
"""Delete invalid Dec 22 portfolio positions (future date)"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Check what dates exist
result = client.supabase.table('portfolio_positions')\
    .select('date')\
    .gte('date', '2025-12-22')\
    .execute()

if result.data:
    dates = sorted(set(r['date'][:10] for r in result.data))
    print(f"Found future dates: {dates}")
    print(f"Total rows: {len(result.data)}")
    
    # Delete Dec 22 and later
    delete_result = client.supabase.table('portfolio_positions')\
        .delete()\
        .gte('date', '2025-12-22')\
        .execute()
    
    print(f"\nDeleted {len(result.data)} rows with dates >= 2025-12-22")
else:
    print("No future dates found")
