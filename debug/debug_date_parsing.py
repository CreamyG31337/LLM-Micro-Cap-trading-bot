"""Debug date parsing in repository."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from data.repositories.csv_repository import CSVRepository

data_dir = Path('trading_data/funds/Project Chimera')
repo = CSVRepository(str(data_dir))

print('Reading CSV directly...')
df = pd.read_csv(data_dir / 'llm_portfolio_update.csv')
print(f'Total rows: {len(df)}')

print('\nSample raw Date values:')
print(df['Date'].tail(30).unique())

print('\nParsing dates...')
df['Date'] = df['Date'].apply(repo._parse_csv_timestamp)
print('After _parse_csv_timestamp:')
print(df['Date'].tail(10))

print('\nConverting to datetime...')
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
print('After pd.to_datetime:')
print(df['Date'].tail(10))
print(f'NaT count: {df["Date"].isna().sum()}')

print('\nGrouping by date...')
df['Date_Only'] = df['Date'].dt.date
print('Unique dates:')
print(sorted(df['Date_Only'].dropna().unique()))