#!/usr/bin/env python3
"""
Prompt Generator for LLM Micro-Cap Trading Bot
==============================================

This module handles all prompt generation for the trading bot, separated from
the core portfolio management functionality. It provides both daily trading
prompts and weekly deep research prompts.

Features:
- Daily trading prompt generation with live market data
- Weekly deep research prompt generation with portfolio context
- Market data fetching and formatting
- Portfolio data integration
- Flexible prompt templates

Design Philosophy:
- Optimized for both human readability and LLM context efficiency
- Colors enhance human scanning but are stripped during copy/paste
- Minimal separators save context space while maintaining structure
- Consistent column alignment makes data easy for LLMs to parse
- Comprehensive performance metrics (daily + total P&L) for better decisions
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Modular startup check - handles path setup and dependency checking
try:
    from utils.script_startup import startup_check
    startup_check("prompt_generator.py")
except ImportError:
    # Fallback for minimal dependency checking if script_startup isn't available
    import sys
    try:
        import pandas
    except ImportError:
        print("\n❌ Missing Dependencies (prompt_generator.py)")
        print("Required packages not found. Please activate virtual environment:")
        if os.name == 'nt':  # Windows
            print("  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print("  source venv/bin/activate")
        print("  python prompt_generator.py")
        print("\n💡 TIP: Use 'python run.py' and select option 'd' to avoid dependency issues")
        sys.exit(1)

import pandas as pd
import yaml

# Import from modular components
# Remove default data directory import - require explicit directory
from config.settings import get_settings
from data.repositories.repository_factory import get_repository_container
from portfolio.portfolio_manager import PortfolioManager
from market_data.market_hours import MarketHours
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache

# HOW TO ACCESS THIS SCRIPT:
# - User hits 'd' in main menu (run.py) -> runs: python prompt_generator.py --data-dir "my trading"
# - Generates daily trading prompt with portfolio data for LLM consumption
# - Uses PortfolioManager to load data and calculate_daily_pnl_from_snapshots for P&L

# Import color formatting
# Colors enhance human readability but are stripped during copy/paste, so they don't affect LLM context
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    _HAS_COLORAMA = True
except ImportError:
    _HAS_COLORAMA = False
    # Create dummy color classes if colorama not available
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = Back = Style = DummyColor()

# Import market configuration
try:
    from market_config import get_daily_instructions, get_market_info, get_benchmarks
    _HAS_MARKET_CONFIG = True
except ImportError:
    _HAS_MARKET_CONFIG = False

# Import dual currency support
try:
    from dual_currency import load_cash_balances, format_cash_display
    _HAS_DUAL_CURRENCY = True
except ImportError:
    _HAS_DUAL_CURRENCY = False

# Import experiment configuration
from utils.timeline_utils import get_experiment_timeline, format_timeline_display


class PromptGenerator:
    """Main class for generating trading prompts"""
    
    def __init__(self, data_dir: Path | str):
        """Initialize prompt generator with required data directory
        
        Args:
            data_dir: Required data directory path
        """
        if not data_dir:
            raise ValueError("Data directory is required - no default directory allowed")
        self.data_dir = Path(data_dir)
        
        # Initialize components
        self.settings = get_settings()
        self.market_hours = MarketHours(self.settings)
        self.price_cache = PriceCache()
        self.market_data_fetcher = MarketDataFetcher(cache_instance=self.price_cache)
        
        # Initialize repository and portfolio manager
        from data.repositories.csv_repository import CSVRepository
        self.repository = CSVRepository(self.data_dir)
        
        # Get fund information from data directory
        from portfolio.fund_manager import Fund, RepositorySettings
        from utils.fund_manager import get_fund_manager
        fund_manager = get_fund_manager()
        
        # Determine fund from data directory path
        fund_name = fund_manager.get_fund_by_data_directory(str(self.data_dir))
        if fund_name is None:
            # Fallback: create a default fund object
            repo_settings = RepositorySettings(type="csv", settings={})
            fund = Fund(
                id="unknown",
                name="Unknown",
                description="Unknown fund",
                repository=repo_settings
            )
        else:
            fund_config = fund_manager.get_fund_config(fund_name)
            if fund_config:
                repo_settings = RepositorySettings(
                    type=fund_config.get("repository", {}).get("type", "csv"),
                    settings=fund_config.get("repository", {}).get("csv", {})
                )
                fund = Fund(
                    id=fund_name,
                    name=fund_config.get("fund", {}).get("name", fund_name),
                    description=fund_config.get("fund", {}).get("description", ""),
                    repository=repo_settings
                )
            else:
                repo_settings = RepositorySettings(type="csv", settings={})
                fund = Fund(
                    id=fund_name,
                    name=fund_name,
                    description="Fund",
                    repository=repo_settings
                )
        
        self.portfolio_manager = PortfolioManager(self.repository, fund)
        
    def _get_market_data_table(self, portfolio_tickers: List[str]) -> List[List[str]]:
        """Fetch market data for portfolio tickers and benchmarks
        Returns rows with: [Ticker, Close, % Chg, Volume, Avg Vol (30d)]
        """
        rows: List[List[str]] = []
        
        # Get a longer historical window so we can compute average volume
        start_d, end_d = self.market_hours.trading_day_window()
        # Use configurable historical window instead of hardcoded 90 days
        historical_days = self.settings.get('market_data', {}).get('historical_window_days', 90)
        start_d = end_d - pd.Timedelta(days=historical_days)

        # Get benchmarks from market configuration
        benchmarks = []
        if _HAS_MARKET_CONFIG:
            try:
                benchmarks = get_benchmarks()
            except Exception as e:
                print(f"Debug: Could not get benchmarks from market_config: {e}")
                # Fallback to default benchmarks
                benchmarks = ["SPY", "QQQ", "VTI"]

        if not benchmarks:
            # Final fallback if market_config fails
            benchmarks = ["SPY", "QQQ", "VTI"]

        all_tickers = portfolio_tickers + benchmarks
        
        for ticker in all_tickers:
            try:
                result = self.market_data_fetcher.fetch_price_data(ticker, start_d, end_d)
                data = result.df
                
                if data.empty or len(data) < 2 or "Close" not in data.columns:
                    rows.append([ticker, "—", "—", "—", "—"])
                    continue
                
                price = float(data["Close"].iloc[-1])
                last_price = float(data["Close"].iloc[-2])
                
                # Last day volume
                if "Volume" in data.columns and len(data["Volume"]) > 0:
                    volume = float(data["Volume"].iloc[-1])
                else:
                    volume = float("nan")
                
                # Average volume calculation using configurable period
                avg_vol_cell = "—"
                if "Volume" in data.columns:
                    vol_series = data["Volume"].dropna()
                    if not vol_series.empty:
                        # Use configurable period instead of hardcoded 30 days
                        avg_period_days = self.settings.get('market_data', {}).get('average_volume_period_days', 30)
                        avg_volume = vol_series.tail(avg_period_days).mean()
                        if pd.notna(avg_volume):
                            # Use configurable threshold for formatting
                            volume_threshold = self.settings.get('market_data', {}).get('volume_format_threshold', 1000)
                            if avg_volume >= volume_threshold:
                                avg_vol_cell = f"{int(avg_volume/volume_threshold):,}K"
                            else:
                                avg_vol_cell = f"{int(avg_volume):,}"
                
                percent_change = ((price - last_price) / last_price) * 100
                # Format current volume using configurable threshold
                if pd.notna(volume):
                    # Use configurable threshold for formatting
                    volume_threshold = self.settings.get('market_data', {}).get('volume_format_threshold', 1000)
                    if volume >= volume_threshold:
                        volume_cell = f"{int(volume/volume_threshold):,}K"
                    else:
                        volume_cell = f"{int(volume):,}"
                else:
                    volume_cell = "—"
                rows.append([ticker, f"{price:,.2f}", f"{percent_change:+.2f}%", volume_cell, avg_vol_cell])
                
            except Exception as e:
                print(f"Warning: Failed to fetch data for {ticker}: {e}")
                rows.append([ticker, "—", "—", "—", "—"])
                
        return rows
        
    def _format_cash_info(self, cash: float) -> tuple[str, float]:
        """Format cash balance information"""
        if _HAS_MARKET_CONFIG and _HAS_DUAL_CURRENCY:
            try:
                cash_balances = load_cash_balances(self.data_dir)
                cash_display = format_cash_display(cash_balances)
                total_equity = cash_balances.total_cad_equivalent()
                return cash_display, total_equity
            except Exception:
                return f"${cash:,.2f}", cash
        else:
            return f"${cash:,.2f}", cash
    
    def _calculate_financial_overview_data(self, latest_snapshot) -> dict:
        """Calculate comprehensive financial overview data for prompts"""
        try:
            # Import required modules
            from decimal import Decimal
            import pandas as pd
            
            # Get portfolio statistics using the same method as main trading script
            # We need to use the position calculator, not the portfolio manager
            from portfolio.position_calculator import PositionCalculator
            position_calculator = PositionCalculator(self.repository)
            stats_data = position_calculator.calculate_portfolio_metrics(latest_snapshot)
            
            # Load fund contributions data (same as main trading script)
            fund_contributions = []
            try:
                fund_file = self.data_dir / "fund_contributions.csv"
                if fund_file.exists():
                    df = pd.read_csv(fund_file)
                    fund_contributions = df.to_dict('records')
            except Exception as e:
                pass  # Fund contributions not available
            
            # Calculate total contributions from fund data (same as main trading script)
            total_contributions = Decimal('0')
            if fund_contributions:
                for contribution in fund_contributions:
                    raw_amount = contribution.get('Amount', contribution.get('amount', 0))
                    try:
                        amount = Decimal(str(raw_amount))
                    except Exception:
                        amount = Decimal('0')
                    contrib_type = contribution.get('Type', contribution.get('type', 'CONTRIBUTION'))
                    ctype = str(contrib_type).upper()
                    if ctype in ('CONTRIBUTION', 'ADJUSTMENT'):
                        total_contributions += amount
                    elif ctype in ('WITHDRAWAL', 'FEE', 'FX_FEE', 'MAINTENANCE_FEE', 'BANK_FEE'):
                        total_contributions -= amount
            
            # Get realized P&L from FIFO processor (same as main trading script)
            from portfolio.fifo_trade_processor import FIFOTradeProcessor
            trade_processor = FIFOTradeProcessor(self.repository)
            realized_summary = trade_processor.get_realized_pnl_summary()
            total_realized_pnl = realized_summary.get('total_realized_pnl', Decimal('0'))
            
            # Get portfolio metrics from position calculator
            total_portfolio_value = stats_data.get('total_market_value', Decimal('0'))
            cost_basis = stats_data.get('total_cost_basis', Decimal('0'))
            unrealized_pnl = stats_data.get('total_unrealized_pnl', Decimal('0'))
            
            # Load cash balance
            cash_balance = Decimal('0')
            cad_cash = None
            usd_cash = None
            usd_to_cad_rate = None
            estimated_fx_fee_total_usd = None
            estimated_fx_fee_total_cad = None
            
            try:
                import json
                cash_file = self.data_dir / "cash_balances.json"
                if cash_file.exists():
                    with open(cash_file, 'r') as f:
                        cash_data = json.load(f)
                        cad_cash = Decimal(str(cash_data.get('cad', 0)))
                        usd_cash = Decimal(str(cash_data.get('usd', 0)))
                        cash_balance = cad_cash + usd_cash
                        
                        # Get exchange rate and calculate FX fees
                        if _HAS_DUAL_CURRENCY:
                            try:
                                from dual_currency import load_cash_balances
                                _, _, usd_to_cad_rate = load_cash_balances(self.data_dir)
                                if usd_cash and usd_to_cad_rate:
                                    # Calculate estimated FX fee (1.5% on USD holdings)
                                    estimated_fx_fee_total_usd = usd_cash * Decimal('0.015')
                                    estimated_fx_fee_total_cad = estimated_fx_fee_total_usd * usd_to_cad_rate
                            except Exception:
                                pass
            except Exception as e:
                pass  # Cash balances not available
            
            # Calculate currency breakdown
            usd_positions_value = Decimal('0')
            cad_positions_value = Decimal('0')
            for position in latest_snapshot.positions:
                if hasattr(position, 'currency') and position.currency == 'USD':
                    usd_positions_value += position.market_value or Decimal('0')
                else:
                    cad_positions_value += position.market_value or Decimal('0')
            
            # Calculate total equity
            total_equity = total_portfolio_value + cash_balance
            
            # Calculate total portfolio P&L (unrealized + realized)
            total_portfolio_pnl = unrealized_pnl + total_realized_pnl
            
            # Calculate overall return
            overall_return_pct = Decimal('0')
            if total_contributions > 0:
                net_pnl_vs_contrib = total_equity - total_contributions
                overall_return_pct = (net_pnl_vs_contrib / total_contributions) * 100
            
            # Calculate unallocated vs cost (audit metric)
            unallocated_vs_cost = total_contributions - cost_basis - cash_balance
            
            return {
                'total_portfolio_value': float(total_portfolio_value),
                'cash_balance': float(cash_balance),
                'cad_cash': float(cad_cash) if cad_cash is not None else None,
                'usd_cash': float(usd_cash) if usd_cash is not None else None,
                'usd_to_cad_rate': float(usd_to_cad_rate) if usd_to_cad_rate is not None else None,
                'estimated_fx_fee_total_usd': float(estimated_fx_fee_total_usd) if estimated_fx_fee_total_usd is not None else None,
                'estimated_fx_fee_total_cad': float(estimated_fx_fee_total_cad) if estimated_fx_fee_total_cad is not None else None,
                'usd_positions_value': float(usd_positions_value),
                'cad_positions_value': float(cad_positions_value),
                'total_equity': float(total_equity),
                'total_contributions': float(total_contributions),
                'cost_basis': float(cost_basis),
                'unrealized_pnl': float(unrealized_pnl),
                'realized_pnl': float(total_realized_pnl),
                'total_portfolio_pnl': float(total_portfolio_pnl),
                'overall_return_pct': float(overall_return_pct),
                'unallocated_vs_cost': float(unallocated_vs_cost)
            }
        except Exception as e:
            # Return minimal data if calculation fails
            return {
                'total_portfolio_value': 0,
                'cash_balance': 0,
                'cad_cash': None,
                'usd_cash': None,
                'usd_to_cad_rate': None,
                'estimated_fx_fee_total_usd': None,
                'estimated_fx_fee_total_cad': None,
                'usd_positions_value': 0,
                'cad_positions_value': 0,
                'total_equity': 0,
                'total_contributions': 0,
                'cost_basis': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0,
                'total_portfolio_pnl': 0,
                'overall_return_pct': 0,
                'unallocated_vs_cost': 0
            }
    
    def _format_portfolio_table(self, portfolio_df: pd.DataFrame, sort_by: str = "date") -> str:
        """Format portfolio data with enhanced date range and P&L information

        Design decisions:
        - Colors enhance human readability but are stripped during copy/paste
        - Consistent column alignment makes data easy for LLMs to parse
        - Shows both daily and total P&L for comprehensive performance context
        - Position open dates provide historical context
        - Minimal separators save context space while maintaining structure
        - Added dollar P&L and total value columns
        - Sorting by date or total value

        Args:
            portfolio_df: Portfolio data as DataFrame
            sort_by: Sort method - "date" or "value"
        """
        if portfolio_df.empty:
            return "No current holdings"

        # Load trade log to get position open dates
        trade_log_df = None
        try:
            trades = self.repository.get_all_trades()
            if trades:
                trade_data = []
                for trade in trades:
                    trade_data.append({
                        'Ticker': trade.ticker,
                        'Date': trade.timestamp,
                        'Action': trade.action
                    })
                trade_log_df = pd.DataFrame(trade_data)
        except Exception:
            trade_log_df = None

        # Get current date for context
        current_date = self.market_hours.last_trading_date().strftime("%Y-%m-%d")
        s, e = self.market_hours.trading_day_window()

        # Create enhanced portfolio display with colors
        # Color scheme: Cyan=tickers, Yellow=headers/prices, Blue=dates, Green/Red=P&L
        lines = []
        # Header row only (section title printed above)
        lines.append(f"{Fore.YELLOW}{'Ticker':<10} {'Company':<25} {'Opened':<8} {'Shares':>8} {'Avg Price':>10} {'Current':>10} {'Total Value':>11} {'% Port':>9} {'Total P&L':>16} {'Daily P&L':>16}{Style.RESET_ALL}")
        # Compute separator length dynamically
        _col_widths = [10, 25, 8, 8, 10, 10, 11, 9, 16, 16]
        _sep_len = sum(_col_widths) + (len(_col_widths) - 1)
        lines.append("-" * _sep_len)
        
        # Prepare data for sorting
        portfolio_rows = []
        for _, row in portfolio_df.iterrows():
            ticker = str(row.get('ticker', ''))
            # Use company name from enhanced data (correct field name)
            company_name = row.get('company', ticker) or ticker
            # Truncate long company names
            display_name = company_name[:22] + "..." if len(company_name) > 25 else company_name

            # Use open date from enhanced data and ensure mm-dd-yy format
            open_date = row.get('opened_date', 'N/A')
            if open_date != 'N/A':
                # Ensure mm-dd-yy format
                try:
                    from datetime import datetime
                    if len(open_date) == 5:  # mm/dd format
                        # Convert mm/dd to mm-dd-yy
                        date_obj = datetime.strptime(open_date + f"/{datetime.now().year}", '%m/%d/%Y')
                        open_date = date_obj.strftime('%m-%d-%y')
                    elif '/' in open_date:
                        # Convert mm/dd/yy to mm-dd-yy
                        parts = open_date.split('/')
                        if len(parts) == 3:
                            open_date = f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{parts[2]}"
                    # If already in correct format, keep as is
                except:
                    pass

            # Get current price and calculate values
            try:
                result = self.market_data_fetcher.fetch_price_data(ticker, s, e)
                if not result.df.empty and "Close" in result.df.columns:
                    current_price = float(result.df['Close'].iloc[-1])
                else:
                    current_price = 0.0
            except:
                current_price = 0.0

            shares = float(row.get('shares', 0))
            buy_price = float(row.get('avg_price', 0))

            # Calculate total value (shares * current price)
            total_value = shares * current_price if current_price > 0 else 0.0

            # Calculate dollar P&L (unrealized_pnl from enhanced data)
            dollar_pnl = row.get('unrealized_pnl', 0)
            if dollar_pnl == 0 and buy_price > 0 and current_price > 0:
                # Fallback calculation: (current - buy) * shares
                dollar_pnl = (current_price - buy_price) * shares

            portfolio_rows.append({
                'row': row,
                'ticker': ticker,
                'display_name': display_name,
                'open_date': open_date,
                'shares': shares,
                'buy_price': buy_price,
                'current_price': current_price,
                'total_value': total_value,
                'dollar_pnl': dollar_pnl,
                'sort_key': open_date if sort_by == "date" else total_value
            })

        # Sort the rows
        if sort_by == "date":
            portfolio_rows.sort(key=lambda x: x['sort_key'] if x['sort_key'] != 'N/A' else '99-99-99')
        else:  # sort by value
            portfolio_rows.sort(key=lambda x: x['sort_key'], reverse=True)

        # Compute total for percentage-of-portfolio column
        grand_total_value = sum(item.get('total_value', 0.0) for item in portfolio_rows) or 0.0

        # Process sorted rows
        for item in portfolio_rows:
            row = item['row']
            ticker = item['ticker']
            display_name = item['display_name']
            open_date = item['open_date']
            shares = item['shares']
            buy_price = item['buy_price']
            current_price = item['current_price']
            total_value = item['total_value']
            dollar_pnl = item['dollar_pnl']
            
            # Calculate P&L values
            if current_price > 0:
                # Calculate total P&L percentage from unrealized_pnl and cost_basis
                pnl_amount = row.get('unrealized_pnl', 0) or 0
                cost_basis = row.get('cost_basis', 0) or 0
                
                if cost_basis > 0:
                    total_pnl_pct = (pnl_amount / cost_basis) * 100
                    total_pnl_pct_str = f"{total_pnl_pct:+.1f}%"
                elif buy_price > 0:
                    # Fallback calculation using current vs buy price
                    total_pnl_pct = ((current_price - buy_price) / buy_price) * 100
                    total_pnl_pct_str = f"{total_pnl_pct:+.1f}%"
                else:
                    total_pnl_pct_str = "N/A"

                # Use daily P&L from enhanced data if available
                daily_pnl_pct_str = row.get('daily_pnl', 'N/A')
                if daily_pnl_pct_str == 'N/A':
                    try:
                        result = self.market_data_fetcher.fetch_price_data(ticker, s, e)
                        if not result.df.empty and len(result.df) > 1:
                            prev_price = float(result.df['Close'].iloc[-2])
                            daily_pnl_pct = ((current_price - prev_price) / prev_price) * 100
                            daily_pnl_pct_str = f"{daily_pnl_pct:+.1f}%"
                        else:
                            daily_pnl_pct_str = "N/A"
                    except:
                        daily_pnl_pct_str = "N/A"

                # Combine P&L values with dollar amounts
                dollar_pnl_str = f"${dollar_pnl:+,.2f}" if dollar_pnl != 0 else "$0.00"
                total_pnl = f"{total_pnl_pct_str} {dollar_pnl_str}"
                
                # Use daily P&L from the row data (already calculated in trading script)
                daily_pnl_dollar = row.get('daily_pnl', 'N/A')
                
                # Calculate proper daily P&L percentage for better color coding
                daily_pnl_value = 0.0
                if daily_pnl_dollar != 'N/A' and daily_pnl_dollar != '$0.00':
                    # Extract dollar value from daily_pnl_dollar for percentage calculation
                    try:
                        # Remove $ and , and * characters, then convert to float
                        daily_pnl_value = float(daily_pnl_dollar.replace('$', '').replace(',', '').replace('*', ''))
                        # Calculate percentage based on current position value
                        if total_value > 0:
                            daily_pnl_pct = (daily_pnl_value / total_value) * 100
                            daily_pnl_pct_str = f"{daily_pnl_pct:+.1f}%"
                        else:
                            daily_pnl_pct_str = "0.0%"
                        daily_pnl = f"{daily_pnl_pct_str} {daily_pnl_dollar}"
                    except (ValueError, AttributeError):
                        daily_pnl = f"{daily_pnl_pct_str} {daily_pnl_dollar}"
                else:
                    daily_pnl = f"0.0% $0.00"
                    daily_pnl_value = 0.0

                current_price_str = f"${current_price:.2f}"
                buy_price_str = f"${buy_price:.2f}"
                total_value_str = f"${total_value:.2f}"
            else:
                current_price_str = "N/A"
                buy_price_str = f"${buy_price:.2f}" if buy_price > 0 else "N/A"
                total_value_str = "N/A"
                total_pnl = "N/A"
                daily_pnl = "N/A"
            
            # Color code P&L values - Green for positive, Red for negative
            # This makes performance immediately visible to humans while preserving data for LLMs
            total_pnl_colored = total_pnl
            daily_pnl_colored = daily_pnl

            # Color based on the percentage part (first character)
            if total_pnl != "N/A" and total_pnl.startswith(('+', '-')):
                total_pnl_colored = f"{Fore.GREEN if total_pnl.startswith('+') else Fore.RED}{total_pnl}{Style.RESET_ALL}"
            if daily_pnl != "N/A" and daily_pnl.startswith(('+', '-')):
                daily_pnl_colored = f"{Fore.GREEN if daily_pnl.startswith('+') else Fore.RED}{daily_pnl}{Style.RESET_ALL}"

            # Format each row with consistent colors and alignment
            # Colors help humans scan data quickly, alignment helps LLMs parse structure
            # Build padded cells first to enforce alignment, then colorize
            ticker_cell = f"{ticker:<10}"
            company_cell = f"{display_name:<25}"
            opened_cell = f"{open_date:<8}"
            shares_cell = f"{shares:>8.1f}"
            buy_price_cell = f"{buy_price_str:>10}"
            current_price_cell = f"{current_price_str:>10}"
            total_value_cell = f"{total_value_str:>11}"
            # Percent of portfolio cell
            if grand_total_value > 0:
                pct_of_port = (total_value / grand_total_value) * 100
                pct_of_port_str = f"{pct_of_port:.1f}%"
            else:
                pct_of_port_str = "0.0%"
            pct_port_cell = f"{pct_of_port_str:>9}"

            total_pnl_cell = f"{total_pnl:>16}"
            daily_pnl_cell = f"{daily_pnl:>16}"

            # Colorize padded P&L cells so ANSI codes don't affect alignment
            total_pnl_cell_colored = total_pnl_cell
            if total_pnl != "N/A" and total_pnl.startswith(("+", "-")):
                total_pnl_cell_colored = f"{Fore.GREEN if total_pnl.startswith('+') else Fore.RED}{total_pnl_cell}{Style.RESET_ALL}"

            # Improved daily P&L coloring based on numeric value, not string prefix
            daily_pnl_cell_colored = daily_pnl_cell
            if daily_pnl != "N/A":
                if daily_pnl_value > 0:
                    daily_pnl_cell_colored = f"{Fore.GREEN}{daily_pnl_cell}{Style.RESET_ALL}"
                elif daily_pnl_value < 0:
                    daily_pnl_cell_colored = f"{Fore.RED}{daily_pnl_cell}{Style.RESET_ALL}"
            
            # Color current price based on comparison with buy price
            current_price_cell_colored = current_price_cell
            if current_price_str != "N/A" and buy_price > 0:
                if current_price > buy_price:
                    current_price_cell_colored = f"{Fore.GREEN}{current_price_cell}{Style.RESET_ALL}"
                elif current_price < buy_price:
                    current_price_cell_colored = f"{Fore.RED}{current_price_cell}{Style.RESET_ALL}"
                else:
                    current_price_cell_colored = f"{Fore.YELLOW}{current_price_cell}{Style.RESET_ALL}"

            # Apply colors to other columns - color ticker by currency
            # Blue for USD, Cyan for CAD (consistent with other parts of system)
            currency = row.get('currency', 'CAD')  # Default to CAD if not specified
            ticker_color = Fore.BLUE if currency == 'USD' else Fore.CYAN
            
            line = (
                f"{ticker_color}{ticker_cell}{Style.RESET_ALL} "
                f"{company_cell} "
                f"{Fore.BLUE}{opened_cell}{Style.RESET_ALL} "
                f"{shares_cell} "
                f"{Fore.BLUE}{buy_price_cell}{Style.RESET_ALL} "
                f"{current_price_cell_colored} "
                f"{Fore.YELLOW}{total_value_cell}{Style.RESET_ALL} "
                f"{Fore.YELLOW}{pct_port_cell}{Style.RESET_ALL} "
                f"{total_pnl_cell_colored} "
                f"{daily_pnl_cell_colored}"
            )
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_fundamentals_table(self, portfolio_tickers: List[str], portfolio_df: pd.DataFrame = None) -> str:
        """Format fundamentals data table for portfolio tickers
        
        Returns formatted table with sector, industry, country, market cap, P/E, dividend yield
        """
        if not portfolio_tickers:
            return "No holdings to display fundamentals"
        
        # Cache currency lookup for performance - build once, use for all tickers
        currency_lookup = {}
        if portfolio_df is not None and not portfolio_df.empty:
            for _, row in portfolio_df.iterrows():
                ticker = row.get('ticker')
                currency = row.get('currency', 'USD')
                if ticker:
                    currency_lookup[ticker] = currency
            
        lines = []
        # Header row only (section title printed above)
        lines.append(f"{Fore.YELLOW}{'Ticker':<10} {'Sector':<20} {'Industry':<25} {'Country':<8} {'Mkt Cap':<12} {'P/E':<6} {'Div %':<6} {'52W High':<10} {'52W Low':<10}{Style.RESET_ALL}")
        
        # Calculate separator length
        col_widths = [10, 20, 25, 8, 12, 6, 6, 10, 10]
        sep_len = sum(col_widths) + (len(col_widths) - 1)
        lines.append("-" * sep_len)
        
        for ticker in portfolio_tickers:
            try:
                
                fundamentals = self.market_data_fetcher.fetch_fundamentals(ticker)
                
                # Check if this is an ETF to provide better labeling
                is_etf = fundamentals.get('marketCap') == 'ETF'
                
                # Format each field with proper truncation/padding and ETF-aware labels
                ticker_cell = f"{ticker:<10}"
                
                # For ETFs, show more meaningful labels instead of N/A
                sector_val = fundamentals.get('sector', 'N/A')
                if is_etf and sector_val == 'N/A':
                    sector_val = 'ETF'
                sector_cell = f"{str(sector_val)[:19]:<20}"
                
                industry_val = fundamentals.get('industry', 'N/A')
                if is_etf and industry_val == 'N/A':
                    industry_val = 'ETF'
                industry_cell = f"{str(industry_val)[:24]:<25}"
                
                country_val = str(fundamentals.get('country', 'N/A'))
                # Truncate long country names to fit 8-character column
                country_cell = f"{country_val[:7]:<8}"
                market_cap_cell = f"{str(fundamentals.get('marketCap', 'N/A')):<12}"
                pe_cell = f"{str(fundamentals.get('trailingPE', 'N/A')):<6}"
                div_cell = f"{str(fundamentals.get('dividendYield', 'N/A')):<6}"
                high_52w_cell = f"{str(fundamentals.get('fiftyTwoWeekHigh', 'N/A')):<10}"
                low_52w_cell = f"{str(fundamentals.get('fiftyTwoWeekLow', 'N/A')):<10}"
                
                # Determine ticker color based on currency (consistent with portfolio table)
                # Use cached currency lookup for performance
                currency = currency_lookup.get(ticker, 'USD')  # Default to USD if not found
                ticker_color = Fore.BLUE if currency == 'USD' else Fore.CYAN
                
                # Build colored line
                line = (
                    f"{ticker_color}{ticker_cell}{Style.RESET_ALL} "
                    f"{sector_cell} "
                    f"{industry_cell} "
                    f"{Fore.BLUE}{country_cell}{Style.RESET_ALL} "
                    f"{Fore.YELLOW}{market_cap_cell}{Style.RESET_ALL} "
                    f"{pe_cell} "
                    f"{div_cell} "
                    f"{Fore.GREEN}{high_52w_cell}{Style.RESET_ALL} "
                    f"{Fore.RED}{low_52w_cell}{Style.RESET_ALL}"
                )
                lines.append(line)
                
            except Exception as e:
                # Fallback row for failed fetches
                ticker_cell = f"{ticker:<10}"
                error_row = (
                    f"{Fore.CYAN}{ticker_cell}{Style.RESET_ALL} "
                    f"{'N/A':<20} {'N/A':<25} {'N/A':<8} {'N/A':<12} {'N/A':<6} {'N/A':<6} {'N/A':<10} {'N/A':<10}"
                )
                lines.append(error_row)
                
        return "\n".join(lines)
            
    def generate_daily_prompt(self, data_dir: Path | str | None = None) -> None:
        """Generate and display daily trading prompt with live data"""
        if data_dir:
            self.data_dir = Path(data_dir)
            # Reinitialize repository with new data dir
            from data.repositories.csv_repository import CSVRepository
            self.repository = CSVRepository(self.data_dir)
            self.portfolio_manager = PortfolioManager(self.repository)
            
        # Load portfolio data
        print("Loading portfolio data...")
        try:
            latest_snapshot = self.portfolio_manager.get_latest_portfolio()
            if latest_snapshot is None:
                print(f"❌ No portfolio data found in {self.data_dir}")
                print("Please run the main trading script first to create portfolio data.")
                return
            print(f"✅ Loaded portfolio with {len(latest_snapshot.positions)} positions")
            
            # Convert to DataFrame with enhanced data (same as main trading script)
            portfolio_data = []
            total_portfolio_value = sum(pos.market_value or 0 for pos in latest_snapshot.positions)
            
            for position in latest_snapshot.positions:
                # Use the same to_dict() method as main trading script
                pos_dict = position.to_dict()
                
                # Get open date from trade log (same logic as main script)
                try:
                    trades = self.repository.get_trade_history(position.ticker)
                    if trades:
                        # Find first BUY trade for this ticker
                        buy_trades = [t for t in trades if t.action.upper() == 'BUY']
                        if buy_trades:
                            first_buy = min(buy_trades, key=lambda t: t.timestamp)
                            pos_dict['opened_date'] = first_buy.timestamp.strftime('%m-%d-%y')
                        else:
                            pos_dict['opened_date'] = "N/A"
                    else:
                        pos_dict['opened_date'] = "N/A"
                except Exception:
                    pos_dict['opened_date'] = "N/A"
                
                # Calculate daily P&L using shared function
                from financial.pnl_calculator import calculate_daily_pnl_from_snapshots
                snapshots = self.portfolio_manager.load_portfolio()
                pos_dict['daily_pnl'] = calculate_daily_pnl_from_snapshots(position, snapshots)
                
                portfolio_data.append(pos_dict)
            
            llm_portfolio = pd.DataFrame(portfolio_data)
            
            # Load cash balance
            cash = 0.0
            try:
                import json
                cash_file = self.data_dir / "cash_balances.json"
                if cash_file.exists():
                    with open(cash_file, 'r') as f:
                        cash_data = json.load(f)
                        cash = cash_data.get('cad', 0) + cash_data.get('usd', 0)
            except Exception:
                cash = 0.0
                
        except Exception as e:
            print(f"❌ Error loading portfolio data: {e}")
            return
            
        # Get portfolio tickers
        portfolio_tickers = []
        if not llm_portfolio.empty and 'ticker' in llm_portfolio.columns:
            portfolio_tickers = llm_portfolio['ticker'].tolist()

        # Fetch market data
        print("Fetching current market data...")
        market_rows = self._get_market_data_table(portfolio_tickers)
        print(f"✅ Updated market data for {len(market_rows)} tickers")

        # Calculate comprehensive financial overview data
        print("Calculating portfolio metrics...")
        financial_data = self._calculate_financial_overview_data(latest_snapshot)
        print("✅ Portfolio metrics calculated successfully")
        
        # Format cash information
        cash_display, total_equity = self._format_cash_info(cash)
        
        # Get current date
        today = self.market_hours.last_trading_date_str()
        
        # Calculate experiment timeline
        timeline_text = format_timeline_display(self.data_dir)
        
        # Generate the prompt with optimized formatting for both humans and LLMs
        # Design: Clean headers, colored data, minimal separators to save context space
        print(f"\n[PROMPT] Daily Results — {today} ({timeline_text})")
        print("Copy everything below and paste into your LLM:")
        
        # 1. Load the appropriate daily prompt template based on fund type
        template_path = self._get_daily_template_path()
        try:
            with open(template_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"❌ Error: {template_path} not found.")
            return

        # 2. Get fund name from settings or active fund
        fund_name = self._get_fund_name()

        # 3. Format all portfolio data into a single string
        portfolio_data_parts = []

        # Market data table
        portfolio_data_parts.append(f"{Fore.CYAN}[ Price & Volume ]{Style.RESET_ALL}")
        header = ["Ticker", "Close", "% Chg", "Volume", "Avg Vol (30d)"]
        colw = [10, 12, 9, 12, 14]
        portfolio_data_parts.append(f"{Fore.YELLOW}{header[0]:<{colw[0]}} {header[1]:>{colw[1]}} {header[2]:>{colw[2]}} {header[3]:>{colw[3]}} {header[4]:>{colw[4]}}{Style.RESET_ALL}")
        sep_len = sum(colw) + (len(colw) - 1)
        portfolio_data_parts.append("-" * sep_len)
        for row in market_rows:
            ticker_cell = f"{str(row[0]):<{colw[0]}}"
            close_cell_plain = str(row[1]).rjust(colw[1])
            pct_change = str(row[2])
            pct_cell_plain = pct_change.rjust(colw[2])
            volume_cell_plain = str(row[3]).rjust(colw[3])
            avg_vol_cell_plain = str(row[4]).rjust(colw[4])

            close_cell = f"{Fore.YELLOW}{close_cell_plain}{Style.RESET_ALL}"
            if pct_change != "—" and pct_change.startswith(('+', '-')):
                pct_cell = f"{Fore.GREEN if pct_change.startswith('+') else Fore.RED}{pct_cell_plain}{Style.RESET_ALL}"
            else:
                pct_cell = pct_cell_plain
            volume_cell = f"{Fore.BLUE}{volume_cell_plain}{Style.RESET_ALL}"
            avg_volume_cell = f"{Fore.BLUE}{avg_vol_cell_plain}{Style.RESET_ALL}"
            portfolio_data_parts.append(f"{Fore.CYAN}{ticker_cell}{Style.RESET_ALL} {close_cell} {pct_cell} {volume_cell} {avg_volume_cell}")
            
        # Portfolio snapshot
        portfolio_data_parts.append(f"\n{Fore.CYAN}[ Portfolio Snapshot ]{Style.RESET_ALL}")
        portfolio_data_parts.append(self._format_portfolio_table(llm_portfolio, sort_by="date"))
        
        # Company fundamentals
        portfolio_data_parts.append(f"\n{Fore.CYAN}[ Company Fundamentals ]{Style.RESET_ALL}")
        portfolio_data_parts.append(self._format_fundamentals_table(portfolio_tickers, llm_portfolio))
            
        # Financial summary
        portfolio_data_parts.append(f"\n{Fore.CYAN}[ Fund Performance Summary ]{Style.RESET_ALL}")
        portfolio_data_parts.append(f"{Fore.GREEN}Portfolio Value:{Style.RESET_ALL} ${financial_data['total_portfolio_value']:,.2f}")
        portfolio_data_parts.append(f"{Fore.GREEN}Cash Balances:{Style.RESET_ALL} {cash_display}")
        portfolio_data_parts.append(f"{Fore.GREEN}Total Equity:{Style.RESET_ALL} ${financial_data['total_equity']:,.2f}")
        
        portfolio_data_string = "\n".join(portfolio_data_parts)

        # 4. Substitute placeholders in the template
        final_prompt = prompt_template.replace("{insert portfolio data}", portfolio_data_string)
        final_prompt = final_prompt.replace("{fund_name}", fund_name)

        print(final_prompt)

        print(f"\n[END] End of prompt - copy everything above to your LLM")
        
    def generate_weekly_research_prompt(self, data_dir: Path | str | None = None) -> None:
        """Generate and display weekly deep research prompt"""
        if data_dir:
            self.data_dir = Path(data_dir)
            # Reinitialize repository with new data dir
            from data.repositories.csv_repository import CSVRepository
            self.repository = CSVRepository(self.data_dir)
            self.portfolio_manager = PortfolioManager(self.repository)
            
        try:
            # Load portfolio data using the same approach as daily prompt
            print("Loading portfolio data...")
            latest_snapshot = self.portfolio_manager.get_latest_portfolio()
            if latest_snapshot is None:
                print(f"❌ No portfolio data found in {self.data_dir}")
                print("Please run the main trading script first to create portfolio data.")
                return
            print(f"✅ Loaded portfolio with {len(latest_snapshot.positions)} positions")
            
            # Convert to DataFrame with enhanced data (same as daily prompt)
            portfolio_data = []
            for position in latest_snapshot.positions:
                # Use the same to_dict() method as main trading script
                pos_dict = position.to_dict()
                
                # Get open date from trade log (same logic as daily prompt)
                try:
                    trades = self.repository.get_trade_history(position.ticker)
                    if trades:
                        # Find first BUY trade for this ticker
                        buy_trades = [t for t in trades if t.action.upper() == 'BUY']
                        if buy_trades:
                            first_buy = min(buy_trades, key=lambda t: t.timestamp)
                            pos_dict['opened_date'] = first_buy.timestamp.strftime('%m-%d-%y')
                        else:
                            pos_dict['opened_date'] = "N/A"
                    else:
                        pos_dict['opened_date'] = "N/A"
                except Exception:
                    pos_dict['opened_date'] = "N/A"
                
                # Calculate daily P&L using shared function
                from financial.pnl_calculator import calculate_daily_pnl_from_snapshots
                snapshots = self.portfolio_manager.load_portfolio()
                pos_dict['daily_pnl'] = calculate_daily_pnl_from_snapshots(position, snapshots)
                
                portfolio_data.append(pos_dict)
            
            llm_portfolio = pd.DataFrame(portfolio_data)
            
            # Load cash balance (same approach as daily prompt)
            cash = 0.0
            try:
                import json
                cash_file = self.data_dir / "cash_balances.json"
                if cash_file.exists():
                    with open(cash_file, 'r') as f:
                        cash_data = json.load(f)
                        cash = cash_data.get('cad', 0) + cash_data.get('usd', 0)
            except Exception:
                cash = 0.0
        except Exception as e:
            print(f"❌ Error loading portfolio data: {e}")
            return
            
        # Get portfolio tickers for additional data tables
        portfolio_tickers = []
        if not llm_portfolio.empty and 'ticker' in llm_portfolio.columns:
            portfolio_tickers = llm_portfolio['ticker'].tolist()

        # Fetch market data (same as daily prompt)
        print("Fetching current market data...")
        market_rows = self._get_market_data_table(portfolio_tickers)
        print(f"✅ Updated market data for {len(market_rows)} tickers")

        # Calculate comprehensive financial overview data
        print("Calculating portfolio metrics...")
        financial_data = self._calculate_financial_overview_data(latest_snapshot)
        print("✅ Portfolio metrics calculated successfully")
        
        # Format cash information
        cash_display, total_equity = self._format_cash_info(cash)
        
        # Calculate experiment timeline using proper configuration
        timeline_text = format_timeline_display(self.data_dir)
        
        # Generate the deep research prompt with same color scheme as daily prompt
        # Weekly prompts need more comprehensive analysis, so colors help organize complex data
        print(f"\n🔬 Weekly Deep Research - {timeline_text}")
        print("Copy everything below and paste into your LLM for deep research:")
        
        # 1. Load the appropriate prompt template based on fund type
        template_path = self._get_weekly_template_path()
        try:
            with open(template_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"❌ Error: {template_path} not found.")
            return

        # 2. Get fund name from settings or active fund
        fund_name = self._get_fund_name()

        # 3. Load and format the thesis from YAML
        thesis_path = self._get_thesis_path()
        try:
            with open(thesis_path, "r") as f:
                thesis_data = yaml.safe_load(f)
            
            # Replace placeholder in thesis title and overview
            thesis_title = thesis_data['guiding_thesis']['title'].replace('{fund_name}', fund_name)
            thesis_overview = thesis_data['guiding_thesis']['overview'].replace('{fund_name}', fund_name)
            
            thesis_text = f"{thesis_title}\n{thesis_overview}\n\n"
            for pillar in thesis_data['guiding_thesis']['pillars']:
                thesis_text += f"{pillar['name']} ({pillar['allocation']})\n"
                thesis_text += f"Thesis: {pillar['thesis']}\n\n"
        except FileNotFoundError:
            thesis_text = f"ERROR: {thesis_path} not found."
        except Exception as e:
            thesis_text = f"ERROR: Could not parse {thesis_path}: {e}"

        # 4. Format the portfolio data
        portfolio_tables = []
        portfolio_tables.append(f"{Fore.CYAN}[ Price & Volume ]{Style.RESET_ALL}")
        header = ["Ticker", "Close", "% Chg", "Volume", "Avg Vol (30d)"]
        colw = [10, 12, 9, 12, 14]
        portfolio_tables.append(f"{Fore.YELLOW}{header[0]:<{colw[0]}} {header[1]:>{colw[1]}} {header[2]:>{colw[2]}} {header[3]:>{colw[3]}} {header[4]:>{colw[4]}}{Style.RESET_ALL}")
        sep_len = sum(colw) + (len(colw) - 1)
        portfolio_tables.append("-" * sep_len)
        for row in market_rows:
            ticker_cell = f"{str(row[0]):<{colw[0]}}"
            close_cell_plain = str(row[1]).rjust(colw[1])
            pct_change = str(row[2])
            pct_cell_plain = pct_change.rjust(colw[2])
            volume_cell_plain = str(row[3]).rjust(colw[3])
            avg_vol_cell_plain = str(row[4]).rjust(colw[4])
            close_cell = f"{Fore.YELLOW}{close_cell_plain}{Style.RESET_ALL}"
            if pct_change != "—" and pct_change.startswith(('+', '-')):
                pct_cell = f"{Fore.GREEN if pct_change.startswith('+') else Fore.RED}{pct_cell_plain}{Style.RESET_ALL}"
            else:
                pct_cell = pct_cell_plain
            volume_cell = f"{Fore.BLUE}{volume_cell_plain}{Style.RESET_ALL}"
            avg_volume_cell = f"{Fore.BLUE}{avg_vol_cell_plain}{Style.RESET_ALL}"
            portfolio_tables.append(f"{Fore.CYAN}{ticker_cell}{Style.RESET_ALL} {close_cell} {pct_cell} {volume_cell} {avg_volume_cell}")
        
        portfolio_tables.append(f"\n{Fore.CYAN}Current Portfolio State{Style.RESET_ALL}")
        portfolio_tables.append(self._format_portfolio_table(llm_portfolio, sort_by="value"))
        portfolio_tables.append(f"\n{Fore.CYAN}[ Company Fundamentals ]{Style.RESET_ALL}")
        portfolio_tables.append(self._format_fundamentals_table(portfolio_tickers, llm_portfolio))
        portfolio_tables.append(f"\n{Fore.CYAN}[ Fund Performance Summary ]{Style.RESET_ALL}")
        
        portfolio_tables.append(f"{Fore.GREEN}Portfolio Value:{Style.RESET_ALL} ${financial_data['total_portfolio_value']:,.2f}")
        portfolio_tables.append(f"{Fore.GREEN}Cash Balance:{Style.RESET_ALL} ${cash:,.2f}")
        portfolio_tables.append(f"{Fore.GREEN}Total Equity:{Style.RESET_ALL} ${total_equity:,.2f}")
        
        portfolio_data_string = "\n".join(portfolio_tables)

        # 5. Substitute placeholders in the template
        final_prompt = prompt_template.replace("{insert portfolio data}", portfolio_data_string)
        final_prompt = final_prompt.replace("{insert thesis}", thesis_text)
        final_prompt = final_prompt.replace("{fund_name}", fund_name)

        print(final_prompt)
        
        print(f"\n🔬 End of deep research prompt - copy everything above to your LLM")
    
    def _get_weekly_template_path(self) -> str:
        """Get the appropriate weekly template path based on fund type."""
        try:
            # Try to get fund type from active fund
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info.get("config"):
                fund_config = fund_info["config"]
                fund_type = fund_config.get("fund", {}).get("fund_type", "").lower()
                
                # Check for fund-specific templates
                if fund_type == "rrsp":
                    rrsp_template = Path("prompts/weekly_rrsp_template.txt")
                    if rrsp_template.exists():
                        return str(rrsp_template)
                elif fund_type == "tfsa":
                    tfsa_template = Path("prompts/weekly_tfsa_template.txt")
                    if tfsa_template.exists():
                        return str(tfsa_template)
        
        except ImportError:
            # Fund management not available, use default
            pass
        except Exception as e:
            # Any other error, fall back to default
            print(f"⚠️  Could not determine fund type: {e}")
        
        # Default to the generic weekly template
        return "prompts/weekly_template.txt"
    
    def _get_daily_template_path(self) -> str:
        """Get the appropriate daily template path based on fund type."""
        try:
            # Try to get fund type from active fund
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info.get("config"):
                fund_config = fund_info["config"]
                fund_type = fund_config.get("fund", {}).get("fund_type", "").lower()
                
                # Check for fund-specific templates
                if fund_type == "rrsp":
                    rrsp_template = Path("prompts/daily_rrsp_template.txt")
                    if rrsp_template.exists():
                        return str(rrsp_template)
                elif fund_type == "tfsa":
                    tfsa_template = Path("prompts/daily_tfsa_template.txt")
                    if tfsa_template.exists():
                        return str(tfsa_template)
        
        except ImportError:
            # Fund management not available, use default
            pass
        except Exception as e:
            # Any other error, fall back to default
            print(f"⚠️  Could not determine fund type for daily template: {e}")
        
        # Default to the generic daily template
        return "prompts/daily_template.txt"
    
    def _get_thesis_path(self) -> str:
        """Get the appropriate thesis file path based on active fund."""
        try:
            # Try to get thesis from active fund
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info["data_directory"]:
                fund_thesis_path = Path(fund_info["data_directory"]) / "thesis.yaml"
                if fund_thesis_path.exists():
                    return str(fund_thesis_path)
        
        except ImportError:
            # Fund management not available, use default
            pass
        except Exception as e:
            # Any other error, fall back to default
            print(f"⚠️  Could not determine thesis path: {e}")
        
        # Default to the legacy thesis location
        return "prompts/thesis.yaml"
    
    def _get_fund_name(self) -> str:
        """Get the fund name from active fund or settings."""
        try:
            # Try to get fund name from active fund
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info.get("config"):
                fund_config = fund_info["config"]
                fund_name = fund_config.get("fund", {}).get("name")
                if fund_name:
                    return fund_name
        
        except ImportError:
            # Fund management not available, use settings
            pass
        except Exception as e:
            # Any other error, fall back to settings
            print(f"⚠️  Could not get fund name from active fund: {e}")
        
        # Fallback to settings or generic name - graceful handling
        fund_name = self.settings.get('fund_details', {}).get('name')
        if not fund_name:
            print("⚠️  No fund name configured - using 'Trading Fund' as default")
            print("   💡 Tip: Set up a proper fund configuration for better organization")
            return "Trading Fund"
        return fund_name


def generate_daily_prompt(data_dir: Path | str | None = None) -> None:
    """Standalone function to generate daily prompt"""
    generator = PromptGenerator(data_dir)
    generator.generate_daily_prompt()


def generate_weekly_research_prompt(data_dir: Path | str | None = None) -> None:
    """Standalone function to generate weekly research prompt"""
    generator = PromptGenerator(data_dir)
    generator.generate_weekly_research_prompt()


def show_prompt_menu(args) -> None:
    """Show a small menu after generating the prompt with options to refresh or exit."""
    while True:
        print("\n" + "="*50)
        print("📋 Prompt Generator Options")
        print("="*50)
        print("[r] 🔄 Refresh (Clear Market Data Cache & Reload)")
        print("[Enter] 🚺 Exit")
        
        try:
            choice = input("\n❓ Select option (r or Enter): ").strip().lower()
            
            if choice == "r":
                # Clear cache and regenerate
                print("\n🔄 Clearing prompt screen caches and reloading...")
                
                # Clear only caches used by prompt generation (scoped clearing)
                cleared_caches = []
                
                # Clear price cache (market data used by prompt screen)
                try:
                    from market_data.price_cache import PriceCache
                    price_cache = PriceCache()
                    price_cache.invalidate_all()
                    cleared_caches.append("Price cache")
                except Exception as e:
                    print(f"⚠️  Failed to clear price cache: {e}")
                
                # Clear exchange rate cache (currency conversion)
                try:
                    from financial.currency_handler import CurrencyHandler
                    from pathlib import Path
                    currency_handler = CurrencyHandler(data_dir=Path(args.data_dir if hasattr(args, 'data_dir') and args.data_dir else 'trading_data/funds/TEST'))
                    currency_handler.clear_exchange_rate_cache()
                    cleared_caches.append("Exchange rate cache")
                except Exception as e:
                    print(f"⚠️  Failed to clear exchange rate cache: {e}")
                
                # Show results
                if cleared_caches:
                    print(f"✅ Cleared {len(cleared_caches)} cache types: {', '.join(cleared_caches)}")
                    print("ℹ️  Fundamentals and other unrelated caches preserved")
                else:
                    print("⚠️  No caches were successfully cleared")
                
                # Regenerate the prompt
                print("\n🔄 Regenerating prompt...")
                print("\n" + "="*80)
                if args.type == "daily":
                    generate_daily_prompt(args.data_dir)
                elif args.type == "weekly":
                    generate_weekly_research_prompt(args.data_dir)
                print("\n✅ Prompt refreshed successfully!")
                
            elif choice == "" or choice.lower() in ["exit", "quit", "q"]:
                print("\n👋 Exiting prompt generator...")
                break
            else:
                print("❌ Invalid choice. Please select 'r' or press Enter to exit.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate LLM trading prompts")
    parser.add_argument("--type", choices=["daily", "weekly"], default="daily",
                       help="Type of prompt to generate (default: daily)")
    parser.add_argument("--data-dir", help="Data directory (default: uses active fund directory)")
    parser.add_argument("--no-menu", action="store_true", 
                       help="Generate prompt and exit without showing menu")
    
    args = parser.parse_args()
    
    # Show environment banner
    from display.console_output import print_environment_banner
    print_environment_banner(args.data_dir)
    
    # Generate initial prompt
    if args.type == "daily":
        generate_daily_prompt(args.data_dir)
    elif args.type == "weekly":
        generate_weekly_research_prompt(args.data_dir)
    
    # Show menu unless --no-menu flag is used
    if not args.no_menu:
        print("\n" + "="*80)  # Visual separator between prompt and menu
        show_prompt_menu(args)
