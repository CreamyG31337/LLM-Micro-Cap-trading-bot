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
import pandas as pd

# Import from modular components
from config.constants import DEFAULT_DATA_DIR
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
try:
    from experiment_config import get_experiment_timeline
    _HAS_EXPERIMENT_CONFIG = True
except ImportError:
    _HAS_EXPERIMENT_CONFIG = False


class PromptGenerator:
    """Main class for generating trading prompts"""
    
    def __init__(self, data_dir: Path | str | None = None):
        """Initialize prompt generator with optional data directory"""
        self.data_dir = Path(data_dir) if data_dir else Path(DEFAULT_DATA_DIR)
        
        # Initialize components
        self.settings = get_settings()
        self.market_hours = MarketHours(self.settings)
        self.price_cache = PriceCache()
        self.market_data_fetcher = MarketDataFetcher(cache_instance=self.price_cache)
        
        # Initialize repository and portfolio manager
        from data.repositories.csv_repository import CSVRepository
        self.repository = CSVRepository(self.data_dir)
        self.portfolio_manager = PortfolioManager(self.repository)
        
    def _get_market_data_table(self, portfolio_tickers: List[str]) -> List[List[str]]:
        """Fetch market data for portfolio tickers and benchmarks"""
        rows: List[List[str]] = []
        
        # Get trading day window
        start_d, end_d = self.market_hours.trading_day_window()
        start_d = start_d - pd.Timedelta(days=4)  # Get more historical data
        
        # Get benchmarks (hardcoded for now, could be moved to config)
        benchmarks = ["SPY", "QQQ", "VTI"]
        all_tickers = portfolio_tickers + benchmarks
        
        for ticker in all_tickers:
            try:
                result = self.market_data_fetcher.fetch_price_data(ticker, start_d, end_d)
                data = result.df
                
                if data.empty or len(data) < 2:
                    rows.append([ticker, "—", "—", "—"])
                    continue
                
                price = float(data["Close"].iloc[-1])
                last_price = float(data["Close"].iloc[-2])
                volume = float(data["Volume"].iloc[-1])
                
                percent_change = ((price - last_price) / last_price) * 100
                rows.append([ticker, f"{price:,.2f}", f"{percent_change:+.2f}%", f"{int(volume):,}"])
                
            except Exception as e:
                print(f"Warning: Failed to fetch data for {ticker}: {e}")
                rows.append([ticker, "—", "—", "—"])
                
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
        lines.append(f"{Fore.CYAN}Portfolio Snapshot - {current_date}{Style.RESET_ALL}")
        lines.append(f"{Fore.YELLOW}{'Ticker':<10} {'Company':<25} {'Opened':<8} {'Shares':>8} {'Avg Price':>10} {'Current':>10} {'Total Value':>11} {'Dollar P&L':>11} {'Total P&L':>10} {'Daily P&L':>10}{Style.RESET_ALL}")
        # Compute separator length dynamically: sum of column widths + spaces between (9)
        _col_widths = [10, 25, 8, 8, 10, 10, 11, 11, 10, 10]
        _sep_len = sum(_col_widths) + 9
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

                # Combine P&L values with brackets around dollar amounts
                dollar_pnl_str = f"${dollar_pnl:+,.2f}" if dollar_pnl != 0 else "$0.00"
                total_pnl = f"{total_pnl_pct_str} [{dollar_pnl_str}]"
                
                # Use daily P&L from the row data (already calculated in trading script)
                daily_pnl_dollar = row.get('daily_pnl', 'N/A')
                if daily_pnl_dollar != 'N/A' and daily_pnl_dollar != '$0.00':
                    daily_pnl = f"{daily_pnl_pct_str} [{daily_pnl_dollar}]"
                else:
                    daily_pnl = f"{daily_pnl_pct_str} [$0.00]"

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
            shares_cell = f"{shares:>8.4f}"
            buy_price_cell = f"{buy_price_str:>10}"
            current_price_cell = f"{current_price_str:>10}"
            total_value_cell = f"{total_value_str:>11}"
            total_pnl_cell = f"{total_pnl:>16}"
            daily_pnl_cell = f"{daily_pnl:>16}"

            # Colorize padded P&L cells so ANSI codes don't affect alignment
            total_pnl_cell_colored = total_pnl_cell
            if total_pnl != "N/A" and total_pnl.startswith(("+", "-")):
                total_pnl_cell_colored = f"{Fore.GREEN if total_pnl.startswith('+') else Fore.RED}{total_pnl_cell}{Style.RESET_ALL}"

            daily_pnl_cell_colored = daily_pnl_cell
            if daily_pnl != "N/A" and daily_pnl.startswith(("+", "-")):
                daily_pnl_cell_colored = f"{Fore.GREEN if daily_pnl.startswith('+') else Fore.RED}{daily_pnl_cell}{Style.RESET_ALL}"

            # Apply colors to other columns
            line = (
                f"{Fore.CYAN}{ticker_cell}{Style.RESET_ALL} "
                f"{company_cell} "
                f"{Fore.BLUE}{opened_cell}{Style.RESET_ALL} "
                f"{shares_cell} "
                f"{Fore.BLUE}{buy_price_cell}{Style.RESET_ALL} "
                f"{Fore.YELLOW}{current_price_cell}{Style.RESET_ALL} "
                f"{Fore.YELLOW}{total_value_cell}{Style.RESET_ALL} "
                f"{total_pnl_cell_colored} "
                f"{daily_pnl_cell_colored}"
            )
            lines.append(line)
        
        return "\n".join(lines)
            
    def _get_daily_instructions(self) -> str:
        """Get daily trading instructions"""
        if _HAS_MARKET_CONFIG:
            try:
                return get_daily_instructions()
            except Exception as e:
                print(f"Warning: Failed to get instructions from market_config: {e}")
                return self._get_default_daily_instructions()
        else:
            return self._get_default_daily_instructions()
            
    def _get_default_daily_instructions(self) -> str:
        """Default daily instructions if market_config not available"""
        return (
            "Use this info to make decisions regarding your Canadian small-cap portfolio. "
            "You have complete control over every decision. Make any changes you believe are beneficial—no approval required.\n"
            "\n"
            "Focus on Canadian small-caps (CAD 50M - CAD 500M market cap) listed on TSX or TSX Venture Exchange.\n"
            "Consider Canadian market dynamics, regulatory environment, and sector-specific catalysts.\n"
            "All positions trade in CAD. Account for TSX/TSXV trading hours and liquidity.\n"
            "\n"
            "Deep research is not permitted. Act at your discretion to achieve the best outcome.\n"
            "If you do not make a clear indication to change positions IMMEDIATELY after this message, "
            "the portfolio remains unchanged for tomorrow.\n"
            "You are encouraged to use the internet to check current Canadian market conditions "
            "and company-specific info for potential buys.\n"
            "\n"
            "*Paste everything above into your preferred LLM (ChatGPT, Claude, Gemini, etc.)*"
        )
        
    def generate_daily_prompt(self, data_dir: Path | str | None = None) -> None:
        """Generate and display daily trading prompt with live data"""
        if data_dir:
            self.data_dir = Path(data_dir)
            # Reinitialize repository with new data dir
            from data.repositories.csv_repository import CSVRepository
            self.repository = CSVRepository(self.data_dir)
            self.portfolio_manager = PortfolioManager(self.repository)
            
        # Load portfolio data
        try:
            latest_snapshot = self.portfolio_manager.get_latest_portfolio()
            if latest_snapshot is None:
                print(f"❌ No portfolio data found in {self.data_dir}")
                print("Please run the main trading script first to create portfolio data.")
                return
            
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
        market_rows = self._get_market_data_table(portfolio_tickers)
        
        # Format cash information
        cash_display, total_equity = self._format_cash_info(cash)
        
        # Get current date
        today = self.market_hours.last_trading_date_str()
        
        # Calculate experiment timeline
        if _HAS_EXPERIMENT_CONFIG:
            week_num, day_num = get_experiment_timeline()
            timeline_text = f"Week {week_num} Day {day_num}"
        else:
            # Fallback to simple date if experiment config not available
            timeline_text = today
        
        # Generate the prompt with optimized formatting for both humans and LLMs
        # Design: Clean headers, colored data, minimal separators to save context space
        print(f"\n[PROMPT] Daily Results — {today} ({timeline_text})")
        print("Copy everything below and paste into your LLM:")
        
        # Market data table with colors for human readability
        # Colors are stripped during copy/paste, so they don't affect LLM context
        print(f"\n{Fore.CYAN}[ Price & Volume ]{Style.RESET_ALL}")
        header = ["Ticker", "Close", "% Chg", "Volume"]
        colw = [10, 12, 9, 15]
        print(f"{Fore.YELLOW}{header[0]:<{colw[0]}} {header[1]:>{colw[1]}} {header[2]:>{colw[2]}} {header[3]:>{colw[3]}}{Style.RESET_ALL}")
        print("-" * (colw[0] + colw[1] + colw[2] + colw[3] + 3))  # Add separator line
        for row in market_rows:
            # Build padded cells first, then apply color so ANSI codes don't affect spacing
            ticker_cell = f"{str(row[0]):<{colw[0]}}"
            close_cell_plain = str(row[1]).rjust(colw[1])
            pct_change = str(row[2])
            pct_cell_plain = pct_change.rjust(colw[2])
            volume_cell_plain = str(row[3]).rjust(colw[3])

            # Apply colors to fully padded cells
            close_cell = f"{Fore.YELLOW}{close_cell_plain}{Style.RESET_ALL}"
            if pct_change != "—" and pct_change.startswith(('+', '-')):
                pct_cell = f"{Fore.GREEN if pct_change.startswith('+') else Fore.RED}{pct_cell_plain}{Style.RESET_ALL}"
            else:
                pct_cell = pct_cell_plain
            volume_cell = f"{Fore.BLUE}{volume_cell_plain}{Style.RESET_ALL}"

            print(f"{Fore.CYAN}{ticker_cell}{Style.RESET_ALL} {close_cell} {pct_cell} {volume_cell}")
            
        # Portfolio snapshot with enhanced formatting
        print(f"\n{Fore.CYAN}[ Portfolio Snapshot ]{Style.RESET_ALL}")
        print(self._format_portfolio_table(llm_portfolio, sort_by="date"))
            
        # Financial summary with color-coded labels for quick scanning
        print(f"\n{Fore.GREEN}Cash Balances:{Style.RESET_ALL} {cash_display}")
        print(f"{Fore.GREEN}Latest LLM Equity:{Style.RESET_ALL} ${total_equity:,.2f}")
        print(f"{Fore.BLUE}Maximum Drawdown:{Style.RESET_ALL} 0.00% (new portfolio)")
            
                    
        # Instructions section - the core trading guidance
        print(f"\n{Fore.CYAN}[ Your Instructions ]{Style.RESET_ALL}")
        instructions = self._get_daily_instructions()
        # Preserve original content; only adapt output if console can't handle Unicode
        from display.console_output import format_text_for_console
        print(format_text_for_console(instructions))
        
        print(f"\n[END] End of prompt - copy everything above to your LLM")
        
    def generate_weekly_research_prompt(self, data_dir: Path | str | None = None) -> None:
        """Generate and display weekly deep research prompt"""
        if data_dir:
            # Import here to avoid circular imports
            try:
                from config.settings import set_data_dir
            except ImportError:
                # Fallback if not available
                pass
            else:
                set_data_dir(Path(data_dir))
            
        # Load portfolio data
        portfolio_file = self.data_dir / "llm_portfolio_update.csv"
        
        if not portfolio_file.exists():
            print(f"❌ Portfolio file not found: {portfolio_file}")
            print("Please run the main trading script first to create portfolio data.")
            return
            
        try:
            # Import here to avoid circular imports
            try:
                from trading_script import load_latest_portfolio_state
            except ImportError:
                print("❌ Required module trading_script not found")
                return

            llm_portfolio, cash = load_latest_portfolio_state(str(portfolio_file))
        except Exception as e:
            print(f"❌ Error loading portfolio data: {e}")
            return
            
        # Format cash information
        cash_display, total_equity = self._format_cash_info(cash)
        
        # Calculate experiment timeline using proper configuration
        if _HAS_EXPERIMENT_CONFIG:
            week_num, day_num = get_experiment_timeline()
        else:
            # Fallback calculation if experiment config not available
            today = datetime.now()
            start_date = datetime(2024, 6, 30)  # Fallback start date
            days_since_start = (today - start_date).days
            week_num = max(1, days_since_start // 7)
            day_num = days_since_start % 7 + 1
        
        # Generate the deep research prompt with same color scheme as daily prompt
        # Weekly prompts need more comprehensive analysis, so colors help organize complex data
        print(f"\n🔬 Weekly Deep Research - Week {week_num} Day {day_num}")
        print("Copy everything below and paste into your LLM for deep research:")
        
        # System Message
        print("""System Message

You are a professional-grade portfolio analyst operating in Deep Research Mode. Your job is to reevaluate the portfolio and produce a complete action plan with exact orders. Optimize risk-adjusted return under strict constraints. Begin by restating the rules to confirm understanding, then deliver your research, decisions, and orders.

Core Rules
- Budget discipline: no new capital beyond what is shown. Track cash precisely.
- Execution limits: fractional shares supported (Wealthsimple). No options, shorting, leverage, margin, or derivatives. Long-only.
- Universe: primarily U.S. micro-caps under 300M market cap unless told otherwise. Respect liquidity, average volume, spread, and slippage.
- Risk control: respect provided stop-loss levels and position sizing. Flag any breaches immediately.
- Cadence: this is the weekly deep research window. You may add new names, exit, trim, or add to positions.
- Complete freedom: you have complete control to act in your best interest to generate alpha.

Deep Research Requirements
- Reevaluate current holdings and consider new candidates.
- Build a clear rationale for every keep, add, trim, exit, and new entry.
- Provide exact order details for every proposed trade.
- Confirm liquidity and risk checks before finalizing orders.
- End with a short thesis review summary for next week.

Order Specification Format
Action: buy or sell
Ticker: symbol
Shares: decimal (fractional shares supported)
Order type: limit preferred, or market with reasoning
Limit price: exact number
Time in force: DAY or GTC
Intended execution date: YYYY-MM-DD
Stop loss (for buys): exact number and placement logic
Special instructions: if needed (e.g., open at or below limit, open only, do not exceed spread threshold)
One-line rationale

Required Sections For Your Reply
- Restated Rules
- Research Scope
- Current Portfolio Assessment
- Candidate Set
- Portfolio Actions
- Exact Orders
- Risk And Liquidity Checks
- Monitoring Plan
- Thesis Review Summary
- Confirm Cash And Constraints

User Message
Context""")
        
        print(f"It is Week {week_num} Day {day_num} of a 6-month live experiment.")
        print()
        print(f"{Fore.GREEN}Cash Available{Style.RESET_ALL}")
        print(cash_display)
        print()
        print(f"{Fore.CYAN}Current Portfolio State{Style.RESET_ALL}")
        print(self._format_portfolio_table(llm_portfolio, sort_by="value"))
        print()
        print(f"{Fore.CYAN}[ Snapshot ]{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Cash Balance:{Style.RESET_ALL} ${cash:,.2f}")
        print(f"{Fore.GREEN}Total Equity:{Style.RESET_ALL} ${total_equity:,.2f}")
        print()
        print("Last Analyst Thesis For Current Holdings")
        print("(Previous research summary would go here - this could be enhanced to track thesis history)")
        print()
        print("""Execution Policy
Describe how orders are executed in this system for clarity (e.g., open-driven limit behavior, or standard limit day orders). If unspecified, assume standard limit DAY orders placed for the next session.

Constraints And Reminders To Enforce
- Hard budget. Use only available cash shown above. No new capital.
- Fractional shares supported (Wealthsimple). No options/shorting/margin/derivatives.
- Prefer U.S. micro-caps and respect liquidity.
- Be sure to use up-to-date stock data for pricing details.
- Focus on alpha generation and risk-adjusted returns.
- This is live money - be thorough and disciplined.""")
        
        print(f"\n🔬 End of deep research prompt - copy everything above to your LLM")


def generate_daily_prompt(data_dir: Path | str | None = None) -> None:
    """Standalone function to generate daily prompt"""
    generator = PromptGenerator(data_dir)
    generator.generate_daily_prompt()


def generate_weekly_research_prompt(data_dir: Path | str | None = None) -> None:
    """Standalone function to generate weekly research prompt"""
    generator = PromptGenerator(data_dir)
    generator.generate_weekly_research_prompt()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate LLM trading prompts")
    parser.add_argument("--type", choices=["daily", "weekly"], default="daily",
                       help="Type of prompt to generate (default: daily)")
    parser.add_argument("--data-dir", help="Data directory (default: trading_data/prod)")
    
    args = parser.parse_args()
    
    # Show environment banner
    from display.console_output import print_environment_banner
    print_environment_banner(args.data_dir)
    
    if args.type == "daily":
        generate_daily_prompt(args.data_dir)
    elif args.type == "weekly":
        generate_weekly_research_prompt(args.data_dir)
