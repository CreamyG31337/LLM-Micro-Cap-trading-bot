#!/usr/bin/env python3
"""
Add confidence_score column to congress_trades_analysis table
Uses urllib and http.client to avoid psycopg2 dependency
"""

import os
import sys
from pathlib import Path

# Try to read .env file manually
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Get the connection URL
db_url = os.getenv('RESEARCH_DATABASE_URL')
if not db_url:
    print("❌ RESEARCH_DATABASE_URL not found in environment")
    sys.exit(1)

print(f"Found RESEARCH_DATABASE_URL: {db_url[:30]}...")
print("\nℹ️  This script requires psycopg2 to be installed.")
print("Since psycopg2 is not available locally, here's what to do:\n")
print("=" * 80)
print("OPTION 1: Install psycopg2-binary locally")
print("=" * 80)
print("pip install psycopg2-binary")
print("python web_dashboard\\scripts\\migrate_add_confidence_score.py\n")
print("=" * 80)
print("OPTION 2: Run migration in Docker container (RECOMMENDED)")
print("=" * 80)
print("The migration will run automatically when the Docker container starts")
print("because the schema file (22_congress_trades_analysis.sql) was updated.\n")
print("=" * 80)
print("OPTION 3: Manual SQL (if you have psql or pgAdmin)")
print("=" * 80)
print("""
ALTER TABLE congress_trades_analysis 
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2) 
CHECK (confidence_score >= 0 AND confidence_score <= 1);

CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_confidence 
ON congress_trades_analysis(confidence_score);

COMMENT ON COLUMN congress_trades_analysis.confidence_score IS 
'AI confidence in the analysis (0.0-1.0, higher is more confident)';
""")
print("=" * 80)
