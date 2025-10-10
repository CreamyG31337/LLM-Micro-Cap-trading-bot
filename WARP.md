# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## CRITICAL DEVELOPMENT RULES

### 🚨 MANDATORY: Always Run Tests Before Code Changes
```bash
# ALWAYS run this before making any code changes
python -m pytest tests/ -v

# For quick validation during development
python run_tests.py
```

### 📁 MANDATORY: Debug File Organization
- **ALL debug scripts** must go in `debug/` folder
- **ALL temporary files** (*.txt, *.log, debug_*.py, fix_*.py) go in `debug/`
- **NO debug files** in root directory
- **Clean up** after debugging sessions

## Common Development Commands

### Environment Setup
Always activate the virtual environment before running commands:
```bash
.\\venv\\Scripts\\activate
```

### Build/Lint/Test Commands

#### Type Checking
```bash
mypy trading_script.py
```

#### Linting and Code Quality
```bash
# Check code style and quality
ruff check trading_script.py

# Auto-fix issues
ruff check --fix trading_script.py
```

#### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_financial_calculations.py -v

# Run tests with coverage
python -m pytest tests/ --cov=.

# Interactive test runner
python run_tests.py
```

#### Development Mode (with detailed logging)
```bash
python dev_run.py --data-dir "trading_data/funds/TEST"
```

### Running the Trading System

#### Production Mode
```bash
python trading_script.py --data-dir "trading_data/funds/Project Chimera"
```

#### Development/Testing Mode (recommended)
```bash
python trading_script.py --data-dir "trading_data/funds/TEST"
```

#### Run Single Test
```bash
# Test specific module
python -m pytest tests/test_financial_calculations.py::TestPnLCalculations::test_daily_pnl_calculation -v

# Debug specific test cases
python debug/test_fifo_system.py
```

### Other Useful Commands
```bash
# Copy production data to test directory
cp "trading_data/funds/Project Chimera/*.csv" "trading_data/funds/TEST/"

# Generate performance graphs
python "Scripts and CSV Files/Generate_Graph.py"
```

## High-Level Code Architecture

This is a **modular Python trading system** with **repository pattern** for data abstraction and **dependency injection** for component management.

### Core Architecture Principles

1. **Repository Pattern**: Data access is abstracted through the `BaseRepository` interface, currently implemented with CSV files but designed to support database migration
2. **Modular Design**: Each domain (portfolio, market data, financial calculations) has its own module with clear interfaces
3. **FIFO Lot Tracking**: Industry-standard First-In-First-Out accounting method for position tracking and P&L calculations
4. **Dual Currency Support**: CAD/USD portfolio management with currency-aware calculations
5. **Configuration-Driven**: Settings managed through `config/settings.py` with environment variable overrides

### Key Architectural Components

#### Data Layer (`data/`)
- **Models**: `Position`, `PortfolioSnapshot`, `Trade`, `Lot` - core business entities with Decimal precision
- **Repositories**: Abstract data access with CSV implementation, designed for database migration
- **Repository Factory**: Dependency injection container for repository instances

#### Business Logic Modules
- **`portfolio/`**: Portfolio management, FIFO trade processing, position calculations, trading interface
- **`market_data/`**: Market data fetching (Yahoo Finance primary, Stooq fallback), market hours handling, price caching
- **`financial/`**: P&L calculations, currency handling, cost basis calculations with Decimal precision
- **`display/`**: Terminal output formatting, Rich table generation with color coding, console utilities with emoji support

#### Configuration and Utilities
- **`config/`**: Settings management with JSON file and environment variable support
- **`utils/`**: Timezone handling, validation, backup management, system utilities
- **`debug/`**: Comprehensive debugging tools for price data, P&L calculations, and FIFO system testing

### Data Flow Architecture

1. **Trading Script** (`trading_script.py`) - Main orchestrator with dependency injection
2. **Repository Layer** - Abstracts CSV/database operations through `BaseRepository`
3. **Business Logic** - Domain-specific managers handle portfolio, market data, and financial calculations
4. **Display Layer** - Terminal formatting and user interface

### Database Migration Design

The system is architected for seamless migration from CSV to database:
- **Repository interface** abstracts data access
- **Data models** serialize to/from both CSV and database formats
- **Configuration system** supports multiple repository types
- **Migration tools** planned in `data/repositories/migration/`

### Financial Calculations Architecture

- **FIFO Lot Tracking**: Each purchase creates a separate lot; sells consume oldest lots first
- **Decimal Precision**: All financial calculations use `decimal.Decimal` for accuracy
- **Currency Conversion**: Handles CAD/USD conversions with proper exchange rates
- **Daily P&L**: Industry-standard close-to-close price comparison with market hours handling
- **5-Day P&L with Partial Periods**: Shows full 5-day P&L when available, falls back to 2-4 day periods with yellow color coding for newer positions

## Development Guidelines

### Windows Environment Considerations
- This is a **Windows environment** - use Windows-specific commands and paths
- Always use `trading_data/funds/TEST/` directory for development (not `trading_data/funds/Project Chimera/` which is production)
- Activate virtual environment with `.\\venv\\Scripts\\activate`


### Code Quality Requirements
- **Python 3.11+** required
- **Strict typing** with mypy enabled
- **Financial calculations** must use `decimal.Decimal`
- **Timezone-aware** datetime handling
- **Error handling** with specific exception types
- **Comprehensive logging** for debugging

### Testing Requirements
- **Always run unit tests** before committing changes
- Write tests for all financial calculations
- Test edge cases and error conditions
- Mock external dependencies (Yahoo Finance, etc.)

### File Structure Guidelines
- **Modular architecture** with single responsibility modules
- **Repository pattern** for data access
- **Separate business logic** from presentation
- **Configuration-driven** components

### Important Notes for Development

1. **Data Safety**: Always use `trading_data/funds/TEST/` directory during development to avoid affecting production data in `trading_data/funds/Project Chimera/`

2. **Financial Accuracy**: This system handles real money - all financial calculations must use `Decimal` type, never float

3. **FIFO System**: The lot tracking system follows industry standards for tax optimization and proper P&L calculation

4. **Market Hours**: The system is timezone-aware (PST) and handles pre-market, market hours, after-hours, and weekend scenarios

5. **Testing Culture**: The codebase has comprehensive test coverage for financial calculations - maintain this standard

## Important File Locations

- **Production Data**: `trading_data/funds/Project Chimera/`
- **Test Data**: `trading_data/funds/TEST/` (use for development)
- **Main Script**: `trading_script.py`
- **Development Runner**: `dev_run.py`
- **Configuration**: `config/settings.py`
- **Tests**: `tests/` directory
- **Debug Tools**: `debug/` directory

## Project Context

This is a **fork** of the ChatGPT Micro-Cap Experiment focused on enhanced portfolio tracking and dual currency support (CAD/USD). The system uses LLM-assisted trading analysis while maintaining professional-grade financial accuracy and audit trails.

Key features include FIFO lot tracking, real-time market data integration, comprehensive P&L calculations with intelligent partial-period display, color-coded portfolio tables, and a modular architecture designed for future database migration and web dashboard development.

### Caching and Performance

#### Python Import Caching
- **Python bytecode caching**: Python caches compiled bytecode (.pyc files) which can persist code changes
- **Module reload required**: After code changes, especially in imported modules like `display/table_formatter.py`, you may need to:
  - Restart the Python process/terminal session
  - Use `importlib.reload()` for development
  - Delete `__pycache__/` directories if experiencing stale code issues

#### Market Data Caching
- **Price data**: Market data is cached to avoid excessive API calls
- **Cache location**: Fund directories under `trading_data/funds/` contain cached CSV files
- **Cache refresh**: Use `--refresh-cache` flag or delete old CSV files to force refresh

### Recent Enhancements

- **Enhanced 5-Day P&L Display**: Intelligently shows 2-4 day partial periods when full 5-day data unavailable
- **Smart Color Coding**: Green/red for full periods, yellow for partial periods, proper formatting without redundant minus signs
- **LLM Prompt Integration**: Multi-period P&L data included in generated prompts for AI trading analysis
- **Improved Column Layout**: Optimized table width (13 characters) for better display formatting
