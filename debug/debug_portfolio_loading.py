"""Debug script to trace portfolio loading issue."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from data.repositories.repository_factory import get_repository_container, configure_repositories
from portfolio.portfolio_manager import PortfolioManager
from portfolio.fund_manager import Fund, RepositorySettings

data_dir = Path('trading_data/funds/Project Chimera')
settings = get_settings()
settings._data_directory = str(data_dir)
settings._config['repository']['csv']['data_directory'] = str(data_dir)

repo_config = settings.get_repository_config()
configure_repositories({'default': repo_config})
repository = get_repository_container().get_repository('default')

fund = Fund(
    id='Project_Chimera',
    name='Project Chimera',
    description='Test',
    repository=RepositorySettings(type='csv', settings={'data_directory': str(data_dir)})
)

print('Creating portfolio manager...')
portfolio_manager = PortfolioManager(repository, fund)

print('\nGetting latest portfolio...')
latest = portfolio_manager.get_latest_portfolio()
print(f'Latest snapshot timestamp: {latest.timestamp}')
print(f'Latest snapshot date: {latest.timestamp.date()}')

print('\nGetting all snapshots...')
all_snapshots = repository.get_portfolio_data()
print(f'Total snapshots: {len(all_snapshots)}')
print('\nLast 10 snapshot dates:')
for snapshot in all_snapshots[-10:]:
    print(f'  {snapshot.timestamp.date()} at {snapshot.timestamp.time()} - {len(snapshot.positions)} positions')

print('\nChecking CSV file directly...')
import pandas as pd
df = pd.read_csv(data_dir / 'llm_portfolio_update.csv')
print(f'Total rows in CSV: {len(df)}')
unique_dates = sorted(set([str(d).split()[0] for d in df['Date'].unique() if '2025-09' in str(d)]))
print(f'\nUnique September dates in CSV:')
for d in unique_dates[-10:]:
    print(f'  {d}')