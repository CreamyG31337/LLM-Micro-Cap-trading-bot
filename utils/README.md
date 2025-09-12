# Utils Module

The utils module provides essential utility functions for the trading system, including backup management, timezone handling, and data validation. These utilities are designed to work with both current CSV storage and future database backends.

## Structure

```
utils/
├── backup_manager.py   # Backup and restore functionality
├── timezone_utils.py   # Timezone handling and timestamp parsing
├── validation.py       # Data validation and integrity checks
└── README.md          # This file
```

## Backup Manager (`backup_manager.py`)

Provides comprehensive backup and restore functionality for trading data:

### Key Features
- **Timestamped Backups**: Automatic timestamping of all backups
- **Selective Backup**: Backup specific files or entire datasets
- **Restore Operations**: Point-in-time restore capabilities
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Repository Agnostic**: Supports both CSV and future database backends

### Backup Operations
- `create_backup()`: Create timestamped backup of all data
- `restore_from_backup()`: Restore data from specific backup
- `list_backups()`: List all available backups
- `cleanup_old_backups()`: Remove backups older than specified age
- `export_to_csv()`: Export database data to CSV format (future)

### Usage Example
```python
from utils.backup_manager import BackupManager
from pathlib import Path

# Initialize backup manager
backup_mgr = BackupManager(data_dir=Path("my trading"))

# Create backup
backup_name = backup_mgr.create_backup()
print(f"Backup created: {backup_name}")

# List available backups
backups = backup_mgr.list_backups()

# Restore from backup
backup_mgr.restore_from_backup(backup_name)
```

### Backup Strategies
- **Full Backups**: Complete copy of all trading data
- **Incremental Backups**: Only changed files (future enhancement)
- **Compressed Backups**: Space-efficient storage (future enhancement)
- **Remote Backups**: Cloud storage integration (future enhancement)

## Timezone Utils (`timezone_utils.py`)

Handles timezone-aware timestamp parsing and formatting:

### Key Features
- **CSV Timestamp Parsing**: Parse timestamps from CSV files with timezone awareness
- **Multiple Formats**: Support for various timestamp formats
- **Timezone Conversion**: Convert between different timezones
- **Market Hours Integration**: Timezone handling for different markets

### Core Functions
- `parse_csv_timestamp()`: Parse timestamps from CSV with timezone detection
- `format_timestamp_for_csv()`: Format timestamps for CSV output
- `get_trading_timezone()`: Get appropriate timezone for trading data
- `convert_timezone()`: Convert timestamps between timezones
- `is_market_timezone()`: Check if timestamp is in market timezone

### Usage Example
```python
from utils.timezone_utils import parse_csv_timestamp, format_timestamp_for_csv
from datetime import datetime

# Parse CSV timestamp
timestamp_str = "2024-01-15 09:30:00"
dt = parse_csv_timestamp(timestamp_str, default_tz="America/New_York")

# Format for CSV output
csv_format = format_timestamp_for_csv(datetime.now())
```

### Timezone Support
- **North American Markets**: Eastern Time (NYSE, NASDAQ, TSX)
- **European Markets**: CET/CEST timezone support
- **Asian Markets**: JST, HKT timezone support (future)
- **UTC Conversion**: Universal time coordination

## Validation (`validation.py`)

Provides comprehensive data validation and integrity checks:

### Key Features
- **Portfolio Validation**: Validate portfolio data structure and values
- **Trade Validation**: Ensure trade data integrity
- **Financial Precision**: Validate monetary calculations for precision
- **Data Integrity**: Cross-reference validation between related data

### Validation Functions
- `validate_portfolio_data()`: Complete portfolio data validation
- `validate_trade_data()`: Trade record validation
- `validate_money_precision()`: Check for floating-point precision issues
- `validate_ticker_format()`: Ensure ticker symbols are properly formatted
- `check_data_integrity()`: Cross-validation of related data

### Validation Rules

#### Portfolio Validation
- All monetary values are positive (except P&L)
- Shares quantities are non-negative
- Ticker symbols follow proper format
- Currency codes are valid ISO codes
- Timestamps are properly formatted

#### Trade Validation
- Trade actions are valid (BUY/SELL)
- Prices are positive numbers
- Share quantities are positive
- Timestamps are within reasonable ranges
- Currency codes match position currencies

### Usage Example
```python
from utils.validation import validate_portfolio_data, validate_trade_data

# Validate portfolio
is_valid, errors = validate_portfolio_data(portfolio_snapshot)
if not is_valid:
    print(f"Portfolio validation errors: {errors}")

# Validate trade
trade_valid, trade_errors = validate_trade_data(trade)
if not trade_valid:
    print(f"Trade validation errors: {trade_errors}")
```

### Error Reporting
- **Detailed Error Messages**: Specific information about validation failures
- **Error Categorization**: Group errors by type and severity
- **Suggested Fixes**: Recommendations for fixing validation issues
- **Batch Validation**: Validate multiple records with consolidated reporting

## Integration with Other Modules

### Repository Pattern Integration
All utilities work seamlessly with the repository pattern:
- Backup manager supports both CSV and database backends
- Validation works with data models from any repository
- Timezone utilities handle timestamps from any source

### Configuration Integration
Utilities respect system configuration:
- Backup retention policies from settings
- Timezone preferences from configuration
- Validation rules from system settings

### Logging Integration
Comprehensive logging throughout all utilities:
- Backup operations logged with timestamps
- Validation results logged for audit trails
- Timezone conversions logged for debugging

## Error Handling

Robust error handling across all utilities:

### Backup Errors
- `BackupError`: General backup operation failures
- `RestoreError`: Restore operation failures
- `StorageError`: Insufficient storage space
- `PermissionError`: File access permission issues

### Validation Errors
- `ValidationError`: Data validation failures
- `IntegrityError`: Data integrity check failures
- `FormatError`: Data format validation failures

### Recovery Strategies
- Automatic retry for transient errors
- Graceful degradation when possible
- Clear error messages with suggested actions

## Configuration

Utility behavior can be configured through settings:

```json
{
  "utils": {
    "backup": {
      "retention_days": 30,
      "compression": false,
      "auto_backup": true,
      "backup_schedule": "daily"
    },
    "timezone": {
      "default_timezone": "America/New_York",
      "market_timezone": "America/New_York",
      "display_timezone": "local"
    },
    "validation": {
      "strict_mode": true,
      "precision_tolerance": 0.005,
      "require_currency": true
    }
  }
}
```

## Testing

Comprehensive testing ensures utility reliability:

### Unit Tests
- Individual function testing with various inputs
- Edge case validation (empty data, invalid formats)
- Error condition testing

### Integration Tests
- Cross-module integration validation
- Repository pattern compatibility
- Configuration system integration

### Performance Tests
- Large dataset handling
- Backup/restore performance
- Validation performance with large portfolios

## Future Enhancements

Planned improvements for database migration:

### Advanced Backup Features
- **Incremental Backups**: Only backup changed data
- **Compressed Backups**: Space-efficient storage
- **Cloud Integration**: AWS S3, Google Cloud Storage
- **Automated Scheduling**: Cron-like backup scheduling

### Enhanced Validation
- **Schema Validation**: Database schema compliance
- **Business Rule Validation**: Complex business logic checks
- **Real-time Validation**: Live validation during data entry
- **Custom Validation Rules**: User-defined validation logic

### Timezone Enhancements
- **Multiple Market Support**: Global market timezone handling
- **Daylight Saving**: Automatic DST transitions
- **Historical Timezone**: Handle timezone changes over time
- **User Preferences**: Per-user timezone settings