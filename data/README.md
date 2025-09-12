# Data Module

The data module provides the foundation for data access and modeling in the trading system. It implements a repository pattern that abstracts data storage, allowing the system to work with both CSV files (current) and database backends (future) without changing business logic.

## Structure

```
data/
├── models/          # Data models for portfolio, trades, and market data
├── repositories/    # Data access layer with repository pattern
└── README.md       # This file
```

## Models

### Portfolio Models (`models/portfolio.py`)
- `Position`: Represents a single stock position with shares, prices, and P&L
- `PortfolioSnapshot`: Complete portfolio state at a point in time
- `CashBalance`: Cash holdings in different currencies

### Trade Models (`models/trade.py`)
- `Trade`: Individual buy/sell transactions with validation
- `TradeLog`: Collection of trades with filtering and analysis

### Market Data Models (`models/market_data.py`)
- `MarketData`: OHLCV price data with metadata
- `ExchangeRate`: Currency conversion rates

## Repository Pattern

The repository pattern provides a clean abstraction for data access:

### Base Repository (`repositories/base_repository.py`)
Abstract interface defining all data operations:
- Portfolio CRUD operations
- Trade history management
- Market data access
- Backup and restore capabilities

### CSV Repository (`repositories/csv_repository.py`)
Current implementation using CSV files:
- Timezone-aware CSV parsing
- Atomic file operations with backups
- Maintains backward compatibility with existing files

### Repository Factory (`repositories/repository_factory.py`)
Factory pattern for creating repository instances:
- Configuration-based repository selection
- Dependency injection support
- Easy switching between backends

## Future Database Migration

The data models and repository pattern are designed to support future database migration:

1. **Database-Ready Models**: All models include optional ID fields for database primary keys
2. **Serialization Support**: Models support both CSV and JSON serialization
3. **Repository Abstraction**: Business logic is decoupled from storage implementation
4. **Migration Tools**: Planned migration utilities to transfer CSV data to database

## Usage Examples

```python
from data.repositories.repository_factory import RepositoryFactory
from config.settings import Settings

# Create repository based on configuration
settings = Settings()
repository = RepositoryFactory.create_repository(settings)

# Load portfolio data
snapshots = repository.get_portfolio_data()
latest = repository.get_latest_portfolio_snapshot()

# Save new data
repository.save_portfolio_snapshot(new_snapshot)
repository.save_trade(new_trade)
```

## Configuration

Repository selection is controlled through the settings system:

```json
{
  "repository": {
    "type": "csv",
    "csv": {
      "data_directory": "my trading"
    }
  }
}
```

Future database configuration:
```json
{
  "repository": {
    "type": "database",
    "database": {
      "host": "localhost",
      "database": "trading_system",
      "username": "user",
      "password": "pass"
    }
  }
}
```