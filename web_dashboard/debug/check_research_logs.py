#!/usr/bin/env python3
"""Check application logs for research job activity"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from log_handler import read_logs_from_file
except ImportError:
    print("Cannot import log_handler")
    sys.exit(1)

# Search for research-related logs
logs = read_logs_from_file(n=500, search='research')

print(f"Found {len(logs)} research-related log entries\n")

if logs:
    print("Recent research job activity:")
    print("=" * 70)
    for log in logs[-30:]:  # Show last 30
        print(f"{log['timestamp']} [{log['level']:8s}] {log['message']}")
else:
    print("No research-related logs found")
    print("\nThis could mean:")
    print("1. Jobs haven't run yet")
    print("2. Web dashboard isn't running (scheduler starts with it)")
    print("3. Logs are in a different location")

# Also check for market_research specifically
market_logs = read_logs_from_file(n=500, search='market_research')
print(f"\n\nFound {len(market_logs)} 'market_research' log entries")
if market_logs:
    print("\nRecent market_research activity:")
    print("=" * 70)
    for log in market_logs[-20:]:
        print(f"{log['timestamp']} [{log['level']:8s}] {log['message']}")

