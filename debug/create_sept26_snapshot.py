"""Create historical portfolio snapshot for September 26, 2025."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import date, datetime, timedelta
from decimal import Decimal
import pandas as pd

from config.settings import get_settings
from data.repositories.repository_factory import get_repository_container, configure_repositories
from portfolio.portfolio_manager import PortfolioManager
from market_data.market_hours import MarketHours
from portfolio.fund_manager import Fund, RepositorySettings
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from data.models.portfolio import Position, PortfolioSnapshot

def get_historical_price(ticker, target_date, market_data_fetcher):
    """Get historical closing price for a ticker on a specific date."""
    try:
        # Try multiple date ranges to find available data
        date_ranges = [
            (target_date, target_date + timedelta(days=1)),  # Exact day
            (target_date - timedelta(days=1), target_date + timedelta(days=2)),  # 3-day window
            (target_date - timedelta(days=3), target_date + timedelta(days=4)),  # 7-day window
        ]
        
        for start_date, end_date in date_ranges:
            result = market_data_fetcher.fetch_price_data(ticker, pd.Timestamp(start_date), pd.Timestamp(end_date))
            df = result.df
            
            if df is not None and not df.empty and 'Close' in df.columns and result.source != "empty":
                # Find row matching the target date or closest available
                day_rows = df[df.index.date == target_date]
                if not day_rows.empty:
                    return float(day_rows['Close'].iloc[0])
                # If no exact match, try to find closest date within range
                available_dates = df.index.date
                closest_dates = [d for d in available_dates if d <= target_date]
                if closest_dates:
                    closest_date = max(closest_dates)
                    closest_rows = df[df.index.date == closest_date]
                    if not closest_rows.empty:
                        return float(closest_rows['Close'].iloc[0])
        
        return None
    except Exception as e:
        print(f"Error fetching historical price for {ticker}: {e}")
        return None


def main():
    # Configure for TEST fund
    data_dir = Path('trading_data/funds/TEST')
    settings = get_settings()
    settings._data_directory = str(data_dir)
    settings._config['repository']['csv']['data_directory'] = str(data_dir)

    repo_config = settings.get_repository_config()
    configure_repositories({'default': repo_config})
    repository = get_repository_container().get_repository('default')

    fund = Fund(
        id='TEST',
        name='Project Chimera',
        description='Test fund',
        repository=RepositorySettings(type='csv', settings={'data_directory': str(data_dir)})
    )

    portfolio_manager = PortfolioManager(repository, fund)
    market_hours = MarketHours(settings=settings)
    price_cache = PriceCache(settings=settings)
    market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)

    print('Creating snapshot for September 26, 2025 (Friday)...')
    
    # Get the latest portfolio to use as template
    latest_snapshot = portfolio_manager.get_latest_portfolio()
    if not latest_snapshot or not latest_snapshot.positions:
        print('Error: No portfolio positions found')
        return

    target_date = date(2025, 9, 26)
    historical_positions = []

    for position in latest_snapshot.positions:
        print(f'Fetching historical price for {position.ticker}...')
        historical_price = get_historical_price(position.ticker, target_date, market_data_fetcher)
        
        if historical_price:
            hist_price_decimal = Decimal(str(historical_price))
            market_value = position.shares * hist_price_decimal
            unrealized_pnl = market_value - position.cost_basis
            
            historical_position = Position(
                ticker=position.ticker,
                shares=position.shares,
                avg_price=position.avg_price,
                cost_basis=position.cost_basis,
                current_price=hist_price_decimal,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                currency=position.currency,
                company=position.company
            )
            historical_positions.append(historical_position)
            print(f'  {position.ticker}: ${historical_price:.2f} (value: ${market_value:.2f})')
        else:
            # Keep existing position data if no historical price found
            historical_positions.append(position)
            print(f'  {position.ticker}: No historical price found, using last known')

    # Create historical snapshot for market close (4:00 PM / 16:00)
    historical_snapshot = PortfolioSnapshot(
        positions=historical_positions,
        timestamp=datetime.combine(target_date, datetime.min.time().replace(hour=16))
    )

    # Save historical snapshot
    repository.save_portfolio_snapshot(historical_snapshot)
    print(f'\n✅ Created snapshot for September 26, 2025 with {len(historical_positions)} positions')


if __name__ == '__main__':
    main()