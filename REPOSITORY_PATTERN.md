# Repository Pattern and Database Migration Guide

This document explains the repository pattern implementation in the trading system and provides guidance for the future database migration.

## Repository Pattern Overview

The repository pattern provides a clean abstraction layer between the business logic and data storage, allowing the system to work with different backends (CSV files, databases) without changing the core application logic.

### Benefits

1. **Backend Independence**: Business logic doesn't depend on storage implementation
2. **Easy Testing**: Mock repositories for unit testing
3. **Future Migration**: Seamless transition from CSV to database
4. **Consistent Interface**: Same API regardless of storage backend
5. **Data Validation**: Centralized data validation and integrity checks

## Current Architecture

### Repository Interface (`data/repositories/base_repository.py`)

The abstract base repository defines the contract for all data operations:

```python
class BaseRepository(ABC):
    @abstractmethod
    def get_portfolio_data(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Retrieve portfolio snapshots within optional date range."""
        pass
    
    @abstractmethod
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Save a portfolio snapshot."""
        pass
    
    @abstractmethod
    def get_trade_history(self, ticker: Optional[str] = None) -> List[Trade]:
        """Retrieve trade history with optional ticker filtering."""
        pass
    
    @abstractmethod
    def save_trade(self, trade: Trade) -> None:
        """Save a trade record."""
        pass
```

### CSV Repository (`data/repositories/csv_repository.py`)

Current implementation using CSV files:

```python
class CSVRepository(BaseRepository):
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.portfolio_file = self.data_dir / "llm_portfolio_update.csv"
        self.trade_file = self.data_dir / "llm_trade_log.csv"
        # ... other file paths
    
    def get_portfolio_data(self, date_range=None):
        # Load and parse CSV files
        # Return PortfolioSnapshot objects
        pass
    
    def save_portfolio_snapshot(self, snapshot):
        # Convert to CSV format and save
        pass
```

### Repository Factory (`data/repositories/repository_factory.py`)

Factory pattern for creating repository instances:

```python
class RepositoryFactory:
    @staticmethod
    def create_repository(settings: Settings) -> BaseRepository:
        repo_type = settings.get_repository_type()
        
        if repo_type == "csv":
            return CSVRepository(settings.get_data_directory())
        elif repo_type == "database":
            return DatabaseRepository(settings.get_database_config())
        else:
            raise ValueError(f"Unsupported repository type: {repo_type}")
```

## Data Models

All data models are designed to work with both CSV and database backends:

### Portfolio Models

```python
@dataclass
class Position:
    ticker: str
    shares: Decimal
    avg_price: Decimal
    cost_basis: Decimal
    currency: str = "CAD"
    position_id: Optional[str] = None  # For database primary key
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            'ticker': self.ticker,
            'shares': float(self.shares),
            'avg_price': float(self.avg_price),
            # ... other fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create from dictionary (CSV row or database record)."""
        return cls(
            ticker=data['ticker'],
            shares=Decimal(str(data['shares'])),
            avg_price=Decimal(str(data['avg_price'])),
            # ... other fields
        )
```

### Trade Models

```python
@dataclass
class Trade:
    ticker: str
    action: str  # BUY/SELL
    shares: Decimal
    price: Decimal
    timestamp: datetime
    currency: str = "CAD"
    trade_id: Optional[str] = None  # For database primary key
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create from dictionary (CSV row or database record)."""
        pass
```

## Future Database Migration

### Database Repository Implementation

The future database repository will implement the same interface:

```python
class DatabaseRepository(BaseRepository):
    def __init__(self, db_config: Dict[str, Any]):
        self.connection_pool = self._create_connection_pool(db_config)
    
    def get_portfolio_data(self, date_range=None):
        # SQL query to fetch portfolio snapshots
        # Convert database records to PortfolioSnapshot objects
        pass
    
    def save_portfolio_snapshot(self, snapshot):
        # Convert to database records and insert/update
        pass
    
    def get_trade_history(self, ticker=None):
        # SQL query with optional ticker filtering
        pass
    
    def save_trade(self, trade):
        # Insert trade record into database
        pass
```

### Database Schema

Proposed PostgreSQL schema for the database backend:

```sql
-- Portfolio snapshots table
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    total_value DECIMAL(15,2) NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(timestamp)
);

-- Positions table
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_snapshot_id UUID REFERENCES portfolio_snapshots(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    shares DECIMAL(15,6) NOT NULL,
    avg_price DECIMAL(10,2) NOT NULL,
    cost_basis DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CAD',
    company VARCHAR(255),
    current_price DECIMAL(10,2),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    stop_loss DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    shares DECIMAL(15,6) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CAD',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cash balances table
CREATE TABLE cash_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    currency VARCHAR(3) NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(currency, timestamp)
);

-- Exchange rates table
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(10,6) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, timestamp)
);

-- Market data cache table
CREATE TABLE market_data_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    volume BIGINT,
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, timestamp, source)
);

-- Indexes for performance
CREATE INDEX idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp);
CREATE INDEX idx_positions_ticker ON positions(ticker);
CREATE INDEX idx_positions_portfolio_snapshot ON positions(portfolio_snapshot_id);
CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_market_data_ticker_timestamp ON market_data_cache(ticker, timestamp);
```

### Migration Process

The migration from CSV to database will follow these steps:

#### Phase 1: Preparation
1. **Database Setup**: Create database and tables
2. **Configuration**: Add database configuration to settings
3. **Testing**: Validate database repository with test data

#### Phase 2: Data Migration
1. **Export CSV Data**: Use existing CSV repository to read all data
2. **Transform Data**: Convert CSV data to database format
3. **Import to Database**: Use database repository to save all data
4. **Validation**: Verify data integrity after migration

#### Phase 3: Cutover
1. **Dual Mode**: Run both repositories in parallel for validation
2. **Switch Primary**: Change primary repository to database
3. **Fallback Testing**: Ensure CSV fallback still works
4. **Monitoring**: Monitor performance and data integrity

### Migration Tools

Planned migration utilities:

```python
class CSVToDatabaseMigrator:
    def __init__(self, csv_repo: CSVRepository, db_repo: DatabaseRepository):
        self.csv_repo = csv_repo
        self.db_repo = db_repo
    
    def migrate_all_data(self) -> MigrationResult:
        """Migrate all data from CSV to database."""
        result = MigrationResult()
        
        # Migrate portfolio snapshots
        snapshots = self.csv_repo.get_portfolio_data()
        for snapshot in snapshots:
            self.db_repo.save_portfolio_snapshot(snapshot)
            result.portfolios_migrated += 1
        
        # Migrate trade history
        trades = self.csv_repo.get_trade_history()
        for trade in trades:
            self.db_repo.save_trade(trade)
            result.trades_migrated += 1
        
        return result
    
    def validate_migration(self) -> ValidationResult:
        """Validate that migration was successful."""
        # Compare data between CSV and database
        # Return validation results
        pass
```

## Configuration for Migration

### Current CSV Configuration
```json
{
  "repository": {
    "type": "csv",
    "csv": {
      "data_directory": "my trading",
      "backup_enabled": true
    }
  }
}
```

### Future Database Configuration
```json
{
  "repository": {
    "type": "database",
    "database": {
      "host": "localhost",
      "port": 5432,
      "database": "trading_system",
      "username": "trading_user",
      "password": "${DB_PASSWORD}",
      "pool_size": 10,
      "ssl_mode": "require"
    }
  }
}
```

### Dual Mode Configuration (During Migration)
```json
{
  "repository": {
    "type": "dual",
    "primary": "database",
    "fallback": "csv",
    "sync_mode": "write_through",
    "validation_enabled": true
  }
}
```

## Benefits of Repository Pattern

### For Current CSV System
1. **Clean Architecture**: Separates data access from business logic
2. **Testability**: Easy to mock for unit testing
3. **Consistency**: Standardized data access patterns
4. **Validation**: Centralized data validation

### For Future Database System
1. **Seamless Migration**: No changes to business logic required
2. **Performance**: Optimized database queries and caching
3. **Scalability**: Support for larger datasets and concurrent access
4. **Features**: Advanced querying, transactions, and data integrity
5. **Web Dashboard**: Direct database access for web APIs

### For Development and Testing
1. **Mock Repositories**: Easy testing without real data
2. **Test Data**: Isolated test environments
3. **Development Speed**: Quick iteration without database setup
4. **CI/CD**: Automated testing with mock data

## Best Practices

### Repository Implementation
1. **Interface Compliance**: Always implement the full BaseRepository interface
2. **Error Handling**: Consistent error handling across all repositories
3. **Transaction Support**: Use transactions for multi-step operations
4. **Connection Management**: Proper connection pooling and cleanup
5. **Logging**: Comprehensive logging for debugging and monitoring

### Data Model Design
1. **Serialization**: Support both CSV and database serialization
2. **Validation**: Include validation in model methods
3. **Immutability**: Use immutable data structures where possible
4. **Type Safety**: Strong typing with proper type hints
5. **Documentation**: Clear documentation for all model fields

### Migration Planning
1. **Backup Strategy**: Always backup data before migration
2. **Rollback Plan**: Have a clear rollback strategy
3. **Validation**: Extensive validation of migrated data
4. **Performance Testing**: Test performance with production data volumes
5. **Monitoring**: Monitor system health during and after migration

This repository pattern provides a solid foundation for the current CSV-based system while enabling a smooth transition to a database backend in the future.