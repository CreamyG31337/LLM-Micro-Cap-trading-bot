"""System constants and default values."""

from pathlib import Path

# File paths and names
DEFAULT_DATA_DIR = "my trading"
PORTFOLIO_CSV_NAME = "llm_portfolio_update.csv"
TRADE_LOG_CSV_NAME = "llm_trade_log.csv"
CASH_BALANCES_JSON_NAME = "cash_balances.json"
FUND_CONTRIBUTIONS_CSV_NAME = "fund_contributions.csv"
EXCHANGE_RATES_CSV_NAME = "exchange_rates.csv"

# Backup configuration
DEFAULT_BACKUP_DIR = "backups"
MAX_BACKUP_FILES = 10

# Market timing constants
MARKET_OPEN_HOUR = 6  # 6:30 AM PDT
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 13  # 1:00 PM PDT
MARKET_CLOSE_MINUTE = 0

# Default timezone configuration
DEFAULT_TIMEZONE_NAME = "PST"
DEFAULT_TIMEZONE_OFFSET = -8
DEFAULT_UTC_OFFSET = "-08:00"

# Market data configuration
DEFAULT_MARKET_DATA_SOURCE = "yahoo"
FALLBACK_MARKET_DATA_SOURCE = "stooq"
DEFAULT_CACHE_DURATION_HOURS = 24

# Default benchmarks
DEFAULT_BENCHMARKS = ["SPY", "QQQ", "IWM", "^GSPTSE"]

# Currency configuration
DEFAULT_CURRENCY = "CAD"
DEFAULT_USD_CAD_RATE = 1.38

# Display configuration
DEFAULT_TERMINAL_WIDTH = 120
MIN_TERMINAL_WIDTH = 80

# Logging configuration
LOG_FILE = "trading_bot_dev.log"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Version information
VERSION = "2.0.0"

# Repository configuration
DEFAULT_REPOSITORY_TYPE = "csv"

# Database configuration (for future use)
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_NAME = "trading_system"
DEFAULT_DB_USER = "trading_user"
DEFAULT_SSL_MODE = "prefer"

# File extensions
CSV_EXTENSION = ".csv"
JSON_EXTENSION = ".json"
BACKUP_EXTENSION = ".backup"

# CSV column names (for backward compatibility)
PORTFOLIO_CSV_COLUMNS = [
    'Date', 'Ticker', 'Shares', 'Average Price', 'Cost Basis', 
    'Stop Loss', 'Current Price', 'Total Value', 'PnL', 'Action', 
    'Company', 'Currency'
]

TRADE_LOG_CSV_COLUMNS = [
    'Date', 'Ticker', 'Shares Bought', 'Buy Price', 
    'Cost Basis', 'PnL', 'Reason'
]

# Validation constants
MIN_SHARE_COUNT = 0.0001
MAX_SHARE_COUNT = 1000000
MIN_PRICE = 0.01
MAX_PRICE = 100000
MIN_COST_BASIS = 0.01
MAX_COST_BASIS = 10000000

# Error messages
ERROR_INVALID_TICKER = "Invalid ticker symbol"
ERROR_INVALID_SHARES = "Invalid share count"
ERROR_INVALID_PRICE = "Invalid price"
ERROR_FILE_NOT_FOUND = "File not found"
ERROR_PERMISSION_DENIED = "Permission denied"
ERROR_INVALID_DATA = "Invalid data format"
ERROR_NETWORK_ERROR = "Network error"
ERROR_MARKET_CLOSED = "Market is closed"

# Success messages
SUCCESS_TRADE_SAVED = "Trade saved successfully"
SUCCESS_PORTFOLIO_UPDATED = "Portfolio updated successfully"
SUCCESS_BACKUP_CREATED = "Backup created successfully"
SUCCESS_DATA_RESTORED = "Data restored successfully"

# Warning messages
WARNING_MARKET_CLOSED = "Market is currently closed"
WARNING_WEEKEND_TRADING = "Weekend trading detected"
WARNING_MISSING_DATA = "Some data is missing"
WARNING_STALE_PRICES = "Price data may be stale"

# Info messages
INFO_USING_FALLBACK = "Using fallback data source"
INFO_CACHE_HIT = "Using cached data"
INFO_CACHE_MISS = "Cache miss, fetching fresh data"
INFO_BACKUP_SKIPPED = "Backup skipped (disabled)"