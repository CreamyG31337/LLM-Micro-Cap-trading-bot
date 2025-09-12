# Financial Module

The financial module provides precise financial calculations using Decimal arithmetic to avoid floating-point precision issues. It includes currency handling, P&L calculations, and core financial operations.

## Structure

```
financial/
├── calculations.py     # Core financial calculations with Decimal precision
├── currency_handler.py # Multi-currency support and exchange rates
├── pnl_calculator.py   # P&L and performance metrics
└── README.md          # This file
```

## Core Calculations (`calculations.py`)

Provides fundamental financial calculations with precise Decimal arithmetic:

### Key Functions
- `money_to_decimal()`: Convert monetary values to precise Decimal format
- `calculate_cost_basis()`: Calculate total cost basis for positions
- `calculate_position_value()`: Calculate current market value of positions
- `calculate_unrealized_pnl()`: Calculate unrealized profit/loss
- `calculate_percentage_change()`: Calculate percentage changes with precision

### Precision Handling
All monetary calculations use Python's `Decimal` type to ensure:
- No floating-point precision errors
- Consistent rounding to 2 decimal places
- Accurate financial calculations for tax and reporting purposes

## Currency Handler (`currency_handler.py`)

Manages multi-currency support and exchange rate conversions:

### Features
- **Currency Detection**: Automatically detect currency from ticker symbols
- **Exchange Rate Management**: Fetch and cache exchange rates
- **Currency Conversion**: Convert between CAD, USD, and other currencies
- **Dual Currency Display**: Support for displaying values in multiple currencies

### Supported Currencies
- CAD (Canadian Dollar) - Primary currency
- USD (US Dollar) - Secondary currency
- EUR, GBP, JPY - Additional currencies (future expansion)

### Usage Example
```python
from financial.currency_handler import CurrencyHandler

handler = CurrencyHandler()

# Detect currency from ticker
currency = handler.detect_ticker_currency("AAPL")  # Returns "USD"

# Convert currencies
cad_value = handler.convert_to_cad(100.0, "USD")
usd_value = handler.convert_to_usd(130.0, "CAD")
```

## P&L Calculator (`pnl_calculator.py`)

Calculates profit/loss and performance metrics:

### Key Features
- **Daily P&L**: Calculate daily profit/loss changes
- **Total Return**: Calculate total return percentages
- **Performance Metrics**: Various performance indicators
- **Time-based Analysis**: P&L over different time periods

### Calculations Provided
- Unrealized P&L for current positions
- Realized P&L from completed trades
- Daily portfolio value changes
- Total return percentages
- Performance attribution by position

### Usage Example
```python
from financial.pnl_calculator import PnLCalculator

calculator = PnLCalculator()

# Calculate daily P&L
daily_pnl = calculator.calculate_daily_pnl(current_portfolio, previous_portfolio)

# Calculate total return
total_return = calculator.calculate_total_return(initial_value, current_value)
```

## Design Principles

### Precision First
All financial calculations prioritize precision over performance:
- Use `Decimal` for all monetary values
- Consistent rounding rules (ROUND_HALF_UP)
- Validation of precision in calculations

### Currency Awareness
All functions are designed with multi-currency support:
- Currency parameters in all relevant functions
- Automatic currency detection where possible
- Exchange rate integration throughout

### Repository Independence
Financial calculations work with data from any repository:
- Accept data models as parameters
- No direct file or database access
- Pure calculation functions for testability

## Testing

The financial module includes comprehensive tests:
- Precision validation for all calculations
- Edge case testing (zero values, negative numbers)
- Currency conversion accuracy
- Performance regression tests

## Future Enhancements

Planned improvements for database migration:
- Real-time exchange rate updates
- Historical exchange rate storage
- Advanced performance analytics
- Tax calculation utilities
- Multi-portfolio support