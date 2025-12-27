#!/usr/bin/env python3
"""Verify logic_check column was added."""

from web_dashboard.postgres_client import PostgresClient

client = PostgresClient()
result = client.execute_query(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'research_articles' AND column_name = 'logic_check'"
)

if result:
    print("✅ logic_check column exists!")
    print(f"   Column: {result[0]['column_name']}")
    print(f"   Type: {result[0]['data_type']}")
else:
    print("❌ logic_check column not found")

