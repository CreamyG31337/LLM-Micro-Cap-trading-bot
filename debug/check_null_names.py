#!/usr/bin/env python3
"""Quick check for NULL company names in securities table"""
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)
result = client.supabase.table('securities').select('ticker, company_name').execute()

null_count = 0
for row in result.data:
    if not row.get('company_name') or row.get('company_name') == 'Unknown':
        null_count += 1
        print(f"{row.get('ticker')}: {row.get('company_name')}")

print(f"\nTotal tickers with NULL/Unknown company name: {null_count} out of {len(result.data)}")
