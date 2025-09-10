# LLM Micro-Cap Trading Bot

**Fork of:** [ChatGPT Micro-Cap Experiment](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment)

This is a personal fork focused on enhanced portfolio tracking, dual currency support (CAD/USD), and improved LLM-assisted trading analysis. For the original concept and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Overview on getting started: [Here](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Start%20Your%20Own/README.md)
   
## Repository Structure

- **`trading_script.py`** - Main trading engine with portfolio management and stop-loss automation
- **`my trading/`** - **Production data folder** (gitignored) - Your real trading data
- **`test_data/`** - **Test environment** - Safe copies for development and testing
- **`Scripts and CSV Files/`** - My personal portfolio (updates every trading day)
- **`Start Your Own/`** - Template files and guide for starting your own experiment  
- **`Weekly Deep Research (MD|PDF)/`** - Research summaries and performance reports
- **`Experiment Details/`** - Documentation, methodology, prompts, and Q&A

# What This Fork Adds

This fork enhances the original ChatGPT Micro-Cap Experiment with:

- **Dual Currency Support** - CAD/USD portfolio management with manual cash balance updates
- **Enhanced Portfolio Tracking** - Real-time price integration and improved P&L calculations
- **Better User Experience** - Terminal optimization, virtual environment checks, and interactive menus
- **Comprehensive Debugging** - Multiple debug tools for troubleshooting and analysis
- **Configurable Timezone Support** - Flexible timezone handling for different markets

## Original Concept & Documentation

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
# Enhanced Features

This fork builds upon the original with:

- **Enhanced Trading Scripts** — Improved price evaluation and portfolio management
- **Dual Currency Support** — CAD/USD portfolio tracking and management
- **Advanced Performance Tracking** — Enhanced P&L calculations and market hours handling
- **Visualization Tools** — Matplotlib graphs for portfolio analysis
- **Comprehensive Debugging** — Multiple debug tools for troubleshooting
- **Better User Experience** — Terminal optimization and interactive menus

*For performance data and results, see the CSV files in `my trading/` and `test_data/` folders.*  

# Why This Fork Exists

This fork focuses on practical enhancements for personal portfolio tracking and LLM-assisted trading analysis. The original project's concept and methodology can be found in the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).

## Want to Contribute?

This is a personal fork, but contributions are welcome! If you have ideas for improvements or find bugs:

- **Issues:** Report bugs or suggest enhancements
- **Pull Requests:** Submit improvements for review
- **Discussion:** Share ideas for new features

Whether it's fixing a typo, adding features, or discussing new ideas, all contributions are appreciated!

# Tech Stack & Features

## Core Technologies
- **Python** - Core scripting and automation
- **pandas + yFinance** - Market data fetching and analysis
- **Matplotlib** - Performance visualization and charting
- **ChatGPT-4** - AI-powered trading decision engine

## Key Features
- **Robust Data Sources** - Yahoo Finance primary, Stooq fallback for reliability
- **Dual Currency Support** - CAD/USD portfolio management with manual cash balance updates
- **Interactive Portfolio Management** - Real-time price updates and position tracking
- **Backtesting Support** - ASOF_DATE override for historical analysis
- **Performance Analytics** - CAPM analysis, Sharpe/Sortino ratios, drawdown metrics
- **Comprehensive Trade Logging** - Complete transparency with detailed execution logs
- **Daily P&L Calculation** - Industry-standard daily performance tracking with market hours handling
- **Configurable Timezone Support** - PST timezone with flexible configuration options
- **Debug Tools** - Comprehensive analysis scripts for troubleshooting price data and P&L calculations

## Daily P&L Calculation Design

The system implements industry-standard daily P&L calculation with robust market hours handling:

### **How It Works**
- **Data Source**: Fetches 5 days of historical price data to ensure sufficient data for calculations
- **Calculation Method**: Compares current day's closing price vs previous day's closing price
- **Market Hours Handling**: 
  - **During Market Hours**: Uses most recent close price (updates throughout the day)
  - **After Hours**: Uses 4 PM close price vs previous day's close
  - **Pre-Market**: Uses previous day's close (appropriate for pre-market scenarios)
  - **Weekends/Holidays**: Uses last trading day's close vs previous trading day's close

### **Industry Standards Compliance**
✅ **Follows standard industry practices:**
- Uses close-to-close price comparison for daily P&L
- Handles different market scenarios appropriately
- Provides consistent calculations regardless of when the script is run
- Matches major trading platforms' daily P&L calculations

### **Technical Implementation**
- **Date Range**: Expands trading day window by 5 days to ensure sufficient historical data
- **Fallback Handling**: Multiple data sources (Yahoo Finance → Stooq) for reliability
- **Configurable Timezone Support**: Handles PST timezone with flexible configuration options
- **Error Handling**: Graceful fallback to "N/A" when insufficient data is available

## Debug Tools

The repository includes comprehensive debugging tools in the `debug/` folder:

- **`daily_pnl_debug.py`** - Analyzes daily P&L calculation issues and data availability
- **`market_hours_analysis.py`** - Tests market hours handling and compares with industry standards
- **`price_debug.py`** - General price data debugging and validation
- **`comprehensive_price_debug.py`** - Advanced price data analysis and troubleshooting

These tools help ensure the trading system operates correctly and provide transparency into how calculations are performed.

## Recent Enhancements & Improvements

*The following enhancements have been added to the original project to improve functionality and user experience:*

### 🚀 **Major Features Added**

#### **Dual Currency Support (CAD/USD)**
- **Manual Cash Balance Updates** - Added functionality to manually update cash balances in both CAD and USD
- **Enhanced Fund Management** - Improved fund contribution tracking and sync functionality
- **Currency-Aware Trading** - Trading system now properly handles both Canadian and US markets

#### **Daily P&L Calculation System**
- **Industry-Standard Implementation** - Fixed daily P&L showing "N/A" by implementing proper close-to-close calculations
- **Market Hours Handling** - Robust handling of pre-market, market hours, after-hours, and weekend scenarios
- **Configurable Timezone Support** - PST timezone with flexible configuration options

#### **Enhanced User Experience**
- **Terminal Width Detection** - Automatic terminal resizing and display optimization
- **Virtual Environment Checks** - Automatic venv activation in test scripts
- **Interactive Menu System** - Improved user interaction and display formatting
- **Color-Coded Output** - Enhanced prompt generation with color formatting

#### **Portfolio Management Improvements**
- **Real-Time Price Integration** - Current prices and P&L percentages in portfolio tables
- **Enhanced Data Handling** - Improved DataFrame operations and error handling
- **Portfolio Snapshot Display** - Better visualization of current holdings and performance
- **Ticker Correction Logic** - Streamlined ticker suffix handling and validation

#### **Development Tools & Debugging**
- **Comprehensive Debug Suite** - Multiple specialized debugging scripts
- **Variable Scoping Checks** - Enhanced development tools for code quality
- **Error Handling** - Improved logging and error management throughout the system
- **Data Source Reliability** - Yahoo Finance primary with Stooq fallback for robust data fetching

### 🔧 **Technical Improvements**
- **Requirements Updates** - Updated library dependencies and added UI enhancements
- **Code Refactoring** - Streamlined ticker correction logic and removed redundant files
- **Documentation** - Enhanced terminal display guidance and system documentation
- **Experiment Timeline Integration** - Timeline features integrated into prompt generation

## System Requirements
- Python  3.11+
- Internet connection for market data
- ~10MB storage for CSV data files

# Getting Started

This fork includes all the original functionality plus enhanced features for portfolio tracking and analysis. To get started:

1. **Clone this repository**
2. **Set up your virtual environment** (see `debug/activate_venv.bat` for Windows)
3. **Configure your data directories** (use `test_data/` for testing, `my trading/` for production)
4. **Run the trading script** with `python trading_script.py --data-dir test_data`

For the original setup guide and methodology, see the [original repository](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment).
