"""Debug script to manually trigger portfolio refresh and check if prices are updating."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from data.repositories.repository_factory import get_repository_container, configure_repositories
from portfolio.portfolio_manager import PortfolioManager
from market_data.market_hours import MarketHours
from portfolio.fund_manager import Fund, RepositorySettings
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache

data_dir = Path('trading_data/funds/WEBULL_TEST')
settings = get_settings()
settings._data_directory = str(data_dir)
settings._config['repository']['csv']['data_directory'] = str(data_dir)

repo_config = settings.get_repository_config()
configure_repositories({'default': repo_config})
repository = get_repository_container().get_repository('default')

fund = Fund(
    id='WEBULL_TEST',
    name='Webull Test',
    description='Test fund',
    repository=RepositorySettings(type='csv', settings={'data_directory': str(data_dir)})
)

portfolio_manager = PortfolioManager(repository, fund)
market_hours = MarketHours(settings=settings)

# Clear the price cache to force fresh fetches
price_cache = PriceCache(settings=settings)
price_cache._price_cache = {}  # Clear cache
market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)

print('Getting latest portfolio snapshot...')
latest_snapshot = portfolio_manager.get_latest_portfolio()
print(f'Latest snapshot timestamp: {latest_snapshot.timestamp}')
print(f'Number of positions: {len(latest_snapshot.positions)}')
print('\nFirst 5 positions BEFORE refresh:')
for pos in latest_snapshot.positions[:5]:
    print(f'  {pos.ticker}: ${pos.current_price:.2f}')

print('\nFetching current prices from API...')
for pos in latest_snapshot.positions[:5]:
    current_price = market_data_fetcher.get_current_price(pos.ticker)
    print(f'  {pos.ticker}: API says ${current_price:.2f} (was ${pos.current_price:.2f})')

print('\nNow running the refresh function...')
from utils.portfolio_refresh import refresh_portfolio_prices_if_needed

was_updated, reason = refresh_portfolio_prices_if_needed(
    market_hours=market_hours,
    portfolio_manager=portfolio_manager,
    repository=repository,
    market_data_fetcher=market_data_fetcher,
    price_cache=price_cache,
    verbose=True
)

print(f'\nRefresh result: {was_updated}, {reason}')

print('\nGetting latest snapshot AFTER refresh...')
latest_snapshot_after = portfolio_manager.get_latest_portfolio()
print(f'Latest snapshot timestamp: {latest_snapshot_after.timestamp}')
print('\nFirst 5 positions AFTER refresh:')
for pos in latest_snapshot_after.positions[:5]:
    print(f'  {pos.ticker}: ${pos.current_price:.2f}')