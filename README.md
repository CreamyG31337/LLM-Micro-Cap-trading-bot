# LLM Micro-Cap Trading Bot

**Fork of:** [ChatGPT Micro-Cap Experiment](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment)

An advanced AI-powered trading bot for micro-cap stock analysis with dual currency support, comprehensive portfolio tracking, and seamless repository switching between local CSV files and cloud databases.

## Quick Start
- **Run with test data**: `python trading_script.py --data-dir "trading_data/funds/TEST"`
- **Production data**: Use `trading_data/funds/Project Chimera/` folder
- **Development mode**: `python dev_run.py --data-dir "trading_data/funds/TEST"`

## Repository Structure

- **`trading_script.py`** - Main trading engine with portfolio management and stop-loss automation
- **`trading_data/funds/Project Chimera/`** - **Production data folder** - Your real trading data
- **`trading_data/funds/TEST/`** - **Test environment** - Safe copies for development and testing
- **`Scripts and CSV Files/`** - My personal portfolio (updates every trading day)
- **`Weekly Deep Research (MD|PDF)/`** - Research summaries and performance reports
- **`Experiment Details/`** - Documentation, methodology, prompts, and Q&A

## Key Features

### **AI-Powered Trading Analysis**
- **LLM Integration** - Seamless integration with ChatGPT, Claude, and other AI models
- **Automated Prompt Generation** - Complete market analysis and portfolio reports
- **North American Focus** - Specialized for Canadian and US small-cap markets
- **Currency-Aware Analysis** - Handles CAD/USD markets with proper exchange rate conversion

### **Advanced Portfolio Management**
- **Dual Currency Support** - CAD/USD portfolio management with separate cash balances
- **FIFO Lot Tracking** - Industry-standard accounting with realized/unrealized P&L
- **Real-Time Price Integration** - Live market data with intelligent caching
- **Performance Analytics** - Sharpe ratio, drawdown analysis, and benchmark comparison

### **Flexible Data Storage**
- **Dual Repository System** - Switch between CSV (local) and Supabase (cloud) backends
- **Zero Downtime Migration** - Seamless switching without code changes
- **Data Safety** - Multiple backup layers and validation systems
- **Web Dashboard** - Cloud-accessible portfolio management interface

### **User Experience**
- **Single-Key Menu System** - Quick access to all functions with single key presses
- **Interactive Interface** - Streamlined menus for maximum efficiency
- **Cache Management** - Comprehensive cache monitoring and management
- **Development Tools** - Extensive debugging and testing capabilities

### **Web Dashboard**
- **Streamlit Interface** - Modern, responsive portfolio dashboard
- **Docker Container** - Production-ready deployment with CI/CD
- **Background Scheduler** - APScheduler for automated tasks (exchange rates, etc.)
- **Multi-User Auth** - Secure access with Supabase RLS policies
- **Performance Charts** - Interactive Plotly charts with benchmark comparison

### **AI Research System** 🆕
- **Automated News Collection** - Continuously monitors financial markets and portfolio holdings
- **AI-Powered Summaries** - Generates intelligent summaries with ticker/sector extraction
- **Semantic Search** - Vector embeddings enable natural language article search
- **ETF Intelligence** - Automatically researches sectors for ETF holdings
- **Opportunity Discovery** - Hunts for new investment opportunities
- **See [AI Research System Documentation](web_dashboard/AI_RESEARCH_SYSTEM.md)** for full details

## Daily Workflow

### **Simple Daily Routine**
1. **Run the trading script**: `python trading_script.py --data-dir "trading_data/funds/TEST"`
2. **Copy the generated prompt** (complete market analysis and portfolio report)
3. **Paste into your preferred LLM** (ChatGPT, Claude, WebAI, etc.)
4. **Execute the AI's trade recommendations** by running the script again
5. **Repeat daily** for continuous AI-driven trading

### **What the Script Does**
- **Loads your portfolio** from CSV or database
- **Shows cash balances** (CAD and USD)
- **Fetches current market data** for all positions and benchmarks
- **Generates performance metrics** (Sharpe ratio, drawdown, etc.)
- **Creates complete LLM prompt** with all your data and market context
- **Handles trade execution** when you follow the AI's recommendations

### **Cache Management**
The system includes intelligent cache management for optimal performance:

```bash
# Access cache management from main menu
python run.py  # Select 'k' for cache management

# Or from trading script
python trading_script.py --data-dir "your_fund"  # Select 'cache'
```

**Cache Types:**
- **Price Cache**: Stock prices and market data
- **Fundamentals Cache**: Company financial information  
- **Exchange Rate Cache**: Currency conversion rates
- **Memory Caches**: Runtime data for performance

For detailed cache management, see [`docs/CACHE_MANAGEMENT.md`](docs/CACHE_MANAGEMENT.md).

## Menu System

The trading bot features a streamlined single-key menu system for maximum efficiency:

### **Quick Access Menu:**
- **'b'** - Buy
- **'s'** - Sell  
- **'c'** - Log Contribution
- **'w'** - Log Withdrawal
- **'m'** - Manage Contributors
- **'u'** - Update Cash Balances
- **'r'** - Refresh Portfolio
- **'f'** - Switch Fund
- **'d'** - Switch Repository (CSV/Supabase)
- **'o'** - Sort Portfolio
- **'k'** - Cache Management
- **Enter** - Quit

### **Benefits:**
- **Speed & Efficiency**: Single key press for all actions
- **No Typing**: No need to type multi-character commands
- **Intuitive**: Easy to remember and use
- **Professional**: Clean, efficient interface

## Data Storage Options

The trading bot supports flexible data storage with seamless switching:

### **Storage Options:**
- **CSV (Local)**: Fast, offline-capable, perfect for development
- **Supabase (Cloud)**: Scalable, web-accessible, ideal for production

### **Quick Repository Switch:**
```bash
# Switch to CSV (local files)
python simple_repository_switch.py csv

# Switch to Supabase (cloud database)  
python simple_repository_switch.py supabase

# Check current status
python simple_repository_switch.py status
```

### **From Trading Script Menu:**
- **Press 'd'** - Switch Repository (CSV/Supabase)
- **Interactive Menu** - Shows current status and available options
- **Automatic Testing** - Tests repository after switching

## System Safety

The trading bot includes comprehensive safety measures:

### **Data Protection:**
- **Multiple Backups**: Timestamped backups in `backups/` directory
- **Repository Switching**: Instant switch between CSV and Supabase backends
- **Data Validation**: Regular integrity checks with `simple_verify.py`
- **Recovery Procedures**: Documented recovery processes for data restoration

### **Safety Commands:**
```bash
# Check system status
python simple_repository_switch.py status

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

## System Requirements

### **Core Requirements**
- **Python 3.11+** - Core scripting and automation
- **Internet connection** - For market data fetching
- **~10MB storage** - For CSV data files and cache
- **Windows/Linux/macOS** - Cross-platform support

### **Optional Requirements**
- **Supabase account** - For cloud database features
- **Web browser** - For web dashboard access
- **Virtual environment** - Recommended for Python dependency management

## Getting Started

### **Quick Setup**
1. **Clone this repository**
2. **Set up virtual environment**: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Run with test data**: `python trading_script.py --data-dir "trading_data/funds/TEST"`

### **Development Mode**
For development with enhanced error checking:
```bash
python dev_run.py --data-dir "trading_data/funds/TEST"
```

### **Testing**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python run_tests.py portfolio_display
python run_tests.py financial
```

## Fund Management

The trading bot includes comprehensive fund management for tracking multiple contributors:

### **How It Works**
- **Contributions**: Each $1 contributed = 1 share
- **Ownership**: Calculated as (your shares / total shares) × 100%
- **Fair Performance**: All contributors benefit equally from fund performance
- **Protection**: Cannot withdraw more than your equity value

### **Managing Contributions**
- **Press 'c'** - Add fund contribution
- **Press 'w'** - Process fund withdrawal  
- **Press 'o'** - Show ownership percentages

## Contributing

This is a personal fork, but contributions are welcome! If you have ideas for improvements or find bugs:

- **Issues:** Report bugs or suggest enhancements
- **Pull Requests:** Submit improvements for review
- **Discussion:** Share ideas for new features

Whether it's fixing a typo, adding features, or discussing new ideas, all contributions are appreciated!
