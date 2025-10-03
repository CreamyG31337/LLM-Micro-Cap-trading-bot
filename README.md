# LLM Micro-Cap Trading Bot

**Fork of:** [ChatGPT Micro-Cap Experiment](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment)

This is a personal fork focused on enhanced portfolio tracking, dual currency support (CAD/USD), and improved LLM-assisted trading analysis. For the original concept and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Quick Start
- **Getting Started Guide**: [Original Setup Instructions](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Start%20Your%20Own/README.md)
- **Run with test data**: `python trading_script.py --data-dir "trading_data/funds/TEST"`
- **Production data**: Use `trading_data/funds/Project Chimera/` folder

## Repository Structure

- **`trading_script.py`** - Main trading engine with portfolio management and stop-loss automation
- **`trading_data/funds/Project Chimera/`** - **Production data folder** - Your real trading data
- **`trading_data/funds/TEST/`** - **Test environment** - Safe copies for development and testing
- **`Scripts and CSV Files/`** - My personal portfolio (updates every trading day)
- **`Weekly Deep Research (MD|PDF)/`** - Research summaries and performance reports
- **`Experiment Details/`** - Documentation, methodology, prompts, and Q&A

## Key Features

This fork enhances the original with:

- **Dual Currency Support** - CAD/USD portfolio management with manual cash balance updates
- **Enhanced Portfolio Tracking** - Real-time price integration and improved P&L calculations with optimized table formatting
- **FIFO Lot Tracking** - Industry-standard accounting with realized/unrealized P&L
- **Better User Experience** - Terminal optimization, virtual environment checks, and interactive menus
- **Single-Key Menu System** - Quick access to all functions with single key presses for maximum efficiency
- **Dual Repository Support** - Switch between CSV (local) and Supabase (cloud) backends with a single command
- **Comprehensive Debugging** - Multiple debug tools for troubleshooting and analysis
- **Configurable Timezone Support** - Flexible timezone handling for different markets
- **Cache Management System** - Monitor, clear, and update cached data with dedicated UI

## Cache Management

The system includes comprehensive cache management to handle cached market data, exchange rates, and company fundamentals:

### Quick Cache Management
```bash
# From main menu - select option 'k'
python run.py

# From trading script - select 'cache'
python trading_script.py --data-dir "your_fund"
```

### Cache Types
- **Price Cache**: Stock prices and market data
- **Fundamentals Cache**: Company financial information
- **Exchange Rate Cache**: Currency conversion rates
- **Memory Caches**: Runtime data for performance

### When to Use Cache Management
- **Stale Data**: Clear caches when data appears outdated
- **Display Issues**: Clear caches for table formatting problems
- **Performance Issues**: Monitor and clear excessive cache sizes
- **Troubleshooting**: First step when experiencing data inconsistencies

### Cache Management Commands
```bash
# View cache status
python run.py  # Select 'k' -> View Cache Status

# Clear specific cache
python run.py  # Select 'k' -> Clear Specific Cache

# Clear all caches (emergency)
python run.py  # Select 'k' -> Clear All Caches
```

For detailed cache management documentation, see [`docs/CACHE_MANAGEMENT.md`](docs/CACHE_MANAGEMENT.md).

## Single-Key Menu System

The trading bot features a streamlined single-key menu system for maximum efficiency and speed:

### **Quick Access Menu:**
- **'b'** - Buy
- **'s'** - Sell  
- **'c'** - Log Contribution
- **'w'** - Log Withdrawal
- **'m'** - Manage Contributors
- **'u'** - Update Cash Balances
- **'r'** - Refresh Portfolio
- **'f'** - Switch Fund (Quick fund switching - 70% faster than before!)
- **'d'** - Switch Repository (CSV/Supabase)
- **'o'** - Sort Portfolio
- **'9'** - Clean Old Backups
- **'0'** - Backup Statistics
- **Enter** - Quit

### **Benefits:**
- **Speed & Efficiency**: Single key press for all actions
- **No Typing**: No need to type multi-character commands
- **Consistent**: All menu options follow same pattern
- **Intuitive**: Easy to remember and use
- **Professional**: Clean, efficient interface

### **Usage:**
1. **Run Trading Script**: `python trading_script.py`
2. **Press Single Key**: Choose any action with one key press
3. **Quick Navigation**: Switch between functions instantly
4. **Reduced Errors**: Less chance of typos or mistakes

### **Enhanced Fund Switching:**
- **70% Faster**: Only 2 key presses instead of 6 for fund switching
- **Direct Access**: Press 'f' from main menu for instant fund switching
- **Intuitive Navigation**: Enter key for "back" and "cancel" operations
- **Unicode Safe**: Works on all console types with emoji fallbacks

## Dual Repository System

The trading bot supports both local CSV files and cloud Supabase database with seamless switching:

### **Repository Options:**
- **CSV (Local)**: Fast, offline-capable, perfect for development and debugging
- **Supabase (Cloud)**: Scalable, web-accessible, ideal for production and web dashboard

### **Quick Repository Switch:**
```bash
# Switch to CSV (local files)
python simple_repository_switch.py csv

# Switch to Supabase (cloud database)  
python simple_repository_switch.py supabase

# Check current status
python simple_repository_switch.py status

# Test current setup
python simple_repository_switch.py test
```

### **From Trading Script Menu:**
- **Press 'd'** - Switch Repository (CSV/Supabase)
- **Interactive Menu** - Shows current status and available options
- **Automatic Testing** - Tests repository after switching
- **Safety Prompts** - Confirmation for cloud database switch

### **Architecture Benefits:**
- **Zero Code Changes**: Business logic works with both repositories
- **Perfect Separation**: Data access completely abstracted from business logic
- **Easy Migration**: Switch between backends with one command
- **Data Safety**: Both repositories can be kept in sync

### **Configuration:**
```json
// CSV Configuration
{
  "repository": {
    "type": "csv",
    "data_directory": "trading_data/funds/Project Chimera"
  }
}

// Supabase Configuration
{
  "repository": {
    "type": "supabase", 
    "url": "https://your-project.supabase.co",
    "key": "your-anon-key",
    "fund": "Project Chimera"
  }
}
```

### **Environment Variables:**
```bash
# Set Supabase credentials
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Force repository type
export TRADING_REPO_TYPE="supabase"  # or "csv"
```

## System Safety & Data Protection

The trading bot includes comprehensive safety measures to protect your data:

### **Data Safety Features:**
- **Multiple Backups**: Timestamped backups in `backups/` directory
- **Repository Switching**: Instant switch between CSV and Supabase backends
- **Data Validation**: Regular integrity checks with `simple_verify.py`
- **Recovery Procedures**: Documented recovery processes for data restoration

### **Configuration Safety:**
- **Flat Configuration**: Simplified repository configuration structure
- **Environment Variables**: Secure credential management
- **Error Handling**: Graceful fallbacks and recovery procedures
- **Testing**: Automatic repository testing after configuration changes

### **System Integrity:**
- **Repository Pattern**: Perfect separation of concerns maintained
- **Zero Downtime**: Switch between backends without code changes
- **Validation Scripts**: Comprehensive data integrity verification
- **Backup Strategy**: Multiple layers of data protection

### **Recovery Commands:**
```bash
# Check system status
python simple_repository_switch.py status

# Test current setup
python simple_repository_switch.py test

# Verify data integrity
python simple_verify.py

# Switch to safe mode (CSV)
python simple_repository_switch.py csv
```

## Original Documentation

For the original concept, methodology, and research documentation, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment):

- [Original Concept & Vision](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment#the-concept)
- [Research Index](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Experiment%20Details/Deep%20Research%20Index.md)  
- [Disclaimer](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Experiment%20Details/Disclaimer.md)  
- [Q&A](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Experiment%20Details/Q%26A.md)  
- [Prompts](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Experiment%20Details/Prompts.md)  
- [Starting Your Own](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Start%20Your%20Own/README.md)  
- [Research Summaries (MD)](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/tree/main/Weekly%20Deep%20Research%20(MD))  
- [Full Deep Research Reports (PDF)](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/tree/main/Weekly%20Deep%20Research%20(PDF))
- [Chats](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Experiment%20Details/Chats.md)

## How the Trading Script Works

### Market Hours & CSV Updates
- **Market Hours**: 6:30 AM - 1:00 PM PST (9:30 AM - 4:00 PM EST)
- **CSV Updates**: Only occur during market hours and once per day
- **Price Display**: Always shows current prices (even after hours) but doesn't save them
- **New Stocks**: Only added to CSV when market is open, with Action = "BUY"

### Portfolio Management
- **One Row Per Day**: Each stock gets one row per day in the CSV
- **No Duplicates**: Script skips stocks that already exist for today
- **Historical Data**: Preserves all historical prices for graphing
- **Action Tracking**: Automatically sets Action = "BUY" for new stocks
- **Weekend Handling**: Portfolio rebuild automatically skips weekends (Saturday/Sunday) when adding HOLD entries since no market data is available

### Usage
1. **Run anytime**: Script works 24/7 for viewing data and managing portfolio
2. **Market hours**: CSV gets updated with current prices and new stocks
3. **After hours**: Shows prices but doesn't save to CSV
4. **Graphing**: Use the CSV data to generate portfolio performance charts

*For performance data and results, see the CSV files in the fund directories under `trading_data/funds/`.*

## Architecture

This trading bot is built using a modern, modular architecture that ensures maintainability, extensibility, and future-proofing. The system employs several key design patterns to achieve clean separation of concerns and facilitate easy migration between different data storage backends.

### Design Patterns

#### Repository Pattern (Data Access Abstraction)
The system uses the Repository pattern to abstract data access operations from business logic:

```python
# Business logic works with any repository implementation
class PortfolioManager:
    def __init__(self, repository: BaseRepository, fund: Fund):
        self.repository = repository  # Could be CSV, Database, or In-Memory
        self.fund = fund

    def load_portfolio(self) -> List[PortfolioSnapshot]:
        return self.repository.get_portfolio_data()
```

**Benefits:**
- **Backend Independence**: Switch between CSV files and databases without changing business logic
- **Easy Testing**: Mock repositories for unit testing
- **Future Migration**: Seamless transition to database backend
- **Consistent Interface**: Same API regardless of storage mechanism

#### Dependency Injection (Component Management)
Components are loosely coupled through dependency injection using the RepositoryContainer:

```python
# Global dependency injection container
class RepositoryContainer:
    def get_repository(self, name: str = 'default') -> BaseRepository:
        # Creates or returns cached repository instance
        return self._repositories[name]
```

**Benefits:**
- **Loose Coupling**: Components don't create their own dependencies
- **Testability**: Easy to inject mock dependencies for testing
- **Configuration**: Runtime configuration of different repository types
- **Singleton Management**: Shared instances managed centrally

#### Factory Pattern (Repository Creation)
Repository instances are created through a factory that handles different backend types:

```python
class RepositoryFactory:
    @classmethod
    def create_repository(cls, repository_type: str, **kwargs) -> BaseRepository:
        if repository_type == "csv":
            return CSVRepository(**kwargs)
        elif repository_type == "supabase":
            return SupabaseRepository(**kwargs)
        elif repository_type == "database":
            return DatabaseRepository(**kwargs)
```

**Benefits:**
- **Extensibility**: Easy to add new repository types
- **Centralized Creation**: Single point for repository instantiation logic
- **Configuration-Driven**: Repository type determined by configuration

#### Domain Model Pattern (Business Entities)
Business entities use dataclasses with rich serialization capabilities:

```python
@dataclass
class Position:
    ticker: str
    shares: Decimal
    avg_price: Decimal
    cost_basis: Decimal
    currency: str = "CAD"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create from dictionary (CSV row or database record)."""
```

**Benefits:**
- **Type Safety**: Strong typing with mypy validation
- **Immutability**: Dataclasses provide immutable value objects
- **Serialization**: Built-in conversion to/from CSV and database formats
- **Validation**: Centralized data validation and conversion logic

#### Service Layer Pattern (Business Logic Separation)
Business operations are encapsulated in service classes that use repositories:

```python
class PortfolioManager:
    """Manages portfolio data using the repository pattern."""

class PnLCalculator:
    """Handles all profit and loss calculations."""

class TradingInterface:
    """Coordinates trading operations and user interactions."""
```

**Benefits:**
- **Separation of Concerns**: Business logic separate from data access
- **Reusability**: Services can be used across different interfaces
- **Testability**: Easy to unit test business logic in isolation

### Modular Architecture

The codebase is organized into focused modules with clear responsibilities:

```
├── config/           # Configuration management
├── data/            # Data access layer
│   ├── models/      # Domain models (Position, Trade, PortfolioSnapshot)
│   └── repositories/# Repository implementations
├── portfolio/       # Portfolio management business logic
├── financial/       # Financial calculation services
├── market_data/     # Market data fetching and caching
├── display/         # User interface and formatting
└── utils/           # Shared utilities and helpers
```

### Configuration Management

The system uses a centralized configuration approach:

```python
class Settings:
    """Centralized configuration management."""

    def __init__(self, config_file: Optional[str] = None):
        self._config = self._load_default_config()
        if config_file:
            self.load_from_file(config_file)
        self._load_from_environment()
```

**Benefits:**
- **Environment Variables**: Secure credential management
- **File-Based Config**: Human-readable configuration files
- **Runtime Configuration**: Dynamic configuration loading
- **Validation**: Configuration validation and defaults

### Future Database Migration

The architecture is designed to support seamless migration from CSV files to a database backend:

#### Current State (CSV Repository)
- Local file-based storage
- Fast development and debugging
- Zero configuration needed
- Perfect for getting started

#### Future State (Database Repository)
- PostgreSQL backend with proper schema
- Scalable for large datasets
- Concurrent access support
- Web dashboard integration
- Transaction support and data integrity

#### Migration Strategy
1. **Phase 1**: Database setup and testing alongside CSV
2. **Phase 2**: Data migration with validation
3. **Phase 3**: Cutover with rollback capability

**Migration Benefits:**
- **Zero Downtime**: Run both systems in parallel during migration
- **Data Safety**: Comprehensive validation and backup procedures
- **Rollback Capability**: Easy reversion if issues arise
- **Performance**: Better performance for large portfolios

### Architecture Benefits

#### For Current Development
- **Easy Testing**: Mock repositories and isolated unit tests
- **Fast Iteration**: Quick development cycles with CSV backend
- **Simple Debugging**: Clear data flow and minimal dependencies
- **Type Safety**: Comprehensive type hints and validation

#### For Production Use
- **Scalability**: Ready for database migration when needed
- **Maintainability**: Clean separation enables easy modifications
- **Reliability**: Comprehensive error handling and validation
- **Extensibility**: Easy to add new features and repository types

#### For Long-term Evolution
- **Database Ready**: Architecture supports seamless database migration
- **Web Integration**: Repository pattern enables web dashboard development
- **Multi-tenancy**: Support for multiple funds and users
- **Performance**: Optimized for large-scale portfolio management

This architecture provides a solid foundation for both current CSV-based development and future database-backed production deployment, ensuring the system can grow and evolve with changing requirements.

## Tech Stack

### Core Technologies
- **Python** - Core scripting and automation
- **pandas + yFinance** - Market data fetching and analysis
- **Matplotlib** - Performance visualization and charting
- **ChatGPT-4** - AI-powered trading decision engine

### Advanced Features
- **Robust Data Sources** - Yahoo Finance primary, Stooq fallback for reliability
- **Interactive Portfolio Management** - Real-time price updates and position tracking
- **Backtesting Support** - ASOF_DATE override for historical analysis
- **Performance Analytics** - CAPM analysis, Sharpe/Sortino ratios, drawdown metrics
- **Comprehensive Trade Logging** - Complete transparency with detailed execution logs
- **Debug Tools** - Comprehensive analysis scripts for troubleshooting price data and P&L calculations

## Core Systems

### Daily P&L Calculation
Industry-standard daily P&L calculation with robust market hours handling:

- **Method**: Close-to-close price comparison (industry standard)
- **Market Hours**: Uses most recent close during market hours, 4 PM close after hours
- **Data Sources**: Yahoo Finance primary, Stooq fallback for reliability
- **Timezone**: PST with flexible configuration options
- **Error Handling**: Graceful fallback to "N/A" when insufficient data

### FIFO Lot Tracking System
**FIFO (First-In, First-Out)** lot tracking for industry-standard P&L calculation:

- **Method**: Oldest shares sold first (industry standard)
- **Benefits**: Tax advantages, accurate P&L tracking, audit trail
- **Portfolio Display**: Shows both unrealized P&L (current positions) and realized P&L (sold positions)
- **Example**: Buy 100 @ $100, then 100 @ $120, sell 100 @ $130 → Sells first lot, realized P&L = $3,000

### Portfolio Display Formatting
The portfolio snapshot table is optimized for standard display environments:

- **Target Resolution**: 1920x1080 with 125% scaling (Windows 11) - ~157 character terminal width
- **Responsive Design**: Adapts to different terminal sizes and capabilities
- **Column Optimization**: Daily P&L and Stop Loss columns balanced for readability
- **Color Coding**: Green for gains, red for losses, with clear visual indicators
- **Rich Formatting**: Beautiful tables with Rich library, graceful fallback to plain text

## Debug Tools

The repository includes comprehensive debugging tools in the `debug/` folder:

- **`daily_pnl_debug.py`** - Analyzes daily P&L calculation issues and data availability
- **`market_hours_analysis.py`** - Tests market hours handling and compares with industry standards
- **`price_debug.py`** - General price data debugging and validation
- **`comprehensive_price_debug.py`** - Advanced price data analysis and troubleshooting
- **`test_fifo_system.py`** - Unit tests for FIFO lot tracking system
- **`demo_fifo_integration.py`** - Demonstrates FIFO vs average cost comparison
- **`fifo_integration_plan.py`** - Integration guide and migration strategy
- **`rebuild_portfolio_from_scratch.py`** - Complete portfolio rebuild from trade log with weekend handling

These tools help ensure the trading system operates correctly and provide transparency into how calculations are performed.

### Portfolio Rebuild System

The `rebuild_portfolio_from_scratch.py` script provides a complete portfolio reconstruction system that can fix data inconsistencies and recover from corruption.

**What It Does:**
- **Complete Recreation**: Rebuilds the entire portfolio CSV from scratch using only the trade log
- **Chronological Processing**: Processes all trades in chronological order to ensure accuracy
- **Full Recalculation**: Recalculates all positions, cost basis, and P&L from first principles
- **HOLD Entry Generation**: Creates HOLD entries for price tracking between trades
- **Data Validation**: Ensures all calculations are consistent and accurate

**When to Use:**
- Portfolio CSV is corrupted or has inconsistent data
- Need to recover from a backup or data loss situation
- Want to verify that all calculations are mathematically correct
- Adding new features that require a fresh portfolio structure
- Debugging portfolio display or calculation issues

**Technical Features:**
- **Price Caching**: Uses PriceCache with MarketDataFetcher to minimize API calls and improve performance
- **Memory Efficiency**: Caches price data in memory to avoid redundant API requests for the same ticker/date
- **Timezone Handling**: Properly handles timezone-aware timestamps throughout the process
- **FIFO Implementation**: Implements proper FIFO lot tracking for accurate P&L calculations
- **Weekend Handling**: Automatically skips weekends when adding HOLD entries (no market data)
- **Error Recovery**: Gracefully handles missing price data and API failures

**Usage:**
```bash
# From main menu (option 'r')
python run.py

# Direct execution with different data directories
python debug/rebuild_portfolio_from_scratch.py "trading_data/funds/TEST"
python debug/rebuild_portfolio_from_scratch.py "my trading" "US/Pacific"
```

## Fund Management System

The trading bot includes a comprehensive fund management system for tracking multiple contributors and their ownership percentages.

### **How It Works**
- **Contributions**: Each $1 contributed = 1 share. Ownership percentage = (your shares / total shares) × 100%
- **Withdrawals**: Reduces your share count. Other contributors' ownership increases to maintain 100% total
- **Fair Performance Sharing**: All contributors benefit equally from fund performance regardless of when they joined
- **Protection**: Cannot withdraw more than your equity value

### **Managing Contributions & Withdrawals**

When you run the trading script, you'll see options for fund management:

```
Fund Management Options:
c - Add fund contribution
w - Process fund withdrawal
o - Show ownership percentages
```

### **Adding Contributions**
1. Select `c` from the main menu
2. Enter contributor name
3. Enter contribution amount
4. Add optional notes
5. The system automatically updates ownership percentages

### **Processing Withdrawals**
1. Select `w` from the main menu
2. Enter contributor name
3. Enter withdrawal amount
4. The system validates the withdrawal against their equity
5. If valid, processes the withdrawal and updates ownership

### **Viewing Ownership**
- Select `o` from the main menu to see current ownership percentages
- Ownership is calculated in real-time based on contributions
- Percentages always total exactly 100%

## System Requirements
- Python 3.11+
- Internet connection for market data
- ~10MB storage for CSV data files

## Getting Started

This fork includes all the original functionality plus enhanced features for portfolio tracking and analysis. To get started:

1. **Clone this repository**
2. **Set up your virtual environment** (see `debug/activate_venv.bat` for Windows)
3. **Configure your fund directories** (use `trading_data/funds/TEST/` for testing, `trading_data/funds/Project Chimera/` for production)
4. **Run the trading script** with `python trading_script.py --data-dir "trading_data/funds/TEST"`

For the original setup guide and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Contributing

This is a personal fork, but contributions are welcome! If you have ideas for improvements or find bugs:

- **Issues:** Report bugs or suggest enhancements
- **Pull Requests:** Submit improvements for review
- **Discussion:** Share ideas for new features

Whether it's fixing a typo, adding features, or discussing new ideas, all contributions are appreciated!
