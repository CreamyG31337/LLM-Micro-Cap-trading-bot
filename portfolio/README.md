# Portfolio Module

The portfolio module handles portfolio management, trade processing, and position calculations. It provides high-level operations for managing trading portfolios using the repository pattern.

## Structure

```
portfolio/
├── portfolio_manager.py    # Portfolio CRUD operations and management
├── trade_processor.py      # Trade execution, validation, and logging
├── position_calculator.py  # Position sizing, metrics, and analytics
└── README.md              # This file
```

## Portfolio Manager (`portfolio_manager.py`)

Manages portfolio data using the repository pattern, providing high-level portfolio operations:

### Key Features
- **Repository Abstraction**: Works with any repository implementation (CSV, database)
- **Portfolio CRUD**: Complete create, read, update, delete operations
- **Data Validation**: Ensures portfolio data integrity
- **Error Handling**: Comprehensive error handling with clear messages

### Core Operations
- `load_portfolio()`: Load portfolio snapshots with optional date filtering
- `save_portfolio_snapshot()`: Save complete portfolio state
- `get_latest_snapshot()`: Get most recent portfolio data
- `update_positions()`: Update individual positions
- `calculate_portfolio_value()`: Calculate total portfolio value

### Usage Example
```python
from portfolio.portfolio_manager import PortfolioManager
from data.repositories.repository_factory import RepositoryFactory

# Initialize with repository
repository = RepositoryFactory.create_repository(settings)
manager = PortfolioManager(repository)

# Load current portfolio
snapshots = manager.load_portfolio()
latest = manager.get_latest_snapshot()

# Update portfolio
manager.save_portfolio_snapshot(updated_snapshot)
```

## Trade Processor (`trade_processor.py`)

Handles trade execution, validation, and logging with comprehensive error checking:

### Key Features
- **Trade Validation**: Validates all trade parameters before execution
- **Execution Logic**: Processes buy/sell orders with proper accounting
- **Trade Logging**: Maintains complete audit trail of all trades
- **Error Recovery**: Handles partial failures and rollback scenarios

### Trade Operations
- `execute_trade()`: Execute buy/sell orders with validation
- `validate_trade()`: Comprehensive trade validation
- `log_trade()`: Record trades in trade history
- `calculate_trade_impact()`: Calculate impact on portfolio
- `process_batch_trades()`: Handle multiple trades atomically

### Validation Rules
- **Sufficient Funds**: Ensure adequate cash for purchases
- **Position Availability**: Verify shares available for sales
- **Price Validation**: Check for reasonable price ranges
- **Market Hours**: Validate trading during appropriate times

### Usage Example
```python
from portfolio.trade_processor import TradeProcessor
from data.models.trade import Trade

processor = TradeProcessor(repository)

# Create and execute trade
trade = Trade(
    ticker="AAPL",
    action="BUY",
    shares=100,
    price=150.00,
    timestamp=datetime.now()
)

result = processor.execute_trade(trade)
```

## Position Calculator (`position_calculator.py`)

Provides position sizing, metrics, and analytics calculations:

### Key Features
- **Position Sizing**: Calculate optimal position sizes
- **Portfolio Metrics**: Comprehensive portfolio analytics
- **Risk Calculations**: Position-level and portfolio-level risk metrics
- **Performance Attribution**: Analyze performance by position
- **NAV-Based Ownership**: Accurate per-investor returns for multi-investor funds

### Calculations Provided
- **Position Metrics**:
  - Current market value
  - Unrealized P&L
  - Position weight in portfolio
  - Cost basis and average price
  
- **Portfolio Analytics**:
  - Total portfolio value
  - Asset allocation percentages
  - Sector/geographic diversification
  - Risk concentration metrics

- **Performance Metrics**:
  - Individual position returns
  - Portfolio total return
  - Risk-adjusted returns
  - Sharpe ratio calculations

- **Ownership Metrics** (for multi-investor funds):
  - NAV (Net Asset Value) tracking per contribution
  - Unit-based ownership calculations
  - Per-investor returns (accounting for join date)
  - Accurate gain/loss attribution

### Usage Example
```python
from portfolio.position_calculator import PositionCalculator

calculator = PositionCalculator()

# Calculate position metrics
metrics = calculator.calculate_position_metrics(position, current_price)

# Calculate portfolio analytics
analytics = calculator.calculate_portfolio_analytics(portfolio_snapshot)

# Calculate optimal position size
optimal_size = calculator.calculate_position_size(
    portfolio_value=100000,
    target_weight=0.05,
    current_price=150.00
)
```

## Integration with Other Modules

### Financial Module Integration
- Uses financial calculations for precise arithmetic
- Leverages currency handling for multi-currency positions
- Integrates P&L calculations for performance metrics

### Market Data Integration
- Fetches current prices for position valuation
- Uses market hours for trade timing validation
- Integrates price cache for performance optimization

### Data Module Integration
- Works exclusively through repository pattern
- Uses data models for type safety
- Supports both CSV and future database backends

## Error Handling

Comprehensive error handling throughout the module:

### Trade Errors
- `InsufficientFundsError`: Not enough cash for purchase
- `InsufficientSharesError`: Not enough shares for sale
- `InvalidTradeError`: Trade validation failures
- `MarketClosedError`: Attempting trades outside market hours

### Portfolio Errors
- `PortfolioNotFoundError`: Portfolio data not available
- `DataIntegrityError`: Portfolio data corruption detected
- `CalculationError`: Errors in portfolio calculations

### Recovery Strategies
- Automatic retry for transient errors
- Rollback capabilities for failed operations
- Graceful degradation when possible

## Configuration

Portfolio behavior can be configured through settings:

```json
{
  "portfolio": {
    "default_currency": "CAD",
    "enable_fractional_shares": false,
    "max_position_weight": 0.10,
    "cash_reserve_percentage": 0.05,
    "trade_validation": {
      "check_market_hours": true,
      "require_price_validation": true,
      "max_price_deviation": 0.05
    }
  }
}
```

## Testing

The portfolio module includes comprehensive tests:

### Unit Tests
- Individual function testing with mock data
- Edge case validation (zero positions, negative values)
- Error condition testing

### Integration Tests
- End-to-end trade processing
- Portfolio state consistency
- Repository integration validation

### Performance Tests
- Large portfolio handling
- Batch operation performance
- Memory usage optimization

## Future Enhancements

Planned improvements for database migration:

### Advanced Features
- **Multi-Portfolio Support**: Manage multiple portfolios per user
- **Real-time Updates**: Live portfolio value updates
- **Advanced Analytics**: Machine learning-based insights
- **Risk Management**: Automated risk monitoring and alerts

### Web Dashboard Integration
- **REST API**: Portfolio data API for web interface
- **Real-time Streaming**: WebSocket updates for live data
- **User Management**: Multi-user portfolio access
- **Mobile Support**: Mobile-optimized portfolio views

### Performance Optimizations
- **Caching Strategies**: Advanced caching for large portfolios
- **Batch Processing**: Optimized batch operations
- **Parallel Calculations**: Multi-threaded analytics
- **Database Optimization**: Efficient database queries