#!/usr/bin/env python3
"""Test that get_trade_log now includes company names"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent  # debug/ -> project root
sys.path.insert(0, str(project_root))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)
trades = client.get_trade_log(limit=10)

print(f"Retrieved {len(trades)} recent trades\n")

with_company = 0
without_company = 0

for idx, trade in enumerate(trades[:10], 1):
    ticker = trade.get('ticker', 'N/A')
    company = trade.get('company_name', None)
    date = trade.get('date', 'N/A')[:10] if trade.get('date') else 'N/A'
    
    if company:
        with_company += 1
        print(f"{idx}. {ticker:10} - {company:40} ({date})")
    else:
        without_company += 1
        print(f"{idx}. {ticker:10} - {'[NO COMPANY NAME]':40} ({date})")

print(f"\nSummary:")
print(f"- With company name: {with_company}")
print(f"- Without company name: {without_company}")
