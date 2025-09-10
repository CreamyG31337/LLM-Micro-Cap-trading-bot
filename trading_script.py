"""Utilities for maintaining the LLM micro-cap portfolio.

This module rewrites the original script to:
- Centralize market data fetching with a robust Yahoo->Stooq fallback
- Ensure ALL price requests go through the same accessor
- Handle empty Yahoo frames (no exception) so fallback actually triggers
- Normalize Stooq output to Yahoo-like columns
- Make weekend handling consistent and testable
- Keep behavior and CSV formats compatible with prior runs

Notes:
- Some tickers/indices are not available on Stooq (e.g., ^RUT). These stay on Yahoo.
- Stooq end date is exclusive; we add +1 day for ranges.
- "Adj Close" is set equal to "Close" for Stooq to match downstream expectations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast,Dict, List, Optional
import os
import warnings

import numpy as np
import pandas as pd
import yfinance as yf
import json
import logging

# Development mode for stricter checking
import os
DEVELOPMENT_MODE = os.getenv("TRADING_BOT_DEV", "false").lower() == "true"

def check_variable_scoping(func_name: str, required_vars: list[str]) -> None:
    """Check for common variable scoping issues in development mode."""
    if not DEVELOPMENT_MODE:
        return
    
    import inspect
    frame = inspect.currentframe().f_back
    local_vars = frame.f_locals
    global_vars = frame.f_globals
    
    for var in required_vars:
        if var in local_vars and var in global_vars:
            logger.warning(f"Potential scoping issue in {func_name}: '{var}' exists in both local and global scope")
        elif var not in local_vars and var not in global_vars:
            logger.error(f"Variable '{var}' not found in {func_name}")

# Import timezone configuration
try:
    from market_config import get_timezone_config, get_timezone_offset, get_timezone_name
    _HAS_MARKET_CONFIG = True
except ImportError:
    _HAS_MARKET_CONFIG = False
    # Fallback timezone configuration
    def get_timezone_config():
        return {"name": "PST", "offset_hours": -8, "utc_offset": "-08:00"}
    def get_timezone_offset():
        return -8
    def get_timezone_name():
        return "PST"
from collections import defaultdict

# ============================================================================
# TIMEZONE UTILITY FUNCTIONS
# ============================================================================

def get_trading_timezone():
    """Get the configured trading timezone object."""
    offset_hours = get_timezone_offset()
    return timezone(timedelta(hours=offset_hours))

def get_current_trading_time():
    """Get current time in the configured trading timezone."""
    tz = get_trading_timezone()
    return datetime.now(tz)

def get_market_open_time(date=None):
    """Get market open time (6:30 AM) in the configured timezone for the given date."""
    tz = get_trading_timezone()
    if date is None:
        date = datetime.now(tz).date()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()
    
    market_open_time = datetime.combine(date, datetime.min.time().replace(hour=6, minute=30), tz)
    return market_open_time

def format_timestamp_for_csv(dt=None):
    """Format a datetime for CSV storage with timezone suffix."""
    if dt is None:
        dt = get_current_trading_time()
    
    tz_name = get_timezone_name()
    return dt.strftime(f"%Y-%m-%d %H:%M:%S {tz_name}")

def parse_csv_timestamp(timestamp_str):
    """Parse a timestamp from CSV with proper timezone handling."""
    if pd.isna(timestamp_str):
        return None
    
    timestamp_str = str(timestamp_str).strip()
    
    # Handle different timestamp formats
    if " PST" in timestamp_str:
        # Remove PST suffix and add proper UTC offset
        clean_timestamp = timestamp_str.replace(" PST", "")
        # Add UTC offset for proper parsing
        utc_offset = get_timezone_config()["utc_offset"]
        timestamp_with_offset = f"{clean_timestamp} {utc_offset}"
        return pd.to_datetime(timestamp_with_offset)
    elif " UTC" in timestamp_str or " GMT" in timestamp_str:
        # Already has timezone info, parse directly
        return pd.to_datetime(timestamp_str)
    else:
        # No timezone info, assume it's in the configured timezone
        tz = get_trading_timezone()
        dt = pd.to_datetime(timestamp_str)
        # Localize to the configured timezone
        return dt.tz_localize(tz)

# Color and formatting imports
try:
    from colorama import init, Fore, Back, Style
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    init(autoreset=True)  # Initialize colorama
    _HAS_RICH = True
    console = Console()
except ImportError:
    _HAS_RICH = False
    console = None

# Force fallback mode for testing (set via environment variable or function call)
_FORCE_FALLBACK = os.environ.get("FORCE_FALLBACK", "").lower() in ("true", "1", "yes", "on")
_FORCE_COLORAMA_ONLY = os.environ.get("FORCE_COLORAMA_ONLY", "").lower() in ("true", "1", "yes", "on")

def set_force_fallback(force_fallback: bool = True, colorama_only: bool = False) -> None:
    """Force fallback mode for testing purposes.
    
    Args:
        force_fallback: If True, disable Rich and use colorama/plain text
        colorama_only: If True, disable Rich but keep colorama (only works if force_fallback=True)
    """
    global _HAS_RICH, _FORCE_FALLBACK, _FORCE_COLORAMA_ONLY
    _FORCE_FALLBACK = force_fallback
    _FORCE_COLORAMA_ONLY = colorama_only
    if force_fallback:
        _HAS_RICH = False
        if not colorama_only:
            # Also disable colorama for plain text testing
            global Fore, Back, Style
            class DummyColor:
                def __getattr__(self, name):
                    return ""
            Fore = Back = Style = DummyColor()

# Import market configuration
try:
    from market_config import get_benchmarks, get_daily_instructions, get_market_info, print_active_config
    _HAS_MARKET_CONFIG = True
except ImportError:
    _HAS_MARKET_CONFIG = False
    print("Warning: market_config.py not found. Using default settings.")

# Import dual currency support
try:
    from dual_currency import (
        CashBalances, prompt_for_dual_currency_cash, save_cash_balances, 
        load_cash_balances, format_cash_display, get_ticker_currency, 
        get_trade_currency_info, is_canadian_ticker, is_us_ticker
    )
    _HAS_DUAL_CURRENCY = True
except ImportError:
    _HAS_DUAL_CURRENCY = False
    print("Warning: dual_currency.py not found. Using single currency mode.")

# Optional pandas-datareader import for Stooq access
try:
    import pandas_datareader.data as pdr
    _HAS_PDR = True
except Exception:
    _HAS_PDR = False

# -------- AS-OF override --------
ASOF_DATE: pd.Timestamp | None = None

def set_asof(date: str | datetime | pd.Timestamp | None) -> None:
    """Set a global 'as of' date so the script treats that day as 'today'. Use 'YYYY-MM-DD' format."""
    global ASOF_DATE
    if date is None:
        print("No prior date passed. Using today's date...")
        ASOF_DATE = None
        return
    ASOF_DATE = pd.Timestamp(date).normalize()
    pure_date = ASOF_DATE.date()

    print(f"Setting date as {pure_date}.")

# Allow env var override:  ASOF_DATE=YYYY-MM-DD python trading_script.py
_env_asof = os.environ.get("ASOF_DATE")
if _env_asof:
    set_asof(_env_asof)

# ------------------------------
# Color and formatting utilities
# ------------------------------

def print_header(title: str, emoji: str = "🔷") -> None:
    """Print a colorful header with emoji."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"\n{emoji} {title} {emoji}", style="bold blue on white", justify="center")
        console.print("─" * 60, style="blue")
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{emoji} {title} {emoji}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

def print_success(message: str, emoji: str = "✅") -> None:
    """Print a success message with green color and emoji."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold green")
    else:
        print(f"{Fore.GREEN}{emoji} {message}{Style.RESET_ALL}")

def print_error(message: str, emoji: str = "❌") -> None:
    """Print an error message with red color and emoji."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold red")
    else:
        print(f"{Fore.RED}{emoji} {message}{Style.RESET_ALL}")

def print_warning(message: str, emoji: str = "⚠️") -> None:
    """Print a warning message with yellow color and emoji."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold yellow")
    else:
        print(f"{Fore.YELLOW}{emoji} {message}{Style.RESET_ALL}")

def print_info(message: str, emoji: str = "ℹ️") -> None:
    """Print an info message with blue color and emoji."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold blue")
    else:
        print(f"{Fore.BLUE}{emoji} {message}{Style.RESET_ALL}")

def detect_terminal_width() -> int:
    """Detect the current terminal width in characters."""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        # Fallback to a reasonable default
        return 80

def is_using_test_data() -> bool:
    """Check if the script is currently using the test_data folder."""
    return "test_data" in str(DATA_DIR).lower()

def get_optimal_table_width() -> int:
    """Get the optimal table width based on environment and data source."""
    terminal_width = detect_terminal_width()
    
    # If using test_data or terminal is narrow, force a wider minimum
    if is_using_test_data() or terminal_width < 140:
        return max(terminal_width, 140)  # Force minimum 140 chars for test data
    
    return terminal_width

def detect_environment() -> dict:
    """Detect OS and terminal environment."""
    import platform
    import os
    
    env = {
        'os': platform.system(),
        'os_version': platform.version(),
        'is_windows': platform.system() == 'Windows',
        'is_windows_11': False,
        'is_conhost': False,
        'is_windows_terminal': False,
        'terminal_name': 'Unknown'
    }
    
    if env['is_windows']:
        # Check if it's Windows 11 (build 22000+)
        try:
            version_parts = platform.version().split('.')
            if len(version_parts) >= 3:
                build_number = int(version_parts[2])
                env['is_windows_11'] = build_number >= 22000
        except (ValueError, IndexError):
            pass
        
        # Detect terminal type
        try:
            # Check for Windows Terminal environment variables
            if os.environ.get('WT_SESSION'):
                env['is_windows_terminal'] = True
                env['terminal_name'] = 'Windows Terminal'
            elif os.environ.get('ConEmuANSI'):
                env['terminal_name'] = 'ConEmu'
            else:
                env['is_conhost'] = True
                env['terminal_name'] = 'Command Prompt (conhost)'
        except Exception:
            env['terminal_name'] = 'Unknown Windows Terminal'
    
    return env

def check_table_display_issues() -> None:
    """Check if tables might be cut off and provide helpful suggestions."""
    terminal_width = detect_terminal_width()
    optimal_width = get_optimal_table_width()
    using_test_data = is_using_test_data()
    env = detect_environment()
    
    if terminal_width < 120:
        print_warning("⚠️  Terminal width may be too narrow for optimal table display")
        print_warning(f"   Current width: {terminal_width} characters")
        print_warning("   Recommended: 130+ characters for best experience")
        print_warning("")
        
        # Provide environment-specific suggestions
        if env['is_windows']:
            if env['is_windows_terminal']:
                print_warning("💡 Windows Terminal detected - To fix this:")
                print_warning("   1. Open Windows Terminal Settings (Ctrl+,)")
                print_warning("   2. Click 'Startup' in the left sidebar")
                print_warning("   3. Under 'Launch size', set 'Columns' to 130 or higher")
                print_warning("   4. Click 'Save'")
                print_warning("   5. Or maximize this window (click maximize button)")
                print_warning("   6. Or press F11 for full screen mode")
                print_warning("")
                print_warning("   Note: This setting is buried deep in the settings!")
                print_warning("   Microsoft keeps reorganizing the UI, so look for 'Startup' → 'Launch size'")
            elif env['is_conhost']:
                print_warning("💡 Command Prompt detected - To fix this:")
                print_warning("   1. Right-click title bar → Properties → Layout")
                print_warning("   2. Set 'Window Size Width' to 130 or higher")
                print_warning("   3. Or maximize this window (click maximize button)")
                print_warning("   4. Or press F11 for full screen mode")
                print_warning("   5. Consider upgrading to Windows Terminal for better experience")
            else:
                print_warning("💡 To fix this, try:")
                print_warning("   1. Maximize this window (click maximize button)")
                print_warning("   2. Press F11 for full screen mode")
                print_warning("   3. Right-click title bar → Properties → Font → Choose smaller font")
        else:
            print_warning("💡 To fix this, try:")
            print_warning("   1. Maximize this window")
            print_warning("   2. Increase terminal width in your terminal settings")
            print_warning("   3. Use a smaller font size")
        
        print_warning("")
    
    if using_test_data:
        print_info("🧪 Test Data Mode: Forcing wider table display for better visibility")
        if optimal_width > terminal_width:
            print_info(f"   Table will be optimized for {optimal_width} characters (current: {terminal_width})")
        print_info("")

def print_money(amount: float, currency: str = "", emoji: str = "💰") -> str:
    """Format money display with color and emoji."""
    formatted = f"${amount:,.2f}"
    if currency:
        formatted += f" {currency}"
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        color = "green" if amount >= 0 else "red"
        return f"{emoji} [bold {color}]{formatted}[/bold {color}]"
    else:
        color = Fore.GREEN if amount >= 0 else Fore.RED
        return f"{color}{emoji} {formatted}{Style.RESET_ALL}"

def create_portfolio_table(portfolio_df: pd.DataFrame) -> None:
    """Create a beautiful portfolio table display with current prices, P&L, and position weights."""
    if portfolio_df.empty:
        print_info("Portfolio is currently empty")
        return
    
    # Check for potential scoping issues in development mode
    check_variable_scoping("create_portfolio_table", ["pd", "timedelta"])
    
    # Check for potential table display issues
    check_table_display_issues()
    
    # Get current prices for all tickers
    print_info("Fetching current prices for portfolio display...", "📈")
    s, e = trading_day_window()
    
    # For daily P&L calculation, we need more historical data
    # Expand the date range to include at least 2 days of data
    s_expanded = s - timedelta(days=5)  # Go back 5 days to ensure we have enough data
    
    # Load trade log to get position open dates
    trade_log_df: pd.DataFrame | None = None
    try:
        if not TRADE_LOG_CSV.exists():
            logger.warning(f"Trade log file does not exist: {TRADE_LOG_CSV}")
            trade_log_df = None
        else:
            trade_log_df = pd.read_csv(TRADE_LOG_CSV)
            if trade_log_df.empty:
                logger.info("Trade log is empty")
                trade_log_df = None
            else:
                # Use proper timezone-aware parsing
                trade_log_df['Date'] = trade_log_df['Date'].apply(parse_csv_timestamp)
                logger.debug(f"Successfully loaded trade log with {len(trade_log_df)} entries")
    except FileNotFoundError:
        logger.warning(f"Trade log file not found: {TRADE_LOG_CSV}")
        trade_log_df = None
    except pd.errors.EmptyDataError:
        logger.warning(f"Trade log file is empty: {TRADE_LOG_CSV}")
        trade_log_df = None
    except pd.errors.ParserError as e:
        logger.error(f"Failed to parse trade log CSV: {e}")
        trade_log_df = None
    except Exception as e:
        logger.error(f"Unexpected error loading trade log: {e}", exc_info=True)
        trade_log_df = None
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        # Get date range information for better clarity
        current_date = last_trading_date().strftime("%Y-%m-%d")
        table_title = f"📊 Portfolio Snapshot - {current_date}"
        
        # Determine optimal column widths based on environment
        optimal_width = get_optimal_table_width()
        using_test_data = is_using_test_data()
        
        # Set minimum widths for numerical columns to ensure visibility
        # Ticker is most important, then numbers, company name can be heavily truncated
        company_max_width = 25 if optimal_width >= 140 else 15
        if using_test_data:
            company_max_width = 12  # Even more conservative for test data
        
        table = Table(title=table_title, show_header=True, header_style="bold magenta")
        table.add_column("🎯 Ticker", style="cyan", no_wrap=True, width=11)  # Slightly wider for ticker visibility
        table.add_column("🏢 Company", style="white", no_wrap=True, max_width=company_max_width, justify="left")
        table.add_column("📅 Opened", style="dim", no_wrap=True, width=10)  # Fixed width for date
        table.add_column("📈 Shares", justify="right", style="green", width=10)  # Ensure shares fit
        table.add_column("💵 Buy Price", justify="right", style="blue", width=10)  # Ensure price fits
        table.add_column("💰 Current", justify="right", style="yellow", width=10)  # Ensure price fits
        table.add_column("📊 Total P&L", justify="right", style="magenta", width=12)  # Wider for P&L display
        table.add_column("📈 Daily P&L", justify="right", style="cyan", width=10)  # Ensure P&L fits
        table.add_column("📊 5-Day P&L", justify="right", style="bright_magenta", width=10)  # 5-day performance
        table.add_column("🍕 Weight", justify="right", style="bright_blue", width=8)  # Position weight as % of portfolio
        table.add_column("🛑 Stop Loss", justify="right", style="red", width=10)  # Ensure price fits
        table.add_column("💵 Cost Basis", justify="right", style="yellow", width=10)  # Ensure price fits
        
        # First pass: Calculate total portfolio value for position weights
        total_portfolio_value = 0.0
        position_data = []
        
        for _, row in portfolio_df.iterrows():
            ticker = str(row.get('ticker', ''))
            shares = float(row.get('shares', 0))
            buy_price = float(row.get('buy_price', 0))
            
            # Fetch current price
            fetch = download_price_data(ticker, start=s_expanded, end=e, auto_adjust=False, progress=False)
            current_price_val = 0.0
            
            if not fetch.df.empty and "Close" in fetch.df.columns:
                current_price_val = float(fetch.df['Close'].iloc[-1].item())
            
            # Calculate position value
            position_value = current_price_val * shares
            total_portfolio_value += position_value
            
            # Store position data for second pass
            position_data.append({
                'ticker': ticker,
                'shares': shares,
                'buy_price': buy_price,
                'current_price_val': current_price_val,
                'position_value': position_value,
                'fetch': fetch,
                'stop_loss': float(row.get('stop_loss', 0)),
                'cost_basis': float(row.get('cost_basis', 0))
            })
        
        # Second pass: Create table rows with position weights
        for pos_data in position_data:
            ticker = pos_data['ticker']
            company_name = get_company_name(ticker)
            # Truncate long company names for display using dynamic width
            display_name = company_name[:company_max_width-3] + "..." if len(company_name) > company_max_width else company_name
            
            # Get position open date from trade log
            open_date = "N/A"
            if trade_log_df is not None:
                ticker_trades = trade_log_df[trade_log_df['Ticker'] == ticker]
                if not ticker_trades.empty:
                    # Get the earliest trade date for this ticker
                    min_date = ticker_trades['Date'].min()
                    if not pd.isna(min_date):
                        try:
                            open_date = min_date.strftime("%m/%d")
                        except Exception:
                            open_date = "N/A"
            
            # Format current price
            current_price_val = pos_data['current_price_val']
            current_price = f"${current_price_val:.2f}" if current_price_val > 0 else "N/A"
            
            # Calculate P&L metrics
            buy_price = pos_data['buy_price']
            shares = pos_data['shares']
            total_pnl = ""
            daily_pnl = ""
            five_day_pnl = ""
            position_weight = ""
            
            if current_price_val > 0 and buy_price > 0:
                # Calculate total P&L since position opened
                total_pnl_pct = ((current_price_val - buy_price) / buy_price) * 100
                total_pnl_amount = (current_price_val - buy_price) * shares
                total_pnl = f"{total_pnl_pct:+.1f}% (${total_pnl_amount:+.2f})"
                
                # Calculate daily P&L (today vs yesterday)
                fetch = pos_data['fetch']
                if len(fetch.df) > 1:
                    prev_price = float(fetch.df['Close'].iloc[-2].item())
                    daily_pnl_pct = ((current_price_val - prev_price) / prev_price) * 100
                    daily_pnl = f"{daily_pnl_pct:+.1f}%"
                else:
                    daily_pnl = "N/A"
                
                # Calculate 5-day P&L (today vs 5 days ago)
                if len(fetch.df) >= 5:
                    five_days_ago_price = float(fetch.df['Close'].iloc[-5].item())
                    five_day_pnl_pct = ((current_price_val - five_days_ago_price) / five_days_ago_price) * 100
                    five_day_pnl = f"{five_day_pnl_pct:+.1f}%"
                else:
                    five_day_pnl = "N/A"
                
                # Calculate position weight as % of total portfolio
                if total_portfolio_value > 0:
                    weight_pct = (pos_data['position_value'] / total_portfolio_value) * 100
                    position_weight = f"{weight_pct:.1f}%"
                else:
                    position_weight = "N/A"
            else:
                total_pnl = "N/A"
                daily_pnl = "N/A"
                five_day_pnl = "N/A"
                position_weight = "N/A"
            
            table.add_row(
                ticker,
                display_name,
                open_date,
                f"{shares:.4f}",  # Show fractional shares with 4 decimal places
                f"${buy_price:.2f}",
                current_price,
                total_pnl,
                daily_pnl,
                five_day_pnl,
                position_weight,
                f"${pos_data['stop_loss']:.2f}" if pos_data['stop_loss'] > 0 else "None",
                f"${pos_data['cost_basis']:.2f}"
            )
        
        console.print(table)
    else:
        # Get date range information for better clarity
        current_date = last_trading_date().strftime("%Y-%m-%d")
        print(f"\n{Fore.MAGENTA}📊 Portfolio Snapshot - {current_date}:{Style.RESET_ALL}")
        # For plain text, add company names and current prices
        display_df = portfolio_df.copy()
        display_df['Company'] = display_df['ticker'].apply(get_company_name)
        
        # Add position open dates
        open_dates = []
        if trade_log_df is not None:
            for _, row in display_df.iterrows():
                ticker = str(row.get('ticker', ''))
                ticker_trades = trade_log_df[trade_log_df['Ticker'] == ticker]
                if not ticker_trades.empty:
                    open_date = ticker_trades['Date'].min().strftime("%m/%d")
                    open_dates.append(open_date)
                else:
                    open_dates.append("N/A")
        else:
            open_dates = ["N/A"] * len(display_df)
        
        display_df['Opened'] = open_dates
        
        # Add current prices and P&L percentages
        current_prices = []
        total_pnl_percentages = []
        daily_pnl_percentages = []
        
        for _, row in display_df.iterrows():
            ticker = str(row.get('ticker', ''))
            # Use expanded date range to ensure we have enough data for daily P&L calculation
            fetch = download_price_data(ticker, start=s_expanded, end=e, auto_adjust=False, progress=False)
            
            if not fetch.df.empty and "Close" in fetch.df.columns:
                current_price = float(fetch.df['Close'].iloc[-1].item())
                current_prices.append(f"${current_price:.2f}")
                
                buy_price = float(row.get('buy_price', 0))
                if buy_price > 0:
                    # Total P&L since position opened
                    total_pnl_pct = ((current_price - buy_price) / buy_price) * 100
                    total_pnl_percentages.append(f"{total_pnl_pct:+.1f}%")
                    
                    # Daily P&L (today vs yesterday)
                    if len(fetch.df) > 1:
                        prev_price = float(fetch.df['Close'].iloc[-2].item())
                        daily_pnl_pct = ((current_price - prev_price) / prev_price) * 100
                        daily_pnl_percentages.append(f"{daily_pnl_pct:+.1f}%")
                    else:
                        daily_pnl_percentages.append("N/A")
                else:
                    total_pnl_percentages.append("N/A")
                    daily_pnl_percentages.append("N/A")
            else:
                current_prices.append("N/A")
                total_pnl_percentages.append("N/A")
                daily_pnl_percentages.append("N/A")
        
        display_df['Current Price'] = current_prices
        display_df['Total P&L %'] = total_pnl_percentages
        display_df['Daily P&L %'] = daily_pnl_percentages
        
        # Reorder columns and format shares to show fractional
        cols = ['ticker', 'Company', 'Opened', 'shares', 'buy_price', 'Current Price', 'Total P&L %', 'Daily P&L %', 'stop_loss', 'cost_basis']
        display_df = display_df[[col for col in cols if col in display_df.columns]]
        
        # Format shares column to show fractional shares properly
        if 'shares' in display_df.columns:
            display_df['shares'] = display_df['shares'].apply(lambda x: f"{float(x):.4f}")
        
        # Use better formatting for plain text to ensure numerical data is visible
        optimal_width = get_optimal_table_width()
        using_test_data = is_using_test_data()
        
        # Set pandas display options for better formatting
        # Prioritize ticker visibility over company names
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', optimal_width)
        pd.set_option('display.max_colwidth', 18 if using_test_data else 20)  # Shorter company names
        
        print(display_df.to_string(index=False))
        
        # Reset pandas options
        pd.reset_option('display.max_columns')
        pd.reset_option('display.width')
        pd.reset_option('display.max_colwidth')

def print_trade_menu() -> None:
    """Print the colorful trade menu."""
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        panel = Panel(
            "[bold green]📈 Trading Menu[/bold green]\n\n"
            "[cyan]'b'[/cyan] 🛒 Buy (Market-on-Open or Limit)\n"
            "[cyan]'s'[/cyan] 📤 Sell (Limit Order)\n"
            "[cyan]'c'[/cyan] 💵 Log Contribution\n"
            "[cyan]'w'[/cyan] 💸 Log Withdrawal\n"
            "[cyan]'u'[/cyan] 🔄 Update Cash Balances\n"
            "[cyan]'sync'[/cyan] 🔗 Sync Fund Contributions\n"
            "[cyan]Enter[/cyan] ➤  Continue to Portfolio Processing",
            border_style="green",
            width=62
        )
        console.print(panel)
    else:
        print(f"\n{Fore.GREEN}📈 Trading Menu:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}'b'{Style.RESET_ALL} 🛒 Buy (Market-on-Open or Limit)")
        print(f"{Fore.CYAN}'s'{Style.RESET_ALL} 📤 Sell (Limit Order)")
        print(f"{Fore.CYAN}'c'{Style.RESET_ALL} 💵 Log Contribution")
        print(f"{Fore.CYAN}'w'{Style.RESET_ALL} 💸 Log Withdrawal")
        print(f"{Fore.CYAN}'u'{Style.RESET_ALL} 🔄 Update Cash Balances")
        print(f"{Fore.CYAN}'sync'{Style.RESET_ALL} 🔗 Sync Fund Contributions")
        print(f"{Fore.CYAN}Enter{Style.RESET_ALL} ➤ Continue to Portfolio Processing")

def _effective_now() -> datetime:
    return (ASOF_DATE.to_pydatetime() if ASOF_DATE is not None else datetime.now())

# ------------------------------
# Globals / file locations
# ------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
# Default to 'my trading' folder for private data (gitignored)
DEFAULT_DATA_DIR = SCRIPT_DIR / "my trading"
DATA_DIR = DEFAULT_DATA_DIR
PORTFOLIO_CSV = DATA_DIR / "llm_portfolio_update.csv"
TRADE_LOG_CSV = DATA_DIR / "llm_trade_log.csv"
# Default benchmarks (fallback if market_config not available)
DEFAULT_BENCHMARKS = ["SPY", "QQQ", "IWM", "^GSPTSE"]  # North American benchmarks

# ------------------------------
# Configuration helpers — benchmark tickers (tickers.json)
# ------------------------------



logger = logging.getLogger(__name__)

def _read_json_file(path: Path) -> Optional[Dict]:
    """Read and parse JSON from `path`. Return dict on success, None if not found or invalid.

    - FileNotFoundError -> return None
    - JSON decode error -> log a warning and return None
    - Other IO errors -> log a warning and return None
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        logger.warning("tickers.json present but malformed: %s -> %s. Falling back to defaults.", path, exc)
        return None
    except Exception as exc:
        logger.warning("Unable to read tickers.json (%s): %s. Falling back to defaults.", path, exc)
        return None

def load_benchmarks(script_dir: Path | None = None) -> List[str]:
    """Return a list of benchmark tickers.

    Priority order:
    1. market_config.py (if available)
    2. tickers.json file
    3. DEFAULT_BENCHMARKS fallback

    Looks for a `tickers.json` file in either:
      - script_dir (if provided) OR the module SCRIPT_DIR, and then
      - script_dir.parent (project root candidate).

    Expected schema:
      {"benchmarks": ["IWO", "XBI", "SPY", "IWM"]}

    Behavior:
    - If market_config available -> use get_benchmarks()
    - If file missing or malformed -> return DEFAULT_BENCHMARKS copy.
    - If 'benchmarks' key missing or not a list -> log warning and return defaults.
    - Normalizes tickers (strip, upper) and preserves order while removing duplicates.
    """
    
    # First try market_config.py
    if _HAS_MARKET_CONFIG:
        try:
            return get_benchmarks()
        except Exception as e:
            logger.warning("Failed to get benchmarks from market_config: %s", e)
    base = Path(script_dir) if script_dir else SCRIPT_DIR
    candidates = [base, base.parent]

    cfg = None
    cfg_path = None
    for c in candidates:
        p = (c / "tickers.json").resolve()
        data = _read_json_file(p)
        if data is not None:
            cfg = data
            cfg_path = p
            break

    if not cfg:
        return DEFAULT_BENCHMARKS.copy()

    benchmarks = cfg.get("benchmarks")
    if not isinstance(benchmarks, list):
        logger.warning("tickers.json at %s missing 'benchmarks' array. Falling back to defaults.", cfg_path)
        return DEFAULT_BENCHMARKS.copy()

    seen = set()
    result: list[str] = []
    for t in benchmarks:
        if not isinstance(t, str):
            continue
        up = t.strip().upper()
        if not up:
            continue
        if up not in seen:
            seen.add(up)
            result.append(up)

    return result if result else DEFAULT_BENCHMARKS.copy()


# ------------------------------
# Date helpers
# ------------------------------

def last_trading_date(today: datetime | None = None) -> pd.Timestamp:
    """Return last trading date (Mon–Fri), mapping Sat/Sun -> Fri."""
    dt = pd.Timestamp(today or _effective_now())
    if dt.weekday() == 5:  # Sat -> Fri
        return (dt - pd.Timedelta(days=1)).normalize()
    if dt.weekday() == 6:  # Sun -> Fri
        return (dt - pd.Timedelta(days=2)).normalize()
    return dt.normalize()

def check_weekend() -> str:
    """Backwards-compatible wrapper returning ISO date string for last trading day."""
    return last_trading_date().date().isoformat()

def trading_day_window(target: datetime | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start, end) window for the last trading day (Fri on weekends)."""
    d = last_trading_date(target)
    return d, (d + pd.Timedelta(days=1))


# ------------------------------
# Data access layer
# ------------------------------

# Known Stooq symbol remaps for common indices
STOOQ_MAP = {
    "^GSPC": "^SPX",  # S&P 500
    "^DJI": "^DJI",   # Dow Jones
    "^IXIC": "^IXIC", # Nasdaq Composite
    # "^RUT": not on Stooq; keep Yahoo
}

# Cache for company names to avoid repeated API calls
COMPANY_NAME_CACHE = {}

# Cache for ticker corrections to avoid repeated API calls
TICKER_CORRECTION_CACHE = {}

def detect_currency_context(ticker: str, buy_price: float = None) -> str:
    """
    Detect if a ticker is likely Canadian based on context clues.
    Returns 'CAD', 'USD', or 'UNKNOWN'
    """
    # Check if ticker has Canadian characteristics in the name
    canadian_patterns = [
        # Common Canadian company name patterns
        'CAN', 'CANADA', 'NORTH', 'NORTHERN', 'WESTERN', 'EASTERN',
        'QUEBEC', 'ONTARIO', 'ALBERTA', 'BRITISH', 'COLUMBIA'
    ]
    
    ticker_upper = ticker.upper()
    for pattern in canadian_patterns:
        if pattern in ticker_upper:
            return 'CAD'
    
    # Don't use price as a clue - it's unreliable
    return 'UNKNOWN'

def detect_and_correct_ticker(ticker: str, buy_price: float = None) -> str:
    """
    Detect if a ticker is Canadian and automatically add the appropriate suffix.
    This helps prevent issues when logging trades from Wealthsimple where .TO isn't shown.
    
    Returns the corrected ticker symbol with appropriate suffix.
    """
    ticker = ticker.upper().strip()
    
    # Check cache first
    if ticker in TICKER_CORRECTION_CACHE:
        return TICKER_CORRECTION_CACHE[ticker]
    
    # If already has a suffix, return as-is
    if any(ticker.endswith(suffix) for suffix in ['.TO', '.V', '.CN', '.NE']):
        TICKER_CORRECTION_CACHE[ticker] = ticker
        return ticker
    
    try:
        import yfinance as yf
        
        # Test if the ticker exists as-is (likely US stock)
        us_stock = yf.Ticker(ticker)
        us_info = us_stock.info
        us_exists = us_info and us_info.get('exchange')
        
        # Test Canadian variants to see if they also exist
        canadian_variants = [f"{ticker}.TO", f"{ticker}.V", f"{ticker}.CN"]
        canadian_exists = False
        canadian_variant_found = None
        
        for variant in canadian_variants:
            try:
                canadian_stock = yf.Ticker(variant)
                canadian_info = canadian_stock.info
                if (canadian_info and 
                    canadian_info.get('exchange') and 
                    any(exchange in canadian_info.get('exchange', '') for exchange in ['TSX', 'VAN', 'CNQ', 'TOR'])):
                    canadian_exists = True
                    canadian_variant_found = variant
                    break
            except:
                continue
        
        # If both US and Canadian versions exist, ask user to choose
        if us_exists and canadian_exists:
            print(f"\n🔍 Found both US and Canadian versions of {ticker}:")
            print(f"US: {us_info.get('longName', 'Unknown')} ({us_info.get('exchange', 'Unknown exchange')})")
            print(f"Canadian ({canadian_variant_found}): {canadian_stock.info.get('longName', 'Unknown')} ({canadian_stock.info.get('exchange', 'Unknown exchange')})")
            
            print("\nWhich version do you want to trade?")
            print("1. US Stock")
            print("2. Canadian Stock")
            
            while True:
                try:
                    choice = input("Enter choice (1-2): ").strip()
                    if choice == "1":
                        TICKER_CORRECTION_CACHE[ticker] = ticker
                        return ticker
                    elif choice == "2":
                        TICKER_CORRECTION_CACHE[ticker] = canadian_variant_found
                        return canadian_variant_found
                    else:
                        print("Please enter 1 or 2")
                except KeyboardInterrupt:
                    print("\nCancelled. Using US version.")
                    TICKER_CORRECTION_CACHE[ticker] = ticker
                    return ticker
        
        # If only Canadian version exists, use it
        elif canadian_exists:
            TICKER_CORRECTION_CACHE[ticker] = canadian_variant_found
            logger.info(f"Auto-corrected ticker {ticker} to {canadian_variant_found} (only Canadian version found)")
            return canadian_variant_found
        
        # If only US version exists, use it
        elif us_exists:
            TICKER_CORRECTION_CACHE[ticker] = ticker
            return ticker
        
        # If no clear exchange info, ask the user
        print(f"\n🔍 Could not auto-detect exchange for {ticker}")
        print("Please specify the exchange:")
        print("1. US Stock (NYSE/NASDAQ)")
        print("2. Canadian Stock - TSX (.TO)")
        print("3. Canadian Stock - TSX Venture (.V)")
        print("4. Canadian Stock - CSE (.CN)")
        
        while True:
            try:
                choice = input("Enter choice (1-4): ").strip()
                if choice == "1":
                    TICKER_CORRECTION_CACHE[ticker] = ticker
                    return ticker
                elif choice == "2":
                    corrected = f"{ticker}.TO"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                elif choice == "3":
                    corrected = f"{ticker}.V"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                elif choice == "4":
                    corrected = f"{ticker}.CN"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                else:
                    print("Please enter 1, 2, 3, or 4")
            except KeyboardInterrupt:
                print("\nCancelled. Using original ticker.")
                TICKER_CORRECTION_CACHE[ticker] = ticker
                return ticker
        
    except Exception as e:
        logger.warning(f"Could not detect ticker type for {ticker}: {e}")
        # Ask user when exception occurs
        print(f"\n🔍 Error detecting exchange for {ticker}: {e}")
        print("Please specify the exchange:")
        print("1. US Stock (NYSE/NASDAQ)")
        print("2. Canadian Stock - TSX (.TO)")
        print("3. Canadian Stock - TSX Venture (.V)")
        print("4. Canadian Stock - CSE (.CN)")
        
        while True:
            try:
                choice = input("Enter choice (1-4): ").strip()
                if choice == "1":
                    TICKER_CORRECTION_CACHE[ticker] = ticker
                    return ticker
                elif choice == "2":
                    corrected = f"{ticker}.TO"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                elif choice == "3":
                    corrected = f"{ticker}.V"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                elif choice == "4":
                    corrected = f"{ticker}.CN"
                    TICKER_CORRECTION_CACHE[ticker] = corrected
                    return corrected
                else:
                    print("Please enter 1, 2, 3, or 4")
            except KeyboardInterrupt:
                print("\nCancelled. Using original ticker.")
                TICKER_CORRECTION_CACHE[ticker] = ticker
                return ticker

def get_company_name(ticker: str) -> str:
    """
    Get the full company name for a ticker symbol.
    Uses yfinance to fetch company info and caches results.
    """
    ticker = ticker.upper()
    
    # Check cache first
    if ticker in COMPANY_NAME_CACHE:
        return COMPANY_NAME_CACHE[ticker]
    
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Try different possible name fields
        name = (info.get('longName') or 
                info.get('shortName') or 
                info.get('name') or 
                ticker)  # Fallback to ticker if no name found
        
        # Cache the result
        COMPANY_NAME_CACHE[ticker] = name
        return name
        
    except Exception as e:
        logger.warning(f"Could not fetch company name for {ticker}: {e}")
        # Cache the ticker as fallback
        COMPANY_NAME_CACHE[ticker] = ticker
        return ticker

# Symbols we should *not* attempt on Stooq
STOOQ_BLOCKLIST = {"^RUT"}


# ------------------------------
# Data access layer (UPDATED)
# ------------------------------

@dataclass
class FetchResult:
    df: pd.DataFrame
    source: str  # "yahoo" | "stooq-pdr" | "stooq-csv" | "yahoo:<proxy>-proxy" | "empty"

def _to_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass
    return df

def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    # Handle multi-level columns (when yfinance returns tuples like ('Close', 'TICKER'))
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten multi-level columns to simple names
        df.columns = df.columns.get_level_values(0)
    
    # Ensure all expected columns exist
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c not in df.columns:
            df[c] = np.nan
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    return df[cols]

def _yahoo_download(ticker: str, **kwargs: Any) -> pd.DataFrame:
    """Call yfinance.download with proper session handling for new API."""
    import io, logging
    from contextlib import redirect_stderr, redirect_stdout

    # Remove session parameter - let yfinance handle it internally
    kwargs.pop("session", None)
    kwargs.setdefault("progress", False)
    kwargs.setdefault("threads", False)

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    buf = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                df = cast(pd.DataFrame, yf.download(ticker, **kwargs))
        except Exception:
            return pd.DataFrame()
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame()

def _stooq_csv_download(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Fetch OHLCV from Stooq CSV endpoint (daily). Good for US tickers, Canadian tickers, and many ETFs."""
    import requests, io
    if ticker in STOOQ_BLOCKLIST:
        return pd.DataFrame()
    t = STOOQ_MAP.get(ticker, ticker)

    # Stooq daily CSV: lowercase; handle different exchanges
    if not t.startswith("^"):
        sym = t.lower()
        # Handle Canadian tickers (.TO suffix)
        if sym.endswith(".to"):
            # Keep .to suffix for Canadian stocks
            pass
        # Handle US tickers (add .us if not present)
        elif not sym.endswith(".us") and not sym.endswith(".to"):
            sym = f"{sym}.us"
    else:
        sym = t.lower()

    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            return pd.DataFrame()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty:
            return pd.DataFrame()

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

        # Filter to [start, end) (Stooq end is exclusive)
        df = df.loc[(df.index >= start.normalize()) & (df.index < end.normalize())]

        # Normalize to Yahoo-like schema
        if "Adj Close" not in df.columns:
            df["Adj Close"] = df["Close"]
        return df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
    except Exception:
        return pd.DataFrame()

def _stooq_download(
    ticker: str,
    start: datetime | pd.Timestamp,
    end: datetime | pd.Timestamp,
) -> pd.DataFrame:
    """Fetch OHLCV from Stooq via pandas-datareader; returns empty DF on failure."""
    if not _HAS_PDR or ticker in STOOQ_BLOCKLIST:
        return pd.DataFrame()

    t = STOOQ_MAP.get(ticker, ticker)
    if not t.startswith("^"):
        t = t.lower()
        # Handle Canadian tickers (.TO suffix) - keep as is for Stooq
        if not t.endswith(".to") and not t.endswith(".us"):
            # Default to .us for US tickers if no suffix
            t = f"{t}.us"

    try:
        # Ensure pdr is imported locally if not available globally
        if not _HAS_PDR:
            return pd.DataFrame()
        import pandas_datareader.data as pdr_local
        df = cast(pd.DataFrame, pdr_local.DataReader(t, "stooq", start=start, end=end))
        df.sort_index(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def _weekend_safe_range(period: str | None, start: Any, end: Any) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Compute a concrete [start, end) window.
    - If explicit start/end provided: use them (add +1 day to end to make it exclusive).
    - If period is '1d': use the last trading day's [Fri, Sat) window on weekends.
    - If period like '2d'/'5d': build a window ending at the last trading day.
    """
    if start or end:
        end_ts = pd.Timestamp(end) if end else last_trading_date() + pd.Timedelta(days=1)
        start_ts = pd.Timestamp(start) if start else (end_ts - pd.Timedelta(days=5))
        return start_ts.normalize(), pd.Timestamp(end_ts).normalize()

    # No explicit dates; derive from period
    if isinstance(period, str) and period.endswith("d"):
        days = int(period[:-1])
    else:
        days = 1

    # Anchor to last trading day (Fri on Sun/Sat)
    end_trading = last_trading_date()
    start_ts = (end_trading - pd.Timedelta(days=days)).normalize()
    end_ts = (end_trading + pd.Timedelta(days=1)).normalize()
    return start_ts, end_ts

def download_price_data(ticker: str, **kwargs: Any) -> FetchResult:
    """
    Robust OHLCV fetch with multi-stage fallbacks:

    Order:
      1) Yahoo Finance via yfinance
      2) Stooq via pandas-datareader
      3) Stooq direct CSV
      4) Index proxies (e.g., ^GSPC->SPY, ^RUT->IWM) via Yahoo
    Returns a DataFrame with columns [Open, High, Low, Close, Adj Close, Volume].
    """
    # Pull out range args, compute a weekend-safe window
    period = kwargs.pop("period", None)
    start = kwargs.pop("start", None)
    end = kwargs.pop("end", None)
    kwargs.setdefault("progress", False)
    kwargs.setdefault("threads", False)

    s, e = _weekend_safe_range(period, start, end)

    # ---------- 1) Yahoo (date-bounded) ----------
    df_y = _yahoo_download(ticker, start=s, end=e, **kwargs)
    if isinstance(df_y, pd.DataFrame) and not df_y.empty:
        return FetchResult(_normalize_ohlcv(_to_datetime_index(df_y)), "yahoo")

    # ---------- 2) Stooq via pandas-datareader ----------
    df_s = _stooq_download(ticker, start=s, end=e)
    if isinstance(df_s, pd.DataFrame) and not df_s.empty:
        return FetchResult(_normalize_ohlcv(_to_datetime_index(df_s)), "stooq-pdr")

    # ---------- 3) Stooq direct CSV ----------
    df_csv = _stooq_csv_download(ticker, s, e)
    if isinstance(df_csv, pd.DataFrame) and not df_csv.empty:
        return FetchResult(_normalize_ohlcv(_to_datetime_index(df_csv)), "stooq-csv")

    # ---------- 4) Proxy indices if applicable ----------
    proxy_map = {"^GSPC": "SPY", "^RUT": "IWM"}
    proxy = proxy_map.get(ticker)
    if proxy:
        df_proxy = _yahoo_download(proxy, start=s, end=e, **kwargs)
        if isinstance(df_proxy, pd.DataFrame) and not df_proxy.empty:
            return FetchResult(_normalize_ohlcv(_to_datetime_index(df_proxy)), f"yahoo:{proxy}-proxy")

    # ---------- Nothing worked ----------
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"])
    return FetchResult(empty, "empty")



# ------------------------------
# File path configuration
# ------------------------------

def set_data_dir(data_dir: Path) -> None:
    """Set the data directory and update file paths. Creates directory if it doesn't exist."""
    global DATA_DIR, PORTFOLIO_CSV, TRADE_LOG_CSV
    DATA_DIR = Path(data_dir)
    os.makedirs(DATA_DIR, exist_ok=True)
    PORTFOLIO_CSV = DATA_DIR / "llm_portfolio_update.csv"
    TRADE_LOG_CSV = DATA_DIR / "llm_trade_log.csv"


# ------------------------------
# Portfolio operations
# ------------------------------

def _ensure_df(portfolio: pd.DataFrame | dict[str, list[object]] | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(portfolio, pd.DataFrame):
        return portfolio.copy()
    if isinstance(portfolio, (dict, list)):
        return pd.DataFrame(portfolio)
    raise TypeError("portfolio must be a DataFrame, dict, or list[dict]")

def _display_ownership_percentages(data_dir: str) -> None:
    """Display ownership percentages by contributor"""
    ownership = calculate_ownership_percentages(data_dir)
    
    if not ownership:
        return
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        ownership_table = Table(title="👥 Ownership Percentages", show_header=True, header_style="bold blue")
        ownership_table.add_column("Contributor", style="yellow", no_wrap=True)
        ownership_table.add_column("Ownership %", justify="right", style="green")
        
        # Sort by ownership percentage (highest first)
        sorted_ownership = sorted(ownership.items(), key=lambda x: x[1], reverse=True)
        
        for contributor, percentage in sorted_ownership:
            ownership_table.add_row(contributor, f"{percentage:.1f}%")
        
        console.print(ownership_table)
    else:
        print_info("Ownership Percentages:", "👥")
        # Sort by ownership percentage (highest first)
        sorted_ownership = sorted(ownership.items(), key=lambda x: x[1], reverse=True)
        
        for contributor, percentage in sorted_ownership:
            print(f"  {contributor}: {percentage:.1f}%")


def _display_risk_metrics(portfolio_df: pd.DataFrame, total_value: float, cash: float) -> None:
    """Display basic risk metrics for the portfolio"""
    if portfolio_df.empty:
        return
    
    # Calculate position weights
    position_weights = []
    for _, row in portfolio_df.iterrows():
        shares = float(row.get('shares', 0))
        buy_price = float(row.get('buy_price', 0))
        # Use buy price as proxy for current value (in real implementation, you'd fetch current prices)
        position_value = shares * buy_price
        weight = (position_value / total_value * 100) if total_value > 0 else 0
        position_weights.append(weight)
    
    # Risk metrics
    max_weight = max(position_weights) if position_weights else 0
    largest_position_idx = position_weights.index(max_weight) if position_weights else 0
    largest_position = str(portfolio_df.iloc[largest_position_idx].get('ticker', 'N/A')) if not portfolio_df.empty else "N/A"
    
    total_equity = total_value + cash
    cash_allocation = (cash / total_equity * 100) if total_equity > 0 else 100
    
    # Portfolio concentration analysis
    concentration_risk = "Low" if max_weight < 30 else "Medium" if max_weight < 50 else "High"
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        risk_table = Table(title="⚠️ Risk Metrics", show_header=True, header_style="bold red")
        risk_table.add_column("Metric", style="cyan", no_wrap=True)
        risk_table.add_column("Value", justify="right", style="yellow")
        risk_table.add_column("Status", justify="center", style="green")
        
        risk_table.add_row("📊 Portfolio Concentration", f"{max_weight:.1f}%", f"[{concentration_risk.lower()}] {concentration_risk}[/{concentration_risk.lower()}]")
        risk_table.add_row("🎯 Largest Position", largest_position, "")
        risk_table.add_row("💰 Cash Allocation", f"{cash_allocation:.1f}%", "Good" if cash_allocation > 10 else "Low")
        risk_table.add_row("📈 Total Positions", f"{len(portfolio_df)}", "Diversified" if len(portfolio_df) > 2 else "Concentrated")
        
        console.print(risk_table)
    else:
        print_info("Risk Metrics:", "⚠️")
        print(f"  Portfolio Concentration: {max_weight:.1f}% ({concentration_risk})")
        print(f"  Largest Position: {largest_position}")
        print(f"  Cash Allocation: {cash_allocation:.1f}%")
        print(f"  Total Positions: {len(portfolio_df)}")


def process_portfolio(
    portfolio: pd.DataFrame | dict[str, list[object]] | list[dict[str, object]],
    cash: float,
    interactive: bool = True,
) -> tuple[pd.DataFrame, float]:
    # Use configured timezone for timestamps - use market open time (6:30 AM) for trades
    market_open_time = get_market_open_time()
    today_iso = format_timestamp_for_csv(market_open_time)
    portfolio_df = _ensure_df(portfolio)

    results: list[dict[str, object]] = []
    total_value = 0.0
    total_pnl = 0.0

    # ------- Interactive trade entry (supports MOO) -------
    if interactive:
        print_header("Portfolio Management", "📊")
        
        while True:
            # Display all information BEFORE the menu
            create_portfolio_table(portfolio_df)
            
            # Show cash balance - dual currency if in North American mode
            if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                try:
                    cash_balances = load_cash_balances(DATA_DIR)
                    if _HAS_RICH and console and not _FORCE_FALLBACK:
                        console.print(f"\n💰 [bold green]Cash Balances:[/bold green] CAD ${cash_balances.cad:,.2f} | USD ${cash_balances.usd:,.2f}")
                    else:
                        print(f"\n{Fore.GREEN}💰 Cash Balances: CAD ${cash_balances.cad:,.2f} | USD ${cash_balances.usd:,.2f}{Style.RESET_ALL}")
                except Exception:
                    if _HAS_RICH and console and not _FORCE_FALLBACK:
                        console.print(f"\n💰 [bold green]Cash Balance:[/bold green] ${cash:,.2f}")
                    else:
                        print(f"\n{Fore.GREEN}💰 Cash Balance: ${cash:,.2f}{Style.RESET_ALL}")
            else:
                if _HAS_RICH and console and not _FORCE_FALLBACK:
                    console.print(f"\n💰 [bold green]Cash Balance:[/bold green] ${cash:,.2f}")
                else:
                    print(f"\n{Fore.GREEN}💰 Cash Balance: ${cash:,.2f}{Style.RESET_ALL}")
            
            # Calculate portfolio value for risk metrics and ownership
            total_value = 0.0
            for _, row in portfolio_df.iterrows():
                shares = float(row.get('shares', 0))
                buy_price = float(row.get('buy_price', 0))
                total_value += shares * buy_price  # Use buy price as proxy for current value
            
            # Display risk metrics and ownership BEFORE menu
            _display_risk_metrics(portfolio_df, total_value, cash)
            _display_ownership_percentages(str(DATA_DIR))
            
            print_trade_menu()
            
            if _HAS_RICH and console and not _FORCE_FALLBACK:
                action = console.input("\n[bold cyan]Choose an action:[/bold cyan] ").strip().lower()
            else:
                action = input(f"\n{Fore.CYAN}Choose an action:{Style.RESET_ALL} ").strip().lower()

            if action == "b":
                print_header("Buy Order", "🛒")
                
                if _HAS_RICH and console and not _FORCE_FALLBACK:
                    ticker = console.input("🎯 [bold cyan]Enter ticker symbol:[/bold cyan] ").strip().upper()
                    order_type = console.input("📋 [bold cyan]Order type? 'm' = market-on-open, 'l' = limit:[/bold cyan] ").strip().lower()
                else:
                    ticker = input(f"{Fore.CYAN}🎯 Enter ticker symbol:{Style.RESET_ALL} ").strip().upper()
                    order_type = input(f"{Fore.CYAN}📋 Order type? 'm' = market-on-open, 'l' = limit:{Style.RESET_ALL} ").strip().lower()
                
                # Auto-detect and correct ticker symbol (will get buy_price later)
                original_ticker = ticker
                ticker = detect_and_correct_ticker(ticker)
                if ticker != original_ticker:
                    print(f"🔍 Auto-corrected ticker: {original_ticker} → {ticker}")

                try:
                    if _HAS_RICH and console and not _FORCE_FALLBACK:
                        shares = float(console.input("📈 [bold cyan]Enter number of shares:[/bold cyan] "))
                    else:
                        shares = float(input(f"{Fore.CYAN}📈 Enter number of shares:{Style.RESET_ALL} "))
                    if shares <= 0:
                        raise ValueError
                except ValueError:
                    print_error("Invalid share amount. Buy cancelled.")
                    continue

                if order_type == "m":
                    try:
                        if _HAS_RICH and console:
                            stop_loss_input = console.input("🛑 [bold cyan]Enter stop loss (or 0 to skip):[/bold cyan] ").strip()
                        else:
                            stop_loss_input = input(f"{Fore.CYAN}🛑 Enter stop loss (or 0 to skip):{Style.RESET_ALL} ").strip()
                        if stop_loss_input == "":
                            stop_loss = 0.0
                        else:
                            stop_loss = float(stop_loss_input)
                        if stop_loss < 0:
                            raise ValueError
                    except ValueError:
                        print_error("Invalid stop loss. Buy cancelled.")
                        continue

                    print_info(f"Fetching market data for {ticker}...", "📊")
                    s, e = trading_day_window()
                    fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
                    data = fetch.df
                    if data.empty:
                        print_error(f"MOO buy for {ticker} failed: no market data available (source={fetch.source})")
                        continue

                    o = float(data["Open"].iloc[-1].item()) if "Open" in data else float(data["Close"].iloc[-1].item())
                    exec_price = round(o, 2)
                    notional = exec_price * shares
                    
                    print_info(f"Market open price: ${exec_price:.2f}")
                    print_info(f"Total cost: ${notional:,.2f}")
                    
                    if notional > cash:
                        print_error(f"MOO buy for {ticker} failed: cost ${notional:,.2f} exceeds cash ${cash:,.2f}")
                        continue

                    log = {
                        "Date": today_iso,
                        "Ticker": ticker,
                        "Shares Bought": shares,
                        "Buy Price": exec_price,
                        "Cost Basis": notional,
                        "PnL": 0.0,
                        "Reason": "MANUAL BUY MOO - Filled",
                    }
                    # --- Manual BUY MOO logging ---
                    if os.path.exists(TRADE_LOG_CSV):
                        df_log = pd.read_csv(TRADE_LOG_CSV)
                        if df_log.empty:
                            df_log = pd.DataFrame([log])
                        else:
                            df_log = pd.concat([df_log, pd.DataFrame([log])], ignore_index=True)
                    else:
                        df_log = pd.DataFrame([log])
                    df_log.to_csv(TRADE_LOG_CSV, index=False)

                    # Check cash availability BEFORE updating portfolio
                    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                        try:
                            cash_balances = load_cash_balances(DATA_DIR)
                            currency = get_ticker_currency(ticker)
                            if currency == 'USD':
                                if not cash_balances.can_afford_usd(notional):
                                    if not handle_insufficient_funds(notional, 'USD', cash_balances.usd, ticker, DATA_DIR):
                                        continue
                                    # Reload balances after potential update
                                    cash_balances = load_cash_balances(DATA_DIR)
                            else:  # CAD
                                if not cash_balances.can_afford_cad(notional):
                                    if not handle_insufficient_funds(notional, 'CAD', cash_balances.cad, ticker, DATA_DIR):
                                        continue
                                    # Reload balances after potential update
                                    cash_balances = load_cash_balances(DATA_DIR)
                        except Exception as e:
                            print(f"Warning: Could not check dual currency balances: {e}")
                            if notional > cash:
                                if not handle_insufficient_funds(notional, 'CASH', cash, ticker, DATA_DIR):
                                    continue
                    else:
                        if notional > cash:
                            if not handle_insufficient_funds(notional, 'CASH', cash, ticker, DATA_DIR):
                                continue

                    # Update portfolio
                    rows = portfolio_df.loc[portfolio_df["ticker"].astype(str).str.upper() == ticker.upper()]
                    if rows.empty:
                        new_trade = {
                            "ticker": ticker,
                            "shares": float(shares),
                            "stop_loss": float(stop_loss),
                            "buy_price": float(exec_price),
                            "cost_basis": float(notional),
                        }
                        if portfolio_df.empty:
                            portfolio_df = pd.DataFrame([new_trade])
                        else:
                            portfolio_df = pd.concat([portfolio_df, pd.DataFrame([new_trade])], ignore_index=True)
                    else:
                        idx = rows.index[0]
                        cur_shares = float(portfolio_df.at[idx, "shares"])
                        cur_cost = float(portfolio_df.at[idx, "cost_basis"])
                        new_shares = cur_shares + float(shares)
                        new_cost = cur_cost + float(notional)
                        avg_price = new_cost / new_shares if new_shares else 0.0
                        portfolio_df.at[idx, "shares"] = new_shares
                        portfolio_df.at[idx, "cost_basis"] = new_cost
                        portfolio_df.at[idx, "buy_price"] = avg_price
                        portfolio_df.at[idx, "stop_loss"] = float(stop_loss)

                    # Update cash balances after successful portfolio update
                    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                        try:
                            cash_balances = load_cash_balances(DATA_DIR)
                            currency = get_ticker_currency(ticker)
                            if currency == 'USD':
                                cash_balances.spend_usd(notional)
                            else:  # CAD
                                cash_balances.spend_cad(notional)
                            save_cash_balances(cash_balances, DATA_DIR)
                            cash = cash_balances.total_cad_equivalent()
                        except Exception as e:
                            print(f"Warning: Could not update dual currency balances: {e}")
                            cash -= notional
                    else:
                        cash -= notional
                    
                    print_success(f"Manual BUY MOO for {ticker} filled at ${exec_price:.2f} ({fetch.source})", "🎉")
                    continue

                elif order_type == "l":
                    try:
                        if _HAS_RICH and console:
                            buy_price = float(console.input("💵 [bold cyan]Enter buy LIMIT price:[/bold cyan] "))
                            stop_loss_input = console.input("🛑 [bold cyan]Enter stop loss (or 0 to skip):[/bold cyan] ").strip()
                        else:
                            buy_price = float(input(f"{Fore.CYAN}💵 Enter buy LIMIT price:{Style.RESET_ALL} "))
                            stop_loss_input = input(f"{Fore.CYAN}🛑 Enter stop loss (or 0 to skip):{Style.RESET_ALL} ").strip()
                        if stop_loss_input == "":
                            stop_loss = 0.0
                        else:
                            stop_loss = float(stop_loss_input)
                        if buy_price <= 0 or stop_loss < 0:
                            raise ValueError
                    except ValueError:
                        print_error("Invalid input. Limit buy cancelled.")
                        continue

                    cash, portfolio_df = log_manual_buy(
                        buy_price, shares, ticker, stop_loss, cash, portfolio_df
                    )
                    continue
                else:
                    print_error("Unknown order type. Use 'm' or 'l'.")
                    continue

            if action == "s":
                print_header("Sell Order", "📤")
                
                try:
                    if _HAS_RICH and console:
                        ticker = console.input("🎯 [bold cyan]Enter ticker symbol:[/bold cyan] ").strip().upper()
                        shares = float(console.input("📉 [bold cyan]Enter number of shares to sell (LIMIT):[/bold cyan] "))
                        sell_price = float(console.input("💵 [bold cyan]Enter sell LIMIT price:[/bold cyan] "))
                    else:
                        ticker = input(f"{Fore.CYAN}🎯 Enter ticker symbol:{Style.RESET_ALL} ").strip().upper()
                        shares = float(input(f"{Fore.CYAN}📉 Enter number of shares to sell (LIMIT):{Style.RESET_ALL} "))
                        sell_price = float(input(f"{Fore.CYAN}💵 Enter sell LIMIT price:{Style.RESET_ALL} "))
                    
                    # Auto-detect and correct ticker symbol
                    original_ticker = ticker
                    ticker = detect_and_correct_ticker(ticker)
                    if ticker != original_ticker:
                        print(f"🔍 Auto-corrected ticker: {original_ticker} → {ticker}")
                    if shares <= 0 or sell_price <= 0:
                        raise ValueError
                except ValueError:
                    print_error("Invalid input. Manual sell cancelled.")
                    continue

                cash, portfolio_df = log_manual_sell(
                    sell_price, shares, ticker, cash, portfolio_df
                )
                continue

            if action == "c":
                print_header("Fund Contribution", "💵")
                
                try:
                    if _HAS_RICH and console:
                        contributor = console.input("👤 [bold cyan]Enter contributor name:[/bold cyan] ").strip()
                        amount = float(console.input("💰 [bold cyan]Enter contribution amount: $[/bold cyan]"))
                        notes = console.input("📝 [bold cyan]Enter notes (optional):[/bold cyan] ").strip()
                    else:
                        contributor = input(f"{Fore.CYAN}👤 Enter contributor name:{Style.RESET_ALL} ").strip()
                        amount = float(input(f"{Fore.CYAN}💰 Enter contribution amount: ${Style.RESET_ALL}"))
                        notes = input(f"{Fore.CYAN}📝 Enter notes (optional):{Style.RESET_ALL} ").strip()
                    if amount <= 0:
                        raise ValueError("Amount must be positive")
                except ValueError as e:
                    print_error(f"Invalid input: {e}. Contribution cancelled.")
                    continue

                new_total = save_fund_contribution(DATA_DIR, contributor, amount, "CONTRIBUTION", notes)
                print_success(f"Contribution logged: {contributor} contributed ${amount:,.2f}")
                print_info(f"Total fund contributions: ${new_total:,.2f}")
                
                # Show updated ownership
                ownership = calculate_ownership_percentages(DATA_DIR)
                print_info("Updated Ownership:", "📊")
                for name, percentage in ownership.items():
                    if _HAS_RICH and console:
                        console.print(f"   [bold cyan]{name}:[/bold cyan] [green]{percentage:.1f}%[/green]")
                    else:
                        print(f"   {Fore.CYAN}{name}:{Style.RESET_ALL} {Fore.GREEN}{percentage:.1f}%{Style.RESET_ALL}")
                continue

            if action == "w":
                print_header("Fund Withdrawal", "💸")
                
                try:
                    if _HAS_RICH and console:
                        contributor = console.input("👤 [bold cyan]Enter contributor name:[/bold cyan] ").strip()
                        amount = float(console.input("💸 [bold cyan]Enter withdrawal amount: $[/bold cyan]"))
                    else:
                        contributor = input(f"{Fore.CYAN}👤 Enter contributor name:{Style.RESET_ALL} ").strip()
                        amount = float(input(f"{Fore.CYAN}💸 Enter withdrawal amount: ${Style.RESET_ALL}"))
                    if amount <= 0:
                        raise ValueError("Amount must be positive")
                except ValueError as e:
                    print_error(f"Invalid input: {e}. Withdrawal cancelled.")
                    continue

                # Get current equity for liquidation calculation
                current_equity = float(cash)  # This will be updated with portfolio value later
                if not portfolio_df.empty:
                    current_equity += portfolio_df['Total Value'].sum()

                liquidation_info = calculate_liquidation_amount(DATA_DIR, contributor, amount, current_equity)
                
                if "error" in liquidation_info:
                    print_error(liquidation_info['error'])
                    continue

                print_info("Withdrawal Analysis:", "💰")
                print_info(f"{contributor}'s equity: ${liquidation_info['contributor_equity']:,.2f}")
                print_info(f"Withdrawal amount: ${liquidation_info['withdrawal_amount']:,.2f}")
                print_warning(f"Portfolio liquidation needed: {liquidation_info['liquidation_percentage']:.1f}%")
                print_info(f"Remaining equity: ${liquidation_info['remaining_equity']:,.2f}")
                
                if _HAS_RICH and console:
                    confirm = console.input("\n[bold yellow]Proceed with withdrawal? (y/n):[/bold yellow] ").strip().lower()
                else:
                    confirm = input(f"\n{Fore.YELLOW}Proceed with withdrawal? (y/n):{Style.RESET_ALL} ").strip().lower()
                
                if confirm == "y":
                    new_total = save_fund_contribution(DATA_DIR, contributor, -amount, "WITHDRAWAL", f"Withdrawal of ${amount:,.2f}")
                    print_success(f"Withdrawal logged: {contributor} withdrew ${amount:,.2f}")
                    
                    # Show updated ownership
                    ownership = calculate_ownership_percentages(DATA_DIR)
                    print_info("Updated Ownership:", "📊")
                    for name, percentage in ownership.items():
                        if _HAS_RICH and console:
                            console.print(f"   [bold cyan]{name}:[/bold cyan] [green]{percentage:.1f}%[/green]")
                        else:
                            print(f"   {Fore.CYAN}{name}:{Style.RESET_ALL} {Fore.GREEN}{percentage:.1f}%{Style.RESET_ALL}")
                else:
                    print_warning("Withdrawal cancelled.")
                continue

            if action == "u":
                update_cash_balances_manual(DATA_DIR)
                # Reload cash balances after update
                if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                    try:
                        cash_balances = load_cash_balances(DATA_DIR)
                        cash = cash_balances.total_cad_equivalent()
                    except Exception:
                        pass
                continue

            if action == "sync":
                if sync_fund_contributions_to_cad_balance(DATA_DIR):
                    # Reload cash balances after sync
                    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                        try:
                            cash_balances = load_cash_balances(DATA_DIR)
                            cash = cash_balances.total_cad_equivalent()
                        except Exception:
                            pass
                continue

            break  # proceed to pricing

    # ------- Daily pricing + stop-loss execution -------
    if not portfolio_df.empty:
        print_header("Portfolio Pricing & Stop-Loss Check", "📊")
        
    s, e = trading_day_window()
    for _, stock in portfolio_df.iterrows():
        ticker = str(stock["ticker"]).upper()
        shares = float(stock["shares"]) if not pd.isna(stock["shares"]) else 0.0
        cost = float(stock["buy_price"]) if not pd.isna(stock["buy_price"]) else 0.0
        cost_basis = float(stock["cost_basis"]) if not pd.isna(stock["cost_basis"]) else cost * shares
        stop = float(stock["stop_loss"]) if not pd.isna(stock["stop_loss"]) else 0.0

        print_info(f"Fetching data for {ticker}...", "📈")
        fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
        data = fetch.df

        if data.empty:
            print_warning(f"No data for {ticker} (source={fetch.source})")
            company_name = get_company_name(ticker)
            row = {
                "Date": today_iso, "Ticker": ticker, "Company": company_name, "Shares": shares,
                "Buy Price": cost, "Cost Basis": cost_basis, "Stop Loss": stop,
                "Current Price": "", "Total Value": "", "PnL": "",
                "Action": "NO DATA", "Cash Balance": "", "Total Equity": "",
            }
            results.append(row)
            continue

        o = float(data["Open"].iloc[-1].item()) if "Open" in data else np.nan
        h = float(data["High"].iloc[-1].item())
        l = float(data["Low"].iloc[-1].item())
        c = float(data["Close"].iloc[-1].item())
        if np.isnan(o):
            o = c

        if stop and l <= stop:
            exec_price = round(o if o <= stop else stop, 2)
            value = round(exec_price * shares, 2)
            pnl = round((exec_price - cost) * shares, 2)
            action = "SELL - Stop Loss Triggered"
            
            print_error(f"🚨 STOP LOSS TRIGGERED for {ticker}!")
            print_warning(f"   Selling {shares:,} shares at ${exec_price:.2f}")
            print_info(f"   PnL: ${pnl:,.2f}")
            
            # Update cash balances based on currency
            if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
                try:
                    cash_balances = load_cash_balances(DATA_DIR)
                    currency = get_ticker_currency(ticker)
                    if currency == 'USD':
                        cash_balances.add_usd(value)
                    else:  # CAD
                        cash_balances.add_cad(value)
                    save_cash_balances(cash_balances, DATA_DIR)
                    cash = cash_balances.total_cad_equivalent()
                except Exception as e:
                    print(f"Warning: Could not update dual currency balances for stop-loss: {e}")
                    cash += value
            else:
                cash += value
                
            portfolio_df = log_sell(ticker, shares, exec_price, cost, pnl, portfolio_df)
            company_name = get_company_name(ticker)
            row = {
                "Date": today_iso, "Ticker": ticker, "Company": company_name, "Shares": shares,
                "Buy Price": cost, "Cost Basis": cost_basis, "Stop Loss": stop,
                "Current Price": exec_price, "Total Value": value, "PnL": pnl,
                "Action": action, "Cash Balance": "", "Total Equity": "",
            }
        else:
            price = round(c, 2)
            value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)
            action = "HOLD"
            total_value += value
            total_pnl += pnl
            company_name = get_company_name(ticker)
            row = {
                "Date": today_iso, "Ticker": ticker, "Company": company_name, "Shares": shares,
                "Buy Price": cost, "Cost Basis": cost_basis, "Stop Loss": stop,
                "Current Price": price, "Total Value": value, "PnL": pnl,
                "Action": action, "Cash Balance": "", "Total Equity": "",
            }

        results.append(row)

    # Calculate totals dynamically - no need to store in CSV
    print_header("Portfolio Summary", "📈")
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        summary_table = Table(title="💰 Financial Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Amount", justify="right", style="green")
        
        summary_table.add_row("📊 Portfolio Value", f"${total_value:,.2f}")
        summary_table.add_row("💹 Total P&L", f"${total_pnl:,.2f}" if total_pnl >= 0 else f"[red]${total_pnl:,.2f}[/red]")
        summary_table.add_row("💰 Cash Balance", f"${cash:,.2f}")
        summary_table.add_row("🏦 Total Equity", f"${total_value + cash:,.2f}")
        
        fund_total = calculate_fund_contributions_total(str(DATA_DIR))
        summary_table.add_row("💵 Fund Contributions", f"${fund_total:,.2f}")
        
        console.print(summary_table)
    else:
        print_info(f"Portfolio Total Value: ${total_value:,.2f}", "📊")
        if total_pnl >= 0:
            print_success(f"Total PnL: ${total_pnl:,.2f}", "💹")
        else:
            print_error(f"Total PnL: ${total_pnl:,.2f}", "📉")
        print_info(f"Cash Balance: ${cash:,.2f}", "💰")
        print_success(f"Total Equity: ${total_value + cash:,.2f}", "🏦")
        
        # Display fund contributions total
        fund_total = calculate_fund_contributions_total(str(DATA_DIR))
        print_info(f"Fund Contributions Total: ${fund_total:,.2f}", "💵")

    df_out = pd.DataFrame(results)
    if PORTFOLIO_CSV.exists():
        existing = pd.read_csv(PORTFOLIO_CSV)
        # Migrate old date-only entries to timestamp format
        if len(existing) > 0 and len(str(existing["Date"].iloc[0])) == 10:
            tz_name = get_timezone_name()
            existing["Date"] = existing["Date"].apply(lambda x: f"{x} 00:00:00 {tz_name}" if len(str(x)) == 10 else x)
        existing = existing[existing["Date"] != str(today_iso)]
        print("Saving results to CSV...")
        df_out = pd.concat([existing, df_out], ignore_index=True)
    df_out.to_csv(PORTFOLIO_CSV, index=False)

    return portfolio_df, cash



# ------------------------------
# Trade logging
# ------------------------------

def log_sell(
    ticker: str,
    shares: float,
    price: float,
    cost: float,
    pnl: float,
    portfolio: pd.DataFrame,
) -> pd.DataFrame:
    # Use configured timezone for timestamps
    today = format_timestamp_for_csv()
    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Sold": shares,
        "Sell Price": price,
        "Cost Basis": cost,
        "PnL": pnl,
        "Reason": "AUTOMATED SELL - STOPLOSS TRIGGERED",
    }
    print_error(f"{ticker} stop loss was met. Selling all shares.", "🚨")
    portfolio = portfolio[portfolio["ticker"] != ticker]

    if TRADE_LOG_CSV.exists():
        df = pd.read_csv(TRADE_LOG_CSV)
        if df.empty:
            df = pd.DataFrame([log])
        else:
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)
    return portfolio

def log_manual_buy(
    buy_price: float,
    shares: float,
    ticker: str,
    stoploss: float,
    cash: float,
    llm_portfolio: pd.DataFrame,
    interactive: bool = True,
) -> tuple[float, pd.DataFrame]:
    # Use configured timezone for timestamps - use market open time (6:30 AM) for trades
    market_open_time = get_market_open_time()
    today = format_timestamp_for_csv(market_open_time)

    # Auto-detect and correct ticker symbol using buy price context
    original_ticker = ticker
    ticker = detect_and_correct_ticker(ticker, buy_price)
    if ticker != original_ticker:
        print(f"🔍 Auto-corrected ticker: {original_ticker} → {ticker}")

    if interactive:
        check = input(
            f"You are placing a BUY LIMIT for {shares} {ticker} at ${buy_price:.2f}.\n"
            f"If this is a mistake, type '1': "
        )
        if check == "1":
            print("Returning...")
            return cash, llm_portfolio

    if not isinstance(llm_portfolio, pd.DataFrame) or llm_portfolio.empty:
        llm_portfolio = pd.DataFrame(
            columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]
        )

    s, e = trading_day_window()
    fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
    data = fetch.df
    if data.empty:
        print(f"Manual buy for {ticker} failed: no market data available (source={fetch.source}).")
        return cash, llm_portfolio

    o = float(data.get("Open", [np.nan])[-1])
    h = float(data["High"].iloc[-1].item())
    l = float(data["Low"].iloc[-1].item())
    if np.isnan(o):
        o = float(data["Close"].iloc[-1].item())

    if o <= buy_price:
        exec_price = o
    elif l <= buy_price:
        exec_price = buy_price
    else:
        print(f"Buy limit ${buy_price:.2f} for {ticker} not reached today (range {l:.2f}-{h:.2f}). Order not filled.")
        return cash, llm_portfolio

    cost_amt = exec_price * shares
    
    # Check cash availability using dual currency if available
    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
        try:
            cash_balances = load_cash_balances(DATA_DIR)
            currency = get_ticker_currency(ticker)
            if currency == 'USD':
                if not cash_balances.can_afford_usd(cost_amt):
                    if not handle_insufficient_funds(cost_amt, 'USD', cash_balances.usd, ticker, DATA_DIR):
                        return cash, llm_portfolio
                    # Reload balances after potential update
                    cash_balances = load_cash_balances(DATA_DIR)
            else:  # CAD
                if not cash_balances.can_afford_cad(cost_amt):
                    if not handle_insufficient_funds(cost_amt, 'CAD', cash_balances.cad, ticker, DATA_DIR):
                        return cash, llm_portfolio
                    # Reload balances after potential update
                    cash_balances = load_cash_balances(DATA_DIR)
        except Exception as e:
            print(f"Warning: Could not check dual currency balances: {e}")
            if cost_amt > cash:
                if not handle_insufficient_funds(cost_amt, 'CASH', cash, ticker, DATA_DIR):
                    return cash, llm_portfolio
    else:
        if cost_amt > cash:
            if not handle_insufficient_funds(cost_amt, 'CASH', cash, ticker, DATA_DIR):
                return cash, llm_portfolio

    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Bought": shares,
        "Buy Price": exec_price,
        "Cost Basis": cost_amt,
        "PnL": 0.0,
        "Reason": "MANUAL BUY LIMIT - Filled",
    }
    if os.path.exists(TRADE_LOG_CSV):
        df = pd.read_csv(TRADE_LOG_CSV)
        if df.empty:
            df = pd.DataFrame([log])
        else:
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)

    rows = llm_portfolio.loc[llm_portfolio["ticker"].str.upper() == ticker.upper()]
    if rows.empty:
        if llm_portfolio.empty:
            llm_portfolio = pd.DataFrame([{
                "ticker": ticker,
                "shares": float(shares),
                "stop_loss": float(stoploss),
                "buy_price": float(exec_price),
                "cost_basis": float(cost_amt),
            }])
        else:
            llm_portfolio = pd.concat(
                [llm_portfolio, pd.DataFrame([{
                    "ticker": ticker,
                    "shares": float(shares),
                    "stop_loss": float(stoploss),
                    "buy_price": float(exec_price),
                    "cost_basis": float(cost_amt),
                }])],
                ignore_index=True
            )
    else:
        idx = rows.index[0]
        cur_shares = float(llm_portfolio.at[idx, "shares"])
        cur_cost = float(llm_portfolio.at[idx, "cost_basis"])
        new_shares = cur_shares + float(shares)
        new_cost = cur_cost + float(cost_amt)
        llm_portfolio.at[idx, "shares"] = new_shares
        llm_portfolio.at[idx, "cost_basis"] = new_cost
        llm_portfolio.at[idx, "buy_price"] = new_cost / new_shares if new_shares else 0.0
        llm_portfolio.at[idx, "stop_loss"] = float(stoploss)

    # Update cash balances based on currency
    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
        try:
            cash_balances = load_cash_balances(DATA_DIR)
            currency = get_ticker_currency(ticker)
            if currency == 'USD':
                if not cash_balances.spend_usd(cost_amt):
                    # This should not happen since we checked above, but just in case
                    print(f"❌ Unexpected error: Insufficient USD cash after balance check")
                    return cash, llm_portfolio
            else:  # CAD
                if not cash_balances.spend_cad(cost_amt):
                    # This should not happen since we checked above, but just in case
                    print(f"❌ Unexpected error: Insufficient CAD cash after balance check")
                    return cash, llm_portfolio
            save_cash_balances(cash_balances, DATA_DIR)
            cash = cash_balances.total_cad_equivalent()
        except Exception as e:
            print(f"Warning: Could not update dual currency balances: {e}")
            cash -= cost_amt
    else:
        cash -= cost_amt
    
    print_success(f"Manual BUY LIMIT for {ticker} filled at ${exec_price:.2f} ({fetch.source})", "🎉")
    return cash, llm_portfolio

def log_manual_sell(
    sell_price: float,
    shares_sold: float,
    ticker: str,
    cash: float,
    llm_portfolio: pd.DataFrame,
    reason: str | None = None,
    interactive: bool = True,
) -> tuple[float, pd.DataFrame]:
    # Use configured timezone for timestamps - use market open time (6:30 AM) for trades
    market_open_time = get_market_open_time()
    today = format_timestamp_for_csv(market_open_time)
    
    # Auto-detect and correct ticker symbol
    original_ticker = ticker
    ticker = detect_and_correct_ticker(ticker)
    if ticker != original_ticker:
        print(f"🔍 Auto-corrected ticker: {original_ticker} → {ticker}")
    
    if interactive:
        reason = input(
            f"""You are placing a SELL LIMIT for {shares_sold} {ticker} at ${sell_price:.2f}.
If this is a mistake, enter 1. """
        )
    if reason == "1":
        print("Returning...")
        return cash, llm_portfolio
    elif reason is None:
        reason = ""

    if ticker not in llm_portfolio["ticker"].values:
        print(f"Manual sell for {ticker} failed: ticker not in portfolio.")
        return cash, llm_portfolio

    ticker_row = llm_portfolio[llm_portfolio["ticker"] == ticker]
    total_shares = float(ticker_row["shares"].item())  # Keep as float to preserve fractional shares
    if shares_sold > total_shares:
        print(f"Manual sell for {ticker} failed: trying to sell {shares_sold} shares but only own {total_shares}.")
        return cash, llm_portfolio

    s, e = trading_day_window()
    fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
    data = fetch.df
    if data.empty:
        print(f"Manual sell for {ticker} failed: no market data available (source={fetch.source}).")
        return cash, llm_portfolio

    o = float(data["Open"].iloc[-1].item()) if "Open" in data else np.nan
    h = float(data["High"].iloc[-1].item())
    l = float(data["Low"].iloc[-1].item())
    if np.isnan(o):
        o = float(data["Close"].iloc[-1].item())

    if o >= sell_price:
        exec_price = o
    elif h >= sell_price:
        exec_price = sell_price
    else:
        print(f"Sell limit ${sell_price:.2f} for {ticker} not reached today (range {l:.2f}-{h:.2f}). Order not filled.")
        return cash, llm_portfolio

    buy_price = float(ticker_row["buy_price"].item())
    cost_basis = buy_price * shares_sold
    pnl = exec_price * shares_sold - cost_basis

    log = {
        "Date": today, "Ticker": ticker,
        "Shares Bought": "", "Buy Price": "",
        "Cost Basis": cost_basis, "PnL": pnl,
        "Reason": f"MANUAL SELL LIMIT - {reason}", "Shares Sold": shares_sold,
        "Sell Price": exec_price,
    }
    if os.path.exists(TRADE_LOG_CSV):
        df = pd.read_csv(TRADE_LOG_CSV)
        if df.empty:
            df = pd.DataFrame([log])
        else:
            df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)


    if total_shares == shares_sold:
        llm_portfolio = llm_portfolio[llm_portfolio["ticker"] != ticker]
    else:
        row_index = ticker_row.index[0]
        llm_portfolio.at[row_index, "shares"] = total_shares - shares_sold
        llm_portfolio.at[row_index, "cost_basis"] = (
            llm_portfolio.at[row_index, "shares"] * llm_portfolio.at[row_index, "buy_price"]
        )

    # Update cash balances based on currency
    proceeds = shares_sold * exec_price
    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
        try:
            cash_balances = load_cash_balances(DATA_DIR)
            currency = get_ticker_currency(ticker)
            if currency == 'USD':
                cash_balances.add_usd(proceeds)
            else:  # CAD
                cash_balances.add_cad(proceeds)
            save_cash_balances(cash_balances, DATA_DIR)
            cash = cash_balances.total_cad_equivalent()
        except Exception as e:
            print(f"Warning: Could not update dual currency balances: {e}")
            cash += proceeds
    else:
        cash += proceeds
    
    print_success(f"Manual SELL LIMIT for {ticker} filled at ${exec_price:.2f} ({fetch.source})", "💰")
    return cash, llm_portfolio



# ------------------------------
# Reporting / Metrics
# ------------------------------

# ------------------------------
# Portfolio State Management
# ------------------------------

def load_latest_portfolio_state(
    file: str,
) -> tuple[pd.DataFrame | list[dict[str, Any]], float]:
    """Load the most recent portfolio snapshot and cash balance."""
    df = pd.read_csv(file)
    if df.empty:
        portfolio = pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"])
        # Ensure shares column is float even for empty DataFrame
        portfolio['shares'] = portfolio['shares'].astype(float)
        print("Portfolio CSV is empty. Returning set amount of cash for creating portfolio.")
        
        # Check if we're in North American mode and should use dual currency
        if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
            cash_balances = prompt_for_dual_currency_cash()
            save_cash_balances(cash_balances, DATA_DIR)
            # Return total CAD equivalent for compatibility with existing code
            cash = cash_balances.total_cad_equivalent()
            print(f"Using dual currency mode. Total equivalent: ${cash:,.2f} CAD")
        else:
            try:
                cash = float(input("What would you like your starting cash amount to be? "))
            except ValueError:
                raise ValueError(
                    "Cash could not be converted to float datatype. Please enter a valid number."
                )
        return portfolio, cash

    non_total = df[df["Ticker"] != "TOTAL"].copy()
    # Use proper timezone-aware parsing
    non_total["Date"] = non_total["Date"].apply(parse_csv_timestamp)

    latest_date = non_total["Date"].max()
    latest_tickers = non_total[non_total["Date"] == latest_date].copy()
    sold_mask = latest_tickers["Action"].astype(str).str.startswith("SELL")
    latest_tickers = latest_tickers[~sold_mask].copy()
    latest_tickers.drop(
        columns=[
            "Date",
            "Cash Balance",
            "Total Equity",
            "Action",
            "Current Price",
            "PnL",
            "Total Value",
        ],
        inplace=True,
        errors="ignore",
    )
    latest_tickers.rename(
        columns={
            "Cost Basis": "cost_basis",
            "Buy Price": "buy_price",
            "Shares": "shares",
            "Ticker": "ticker",
            "Stop Loss": "stop_loss",
        },
        inplace=True,
    )
    
    # Ensure shares column is float to preserve fractional shares
    if 'shares' in latest_tickers.columns:
        latest_tickers['shares'] = latest_tickers['shares'].astype(float)
    # Ensure we always return a DataFrame, even if empty
    if latest_tickers.empty:
        latest_tickers = pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"])
        # Ensure shares column is float even for empty DataFrame
        latest_tickers['shares'] = latest_tickers['shares'].astype(float)
    else:
        latest_tickers = latest_tickers.reset_index(drop=True)

    # Load cash balance from dual currency system instead of TOTAL rows
    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
        try:
            cash_balances = load_cash_balances(DATA_DIR)
            cash = cash_balances.total_cad_equivalent()
        except Exception:
            # Fallback to default cash if dual currency not available
            cash = 1000.0
    else:
        # Fallback to default cash for single currency mode
        cash = 1000.0
    
    return latest_tickers, cash


def handle_insufficient_funds(needed_amount: float, currency: str, current_balance: float, ticker: str, data_dir: Path = None) -> bool:
    """
    Handle insufficient funds by offering to update cash balances.
    Returns True if user updated balance and there are now sufficient funds, False otherwise.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    if not (_HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY):
        # Single currency mode - offer simple cash update
        print_error(f"Insufficient Funds for {ticker}", "💰")
        print_warning(f"Need: ${needed_amount:,.2f}")
        print_info(f"Have: ${current_balance:,.2f}")
        print_error(f"Short: ${needed_amount - current_balance:,.2f}")
        
        response = input(f"\nWould you like to add more cash to complete this purchase? (y/n): ").strip().lower()
        if response == 'y':
            try:
                additional_cash = float(input(f"Enter additional cash amount: $"))
                if additional_cash <= 0:
                    print("❌ Amount must be positive")
                    return False
                # Note: In single currency mode, we don't actually update the balance
                # This is more of a "promise" that the user will fund the account
                print(f"✅ Proceeding with purchase assuming ${additional_cash:,.2f} additional funding")
                return True
            except ValueError:
                print("❌ Invalid amount entered")
                return False
        return False
    
    # Dual currency mode - offer specific currency update
    print_error(f"Insufficient {currency} Funds for {ticker}", "💰")
    print_warning(f"Need: ${needed_amount:,.2f} {currency}")
    print_info(f"Have: ${current_balance:,.2f} {currency}")
    print_error(f"Short: ${needed_amount - current_balance:,.2f} {currency}")
    
    response = input(f"\nWould you like to add more {currency} to complete this purchase? (y/n): ").strip().lower()
    if response != 'y':
        return False
    
    try:
        # Load current balances
        cash_balances = load_cash_balances(data_dir)
        
        # Show current balances
        print(f"\n💰 Current Cash Balances:")
        print(f"   CAD: ${cash_balances.cad:,.2f}")
        print(f"   USD: ${cash_balances.usd:,.2f}")
        
        # Ask for the amount to add
        amount_needed = needed_amount - current_balance
        suggested_amount = max(amount_needed, amount_needed * 1.1)  # Suggest 10% buffer
        
        amount_input = input(f"Enter {currency} amount to add (suggested: ${suggested_amount:,.2f}): $").strip()
        if amount_input == "":
            amount_to_add = suggested_amount
        else:
            amount_to_add = float(amount_input)
            
        if amount_to_add <= 0:
            print("❌ Amount must be positive")
            return False
        
        # Add the funds
        if currency == 'USD':
            cash_balances.add_usd(amount_to_add)
            new_balance = cash_balances.usd
        else:  # CAD
            cash_balances.add_cad(amount_to_add)
            new_balance = cash_balances.cad
        
        # Save the updated balances
        save_cash_balances(cash_balances, data_dir)
        
        print(f"✅ Added ${amount_to_add:,.2f} {currency}")
        print(f"   New {currency} balance: ${new_balance:,.2f}")
        
        # Check if we now have sufficient funds
        if new_balance >= needed_amount:
            print(f"✅ Sufficient funds available for {ticker} purchase!")
            return True
        else:
            print(f"⚠️  Still short ${needed_amount - new_balance:,.2f} {currency} for this purchase")
            return False
            
    except ValueError:
        print("❌ Invalid amount entered")
        return False
    except Exception as e:
        print(f"❌ Error updating cash balances: {e}")
        return False


def update_cash_balances_manual(data_dir: Path = None) -> None:
    """Manually update cash balances - useful for deposits, withdrawals, or corrections"""
    if data_dir is None:
        data_dir = DATA_DIR
    
    if not (_HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY):
        print("❌ Dual currency support not available. Cannot update cash balances.")
        return
    
    try:
        # Load current balances
        cash_balances = load_cash_balances(data_dir)
        print(f"\n💰 Current Cash Balances:")
        print(f"   CAD: ${cash_balances.cad:,.2f}")
        print(f"   USD: ${cash_balances.usd:,.2f}")
        print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
        
        # Get user input
        action = input("\nWhat would you like to do?\n'c' = add/remove CAD, 'u' = add/remove USD, 's' = set exact amounts, 'q' = quit: ").strip().lower()
        
        if action == 'q':
            return
            
        elif action == 'c':
            try:
                amount = float(input("Enter CAD amount (positive to add, negative to remove): $"))
                if amount >= 0:
                    cash_balances.add_cad(amount)
                    print(f"✅ Added ${amount:,.2f} CAD")
                else:
                    if cash_balances.can_afford_cad(abs(amount)):
                        cash_balances.spend_cad(abs(amount))
                        print(f"✅ Removed ${abs(amount):,.2f} CAD")
                    else:
                        print(f"❌ Cannot remove ${abs(amount):,.2f} CAD - insufficient balance")
                        return
            except ValueError:
                print("❌ Invalid amount entered")
                return
                
        elif action == 'u':
            try:
                amount = float(input("Enter USD amount (positive to add, negative to remove): $"))
                if amount >= 0:
                    cash_balances.add_usd(amount)
                    print(f"✅ Added ${amount:,.2f} USD")
                else:
                    if cash_balances.can_afford_usd(abs(amount)):
                        cash_balances.spend_usd(abs(amount))
                        print(f"✅ Removed ${abs(amount):,.2f} USD")
                    else:
                        print(f"❌ Cannot remove ${abs(amount):,.2f} USD - insufficient balance")
                        return
            except ValueError:
                print("❌ Invalid amount entered")
                return
                
        elif action == 's':
            try:
                cad_amount = float(input("Enter exact CAD balance: $"))
                usd_amount = float(input("Enter exact USD balance: $"))
                if cad_amount < 0 or usd_amount < 0:
                    print("❌ Balances cannot be negative")
                    return
                cash_balances.cad = cad_amount
                cash_balances.usd = usd_amount
                print(f"✅ Set balances to CAD ${cad_amount:,.2f} and USD ${usd_amount:,.2f}")
            except ValueError:
                print("❌ Invalid amounts entered")
                return
        else:
            print("❌ Invalid option")
            return
        
        # Save the updated balances
        save_cash_balances(cash_balances, data_dir)
        
        # Show final balances
        print(f"\n💰 Updated Cash Balances:")
        print(f"   CAD: ${cash_balances.cad:,.2f}")
        print(f"   USD: ${cash_balances.usd:,.2f}")
        print(f"   Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
        
    except Exception as e:
        print(f"❌ Error updating cash balances: {e}")


def main(file: str | None = None, data_dir: Path | None = None) -> None:
    """Check versions, then run the trading script."""
    # Set up data directory first
    if data_dir is not None:
        set_data_dir(data_dir)
    else:
        # Use default 'my trading' directory
        set_data_dir(DEFAULT_DATA_DIR)
    
    # Determine portfolio file path
    if file is not None:
        portfolio_file = file
    else:
        # Use the default portfolio file in the data directory
        portfolio_file = str(PORTFOLIO_CSV)
    
    # Show formatting mode
    if _FORCE_FALLBACK:
        if _FORCE_COLORAMA_ONLY:
            print("🧪 Testing Mode: Colorama Only (Rich disabled)")
        else:
            print("🧪 Testing Mode: Plain Text (Rich and Colorama disabled)")
    elif _HAS_RICH:
        print("🎨 Rich Formatting Mode: Full visual enhancements")
    else:
        print("🎨 Colorama Mode: Basic colors and emojis")
    
    print(f"Using portfolio file: {portfolio_file}")
    print(f"Using data directory: {DATA_DIR}")
    
    llm_portfolio, cash = load_latest_portfolio_state(portfolio_file)
    llm_portfolio, cash = process_portfolio(llm_portfolio, cash)
    
    print_header("Processing Complete", "🎉")
    print_success("Portfolio processing complete!")
    print_info(f"Cash balance: ${cash:,.2f}", "💰")
    if not llm_portfolio.empty:
        print_info(f"Holdings: {len(llm_portfolio)} positions", "📊")
    
    # Display fund contributions total
    fund_total = calculate_fund_contributions_total(str(DATA_DIR))
    print_info(f"Fund contributions total: ${fund_total:,.2f}", "💵")
    
    print_info("To generate prompts, use the menu options:", "💡")
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print("   [cyan]'d'[/cyan] for daily trading prompt")
        console.print("   [cyan]'w'[/cyan] for weekly deep research prompt")
    else:
        print(f"   {Fore.CYAN}'d'{Style.RESET_ALL} for daily trading prompt")
        print(f"   {Fore.CYAN}'w'{Style.RESET_ALL} for weekly deep research prompt")


def load_fund_contributions(data_dir: str) -> pd.DataFrame:
    """Load fund contributions from CSV."""
    contributions_file = os.path.join(data_dir, "fund_contributions.csv")
    if os.path.exists(contributions_file):
        df = pd.read_csv(contributions_file)
        
        # Remove Running_Total column if it exists (we calculate this dynamically now)
        if "Running_Total" in df.columns:
            df = df.drop(columns=["Running_Total"])
            # Save the updated format
            df.to_csv(contributions_file, index=False)
            print("ℹ️  Migrated fund_contributions.csv: Removed Running_Total column (now calculated dynamically)")
        
        # Migrate old "Date" column to "Timestamp" if needed
        if "Date" in df.columns and "Timestamp" not in df.columns:
            df = df.rename(columns={"Date": "Timestamp"})
            # Convert date-only timestamps to full timestamps with configured timezone (assume 00:00:00 for old entries)
            tz_name = get_timezone_name()
            df["Timestamp"] = df["Timestamp"].apply(lambda x: f"{x} 00:00:00 {tz_name}" if len(str(x)) == 10 else x)
            # Save the updated format
            df.to_csv(contributions_file, index=False)
        # Also migrate old timestamps without timezone to configured timezone format
        elif "Timestamp" in df.columns and not df["Timestamp"].astype(str).str.contains(f"{get_timezone_name()}|UTC|GMT").any():
            # Convert old timestamps without timezone to configured timezone format
            tz_name = get_timezone_name()
            df["Timestamp"] = df["Timestamp"].apply(lambda x: f"{x} {tz_name}" if tz_name not in str(x) and "UTC" not in str(x) and "GMT" not in str(x) else x)
            # Save the updated format
            df.to_csv(contributions_file, index=False)
        return df
    else:
        # Create empty DataFrame with expected columns
        return pd.DataFrame(columns=["Timestamp", "Contributor", "Amount", "Type", "Notes"])


def calculate_fund_contributions_total(data_dir: str) -> float:
    """Calculate the current running total of fund contributions dynamically."""
    df = load_fund_contributions(data_dir)
    
    if len(df) == 0:
        return 0.0
    
    # Sum all contributions and withdrawals
    total = 0.0
    for _, row in df.iterrows():
        amount = row["Amount"]
        if row["Type"] == "WITHDRAWAL":
            total += amount  # amount should already be negative for withdrawals
        else:
            total += amount
    
    return total


def save_fund_contribution(data_dir: str, contributor: str, amount: float, contribution_type: str = "CONTRIBUTION", notes: str = ""):
    """Save a new fund contribution and update CAD balance automatically."""
    contributions_file = os.path.join(data_dir, "fund_contributions.csv")
    # Use configured timezone
    timestamp = format_timestamp_for_csv()
    
    # Load existing contributions
    df = load_fund_contributions(data_dir)
    
    # Create new row (no more Running_Total column)
    new_row = {
        "Timestamp": timestamp,
        "Contributor": contributor,
        "Amount": amount,
        "Type": contribution_type,
        "Notes": notes
    }
    
    # Add to DataFrame and save
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(contributions_file, index=False)
    
    # Calculate the new total dynamically
    new_total = calculate_fund_contributions_total(data_dir)
    
    # Optionally update CAD balance if dual currency is enabled
    if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
        try:
            data_path = Path(data_dir)
            cash_balances = load_cash_balances(data_path)
            
            # Ask user if they want to update CAD balance
            if contribution_type == "CONTRIBUTION":
                update_prompt = f"Update CAD balance by adding ${amount:,.2f}? (y/n): "
                balance_change_msg = f"💰 Added ${amount:,.2f} CAD to cash balance"
            elif contribution_type == "WITHDRAWAL":
                update_prompt = f"Update CAD balance by removing ${abs(amount):,.2f}? (y/n): "
                balance_change_msg = f"💰 Removed ${abs(amount):,.2f} CAD from cash balance"
            else:
                # For other types, skip the balance update
                return new_total
            
            print(f"\n💰 Current CAD balance: ${cash_balances.cad:,.2f}")
            response = input(update_prompt).strip().lower()
            
            if response == 'y':
                if contribution_type == "CONTRIBUTION":
                    cash_balances.add_cad(amount)
                elif contribution_type == "WITHDRAWAL":
                    cash_balances.add_cad(amount)  # amount is negative for withdrawals
                
                save_cash_balances(cash_balances, data_path)
                print(balance_change_msg)
                print(f"💰 New CAD balance: ${cash_balances.cad:,.2f}")
            else:
                print("💰 CAD balance left unchanged")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not update CAD balance: {e}")
            print("   Fund contribution recorded but cash balance not updated.")
    
    return new_total


def sync_fund_contributions_to_cad_balance(data_dir: str) -> bool:
    """
    Sync existing fund contributions to CAD balance.
    This reconciles the fund_contributions.csv total with cash_balances.json CAD amount.
    """
    if not (_HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY):
        print("⚠️  Dual currency mode not enabled. Sync not available.")
        return False
    
    try:
        data_path = Path(data_dir)
        
        # Load current contributions and calculate total
        df = load_fund_contributions(data_dir)
        if len(df) == 0:
            print("📊 No fund contributions found. Nothing to sync.")
            return True
        
        # Calculate net contributions using the dynamic function
        total_contributions = calculate_fund_contributions_total(data_dir)
        
        # Load current cash balances
        cash_balances = load_cash_balances(data_path)
        current_cad = cash_balances.cad
        
        print(f"📊 Fund Contribution Sync Analysis:")
        print(f"   Net fund contributions: ${total_contributions:,.2f} CAD")
        print(f"   Current CAD balance: ${current_cad:,.2f} CAD")
        print(f"   Difference: ${current_cad - total_contributions:,.2f} CAD")
        
        if abs(current_cad - total_contributions) < 0.01:  # Within 1 cent
            print("✅ CAD balance is already in sync with fund contributions!")
            return True
        
        response = input(f"\nSet CAD balance to match fund contributions (${total_contributions:,.2f})? (y/n): ").strip().lower()
        if response == 'y':
            cash_balances.cad = total_contributions
            save_cash_balances(cash_balances, data_path)
            print(f"✅ CAD balance updated to ${cash_balances.cad:,.2f}")
            return True
        else:
            print("Sync cancelled.")
            return False
            
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        return False


def calculate_ownership_percentages(data_dir: str) -> Dict[str, float]:
    """Calculate current ownership percentages for each contributor based on equity shares."""
    df = load_fund_contributions(data_dir)
    
    if len(df) == 0:
        return {}
    
    # Calculate current total fund equity (portfolio + cash)
    current_equity = get_current_fund_equity(data_dir)
    
    if current_equity <= 0:
        return {}
    
    # Calculate shares owned by each contributor
    contributor_shares = defaultdict(float)
    total_shares_outstanding = 0.0
    
    for _, row in df.iterrows():
        amount = row["Amount"]
        contributor = row["Contributor"]
        
        if row["Type"] == "WITHDRAWAL":
            amount = -amount  # Withdrawals are negative
        
        # Calculate fund value per share at time of transaction
        # For now, use a simplified approach - in production you'd track this historically
        fund_value_per_share = get_fund_value_per_share_at_time(data_dir, row["Timestamp"])
        
        if fund_value_per_share > 0:
            shares_purchased = amount / fund_value_per_share
            contributor_shares[contributor] += shares_purchased
            total_shares_outstanding += shares_purchased
    
    if total_shares_outstanding <= 0:
        return {}
    
    # Calculate ownership percentages based on shares
    percentages = {}
    for contributor, shares in contributor_shares.items():
        if shares > 0:  # Only show contributors with positive shares
            percentages[contributor] = (shares / total_shares_outstanding) * 100
    
    return percentages


def get_current_fund_equity(data_dir: str) -> float:
    """Get current total fund equity (portfolio value + cash balance)."""
    try:
        # Load current portfolio
        portfolio_csv = Path(data_dir) / "llm_portfolio_update.csv"
        if not portfolio_csv.exists():
            return 0.0
        
        df = pd.read_csv(portfolio_csv)
        if df.empty:
            return 0.0
        
        # Get the most recent date's data
        df['Date'] = pd.to_datetime(df['Date'])
        latest_date = df['Date'].max()
        latest_data = df[df['Date'] == latest_date]
        
        # Calculate total portfolio value
        portfolio_value = 0.0
        cash_balance = 0.0
        
        for _, row in latest_data.iterrows():
            if pd.notna(row.get('Total Value')):
                portfolio_value += float(row['Total Value'])
            if pd.notna(row.get('Cash Balance')) and row.get('Cash Balance') != '':
                cash_balance = float(row['Cash Balance'])  # Use the last cash balance
        
        # If no cash balance in portfolio data, try to get it from cash balances file
        if cash_balance == 0.0:
            try:
                cash_file = Path(data_dir) / "cash_balances.json"
                if cash_file.exists():
                    import json
                    with open(cash_file, 'r') as f:
                        cash_data = json.load(f)
                        cash_balance = float(cash_data.get('CAD', 0.0))
            except Exception:
                pass
        
        # If still no cash balance, use fund contributions as a fallback
        if cash_balance == 0.0:
            total_contributions = calculate_fund_contributions_total(data_dir)
            # Assume some portion is in cash (simplified)
            cash_balance = max(0.0, total_contributions - portfolio_value)
        
        return portfolio_value + cash_balance
    
    except Exception as e:
        print(f"Error calculating current fund equity: {e}")
        return 0.0


def get_fund_value_per_share_at_time(data_dir: str, timestamp: str) -> float:
    """Get fund value per share at a specific timestamp."""
    try:
        # For now, implement a simplified approach that assumes $1 per share initially
        # In a production system, you'd track historical fund values and share counts
        
        # Load fund contributions to get total contributions up to that point
        df = load_fund_contributions(data_dir)
        if df.empty:
            return 1.0  # Default to $1 per share if no data
        
        # Convert timestamp to datetime for comparison
        target_time = pd.to_datetime(timestamp)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        
        # Get contributions up to the target time
        historical_contributions = df[df['Timestamp'] <= target_time]
        
        if historical_contributions.empty:
            return 1.0  # Default to $1 per share
        
        # Calculate total contributions up to that point
        total_contributions = 0.0
        for _, row in historical_contributions.iterrows():
            amount = row["Amount"]
            if row["Type"] == "WITHDRAWAL":
                amount = -amount
            total_contributions += amount
        
        if total_contributions <= 0:
            return 1.0
        
        # Simplified approach: assume fund starts at $1 per share
        # and grows proportionally with total contributions
        # This is a placeholder - in production you'd track actual fund performance
        
        # For now, use a simple linear growth model
        # Fund value per share = 1.0 + (contribution_sequence * growth_factor)
        contribution_sequence = len(historical_contributions)
        growth_factor = 0.1  # 10% growth per contribution (simplified)
        
        fund_value_per_share = 1.0 + (contribution_sequence * growth_factor)
        
        return max(fund_value_per_share, 0.01)  # Minimum $0.01 per share
    
    except Exception as e:
        print(f"Error calculating fund value per share: {e}")
        return 1.0


def calculate_liquidation_amount(data_dir: str, contributor: str, withdrawal_amount: float, current_equity: float) -> Dict[str, float]:
    """Calculate how much needs to be liquidated for a withdrawal."""
    ownership = calculate_ownership_percentages(data_dir)
    
    if contributor not in ownership:
        return {"error": f"Contributor {contributor} not found"}
    
    contributor_percentage = ownership[contributor] / 100
    contributor_equity = current_equity * contributor_percentage
    
    if withdrawal_amount > contributor_equity:
        return {
            "error": f"Withdrawal amount ${withdrawal_amount:,.2f} exceeds {contributor}'s equity of ${contributor_equity:,.2f}"
        }
    
    # Calculate what percentage of total portfolio needs to be liquidated
    liquidation_percentage = withdrawal_amount / current_equity
    
    return {
        "withdrawal_amount": withdrawal_amount,
        "contributor_equity": contributor_equity,
        "liquidation_percentage": liquidation_percentage * 100,
        "remaining_equity": contributor_equity - withdrawal_amount
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LLM Micro-Cap Trading Bot - Portfolio Management",
        epilog="By default, uses 'my trading' folder for private data storage."
    )
    parser.add_argument("--file", default=None, 
                       help="Path to portfolio CSV (default: my trading/llm_portfolio_update.csv)")
    parser.add_argument("--data-dir", default=None, 
                       help="Data directory (default: my trading)")
    parser.add_argument("--asof", default=None, 
                       help="Treat this YYYY-MM-DD as 'today' (e.g., 2025-08-27)")
    parser.add_argument("--force-fallback", action="store_true",
                       help="Force fallback mode (disable Rich, use colorama/plain text)")
    parser.add_argument("--colorama-only", action="store_true",
                       help="Force colorama-only mode (disable Rich but keep colorama)")
    args = parser.parse_args()

    if args.asof:
        set_asof(args.asof)
    
    # Handle force fallback options
    if args.force_fallback or args.colorama_only:
        set_force_fallback(force_fallback=True, colorama_only=args.colorama_only)

    # Use the new main function with better defaults
    main(args.file, Path(args.data_dir) if args.data_dir else None)
