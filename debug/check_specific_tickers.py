#!/usr/bin/env python3
"""Check specific tickers for company names in securities table"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Tickers reported as missing
tickers_to_check = ['CTRN', 'HLIT.TO', 'FDS', 'TSCO']

print("Checking specific tickers in securities table:")
print("=" * 60)

for ticker in tickers_to_check:
    result = client.supabase.table('securities').select('ticker, company_name').eq('ticker', ticker).execute()
    if result.data:
        company = result.data[0].get('company_name', 'NULL')
        print(f"{ticker:10} -> {company}")
    else:
        print(f"{ticker:10} -> NOT IN SECURITIES TABLE")

# Also check trade_log to see if join would work
print("\n" + "=" * 60)
print("Checking trade_log join result:")
trades = client.get_trade_log(limit=50)
for trade in trades:
    ticker = trade.get('ticker')
    if ticker in tickers_to_check:
        print(f"{ticker:10} -> company_name: {trade.get('company_name')}")
