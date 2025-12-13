#!/usr/bin/env python3
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env')
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_PUBLISHABLE_KEY'])

# Check what dates exist in portfolio_positions
result = supabase.table('portfolio_positions').select('date').eq('fund', 'RRSP Lance Webull').order('date', desc=True).limit(200).execute()
dates = sorted(set([row['date'] for row in result.data]), reverse=True)
print(f'Most recent dates in portfolio_positions ({len(dates)} unique dates):')
for d in dates[:10]:
    print(f'  {d}')
