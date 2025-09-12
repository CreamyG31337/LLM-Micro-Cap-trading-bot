# Config Module

The config module provides centralized configuration management for the trading system. It handles settings loading, environment variable integration, and configuration for different deployment scenarios.

## Structure

```
config/
├── settings.py     # Configuration management system
├── constants.py    # System constants and default values
└── README.md      # This file
```

## Settings (`settings.py`)

Provides comprehensive configuration management with support for multiple configuration sources:

### Key Features
- **Multiple Sources**: Configuration files, environment variables, defaults
- **Repository Selection**: Choose between CSV and database backends
- **Environment Awareness**: Different settings for development, testing, production
- **Validation**: Configuration validation with clear error messages
- **Hot Reload**: Dynamic configuration updates (future enhancement)

### Configuration Sources (Priority Order)
1. **Environment Variables**: Highest priority for deployment flexibility
2. **Configuration Files**: JSON/YAML configuration files
3. **Default Values**: Built-in sensible defaults

### Usage Example
```python
from config.settings import Settings

# Load configuration
settings = Settings()

# Get repository configuration
repo_type = settings.get_repository_type()  # 'csv' or 'database'
data_dir = settings.get_data_directory()

# Get database configuration (when using database backend)
db_config = settings.get_database_config()
```

### Configuration Structure
```json
{
  "repository": {
    "type": "csv",
    "csv": {
      "data_directory": "my trading",
      "backup_enabled": true,
      "backup_retention_days": 30
    },
    "database": {
      "host": "localhost",
      "port": 5432,
      "database": "trading_system",
      "username": "trading_user",
      "password": "${DB_PASSWORD}",
      "pool_size": 10,
      "ssl_mode": "require"
    }
  },
  "market_data": {
    "primary_source": "yahoo",
    "enable_fallbacks": true,
    "cache_duration_minutes": 15,
    "timeout_seconds": 30
  },
  "display": {
    "use_rich": true,
    "use_colors": true,
    "max_table_width": 120,
    "currency_display": "symbol"
  },
  "logging": {
    "level": "INFO",
    "file": "trading_system.log",
    "max_size_mb": 10,
    "backup_count": 5
  }
}
```

### Environment Variables
Key environment variables for deployment:
- `TRADING_DATA_DIR`: Override data directory location
- `TRADING_REPO_TYPE`: Force repository type ('csv' or 'database')
- `TRADING_DB_HOST`: Database host
- `TRADING_DB_PASSWORD`: Database password
- `TRADING_LOG_LEVEL`: Logging level
- `TRADING_CONFIG_FILE`: Custom configuration file path

## Constants (`constants.py`)

Defines system-wide constants and default values:

### Key Constants
- **File Paths**: Default file names and directory structures
- **Market Timing**: Trading hours, market holidays, timezone defaults
- **Display Formatting**: Default table widths, number formats, colors
- **Financial Precision**: Decimal places, rounding rules, currency codes
- **System Limits**: Maximum values, timeout defaults, retry counts

### Constant Categories

#### File System Constants
```python
# Default file names
PORTFOLIO_FILE = "llm_portfolio_update.csv"
TRADE_LOG_FILE = "llm_trade_log.csv"
CASH_BALANCE_FILE = "cash_balances.json"
EXCHANGE_RATES_FILE = "exchange_rates.csv"

# Directory structure
DEFAULT_DATA_DIR = "my trading"
BACKUP_DIR = "backups"
TEST_DATA_DIR = "test_data"
```

#### Market Constants
```python
# Market timing
MARKET_TIMEZONE = "America/New_York"
MARKET_OPEN_TIME = "09:30"
MARKET_CLOSE_TIME = "16:00"

# Trading days
TRADING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MARKET_HOLIDAYS = [...]  # List of market holidays
```

#### Display Constants
```python
# Table formatting
DEFAULT_TABLE_WIDTH = 120
MIN_TABLE_WIDTH = 80
MAX_TABLE_WIDTH = 200

# Color schemes
SUCCESS_COLOR = "green"
ERROR_COLOR = "red"
WARNING_COLOR = "yellow"
INFO_COLOR = "blue"
```

#### Financial Constants
```python
# Precision settings
DECIMAL_PLACES = 2
SHARE_DECIMAL_PLACES = 6
PERCENTAGE_DECIMAL_PLACES = 2

# Currency settings
DEFAULT_CURRENCY = "CAD"
SUPPORTED_CURRENCIES = ["CAD", "USD", "EUR", "GBP"]
```

## Configuration Management

### Development vs Production
Different configuration strategies for different environments:

#### Development Configuration
```json
{
  "repository": {
    "type": "csv",
    "csv": {
      "data_directory": "test_data"
    }
  },
  "logging": {
    "level": "DEBUG",
    "console": true
  },
  "market_data": {
    "cache_duration_minutes": 1
  }
}
```

#### Production Configuration
```json
{
  "repository": {
    "type": "database",
    "database": {
      "host": "${DB_HOST}",
      "password": "${DB_PASSWORD}",
      "ssl_mode": "require"
    }
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/trading_system.log"
  },
  "market_data": {
    "cache_duration_minutes": 15
  }
}
```

### Configuration Validation
Comprehensive validation ensures configuration correctness:

#### Repository Configuration
- Validate repository type is supported
- Check CSV directory exists and is writable
- Validate database connection parameters
- Verify required credentials are provided

#### Market Data Configuration
- Validate timeout values are reasonable
- Check cache duration is positive
- Verify supported data sources are configured

#### Display Configuration
- Validate color schemes are supported
- Check table width limits
- Verify font and theme settings

### Configuration Loading Process
1. **Load Defaults**: Start with built-in default values
2. **Load Config File**: Override with configuration file values
3. **Apply Environment**: Override with environment variables
4. **Validate**: Ensure all required settings are present and valid
5. **Initialize**: Set up logging and other system components

## Integration with Other Modules

### Repository Factory Integration
The settings system directly controls repository selection:
```python
from config.settings import Settings
from data.repositories.repository_factory import RepositoryFactory

settings = Settings()
repository = RepositoryFactory.create_repository(settings)
```

### Logging Configuration
Settings control logging behavior throughout the system:
```python
import logging
from config.settings import Settings

settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.get_log_level()),
    filename=settings.get_log_file(),
    format=settings.get_log_format()
)
```

### Module Configuration
Each module can access its specific configuration:
```python
from config.settings import Settings

settings = Settings()
market_config = settings.get_market_data_config()
display_config = settings.get_display_config()
```

## Testing Configuration

Special configuration handling for testing environments:

### Test Configuration
```json
{
  "repository": {
    "type": "csv",
    "csv": {
      "data_directory": "test_data"
    }
  },
  "market_data": {
    "enable_fallbacks": false,
    "use_mock_data": true
  },
  "logging": {
    "level": "WARNING",
    "console": false
  }
}
```

### Mock Configuration
For unit testing, configuration can be mocked:
```python
from unittest.mock import patch
from config.settings import Settings

with patch.object(Settings, 'get_repository_type', return_value='csv'):
    # Test code here
    pass
```

## Future Database Migration

The configuration system is designed to support seamless database migration:

### Migration Configuration
```json
{
  "migration": {
    "source": {
      "type": "csv",
      "directory": "my trading"
    },
    "target": {
      "type": "database",
      "connection": "postgresql://user:pass@localhost/trading"
    },
    "options": {
      "backup_before_migration": true,
      "validate_after_migration": true,
      "preserve_csv_files": true
    }
  }
}
```

### Dual Mode Operation
During migration, the system can operate in dual mode:
```json
{
  "repository": {
    "type": "dual",
    "primary": "database",
    "fallback": "csv",
    "sync_mode": "write_through"
  }
}
```

## Security Considerations

### Sensitive Data Handling
- Passwords and API keys stored in environment variables
- Configuration files exclude sensitive information
- Secure defaults for database connections
- Audit logging for configuration changes

### Access Control
- File permissions for configuration files
- Environment variable access control
- Configuration validation prevents injection attacks
- Secure configuration loading process

## Performance Considerations

### Configuration Caching
- Settings cached after initial load
- Minimal overhead for configuration access
- Hot reload capability for dynamic updates
- Memory-efficient configuration storage

### Startup Performance
- Fast configuration loading
- Lazy initialization where possible
- Minimal validation overhead
- Efficient default value handling