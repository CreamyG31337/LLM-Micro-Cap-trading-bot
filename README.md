# LLM Micro-Cap Trading Bot

**Fork of:** [ChatGPT Micro-Cap Experiment](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment)

This is a personal fork focused on enhanced portfolio tracking, dual currency support (CAD/USD), and improved LLM-assisted trading analysis. For the original concept and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Quick Start
- **Getting Started Guide**: [Original Setup Instructions](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Start%20Your%20Own/README.md)
- **Run with test data**: `python trading_script.py --data-dir trading_data/dev`
- **Production data**: Use `trading_data/prod/` folder (gitignored)

## Repository Structure

- **`trading_script.py`** - Main trading engine with portfolio management and stop-loss automation
- **`trading_data/prod/`** - **Production data folder** (gitignored) - Your real trading data
- **`trading_data/dev/`** - **Test environment** - Safe copies for development and testing
- **`Scripts and CSV Files/`** - My personal portfolio (updates every trading day)
- **`Weekly Deep Research (MD|PDF)/`** - Research summaries and performance reports
- **`Experiment Details/`** - Documentation, methodology, prompts, and Q&A

## Key Features

This fork enhances the original with:

- **Dual Currency Support** - CAD/USD portfolio management with manual cash balance updates
- **Enhanced Portfolio Tracking** - Real-time price integration and improved P&L calculations with optimized table formatting
- **FIFO Lot Tracking** - Industry-standard accounting with realized/unrealized P&L
- **Better User Experience** - Terminal optimization, virtual environment checks, and interactive menus
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

*For performance data and results, see the CSV files in `trading_data/prod/` and `trading_data/dev/` folders.*

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
python debug/rebuild_portfolio_from_scratch.py trading_data/dev
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
3. **Configure your data directories** (use `trading_data/dev/` for testing, `trading_data/prod/` for production)
4. **Run the trading script** with `python trading_script.py --data-dir trading_data/dev`

For the original setup guide and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Contributing

This is a personal fork, but contributions are welcome! If you have ideas for improvements or find bugs:

- **Issues:** Report bugs or suggest enhancements
- **Pull Requests:** Submit improvements for review
- **Discussion:** Share ideas for new features

Whether it's fixing a typo, adding features, or discussing new ideas, all contributions are appreciated!
