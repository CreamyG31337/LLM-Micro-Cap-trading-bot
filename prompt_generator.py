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

# Import from trading_script for data access
from trading_script import (
    DATA_DIR, PORTFOLIO_CSV, TRADE_LOG_CSV,
    load_latest_portfolio_state, load_benchmarks, download_price_data,
    last_trading_date, check_weekend, set_data_dir,
    load_fund_contributions, calculate_ownership_percentages,
    get_company_name, trading_day_window
)

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


class PromptGenerator:
    """Main class for generating trading prompts"""
    
    def __init__(self, data_dir: Path | str | None = None):
        """Initialize prompt generator with optional data directory"""
        if data_dir:
            set_data_dir(Path(data_dir))
        self.data_dir = DATA_DIR
        
    def _get_market_data_table(self, portfolio_tickers: List[str]) -> List[List[str]]:
        """Fetch market data for portfolio tickers and benchmarks"""
        rows: List[List[str]] = []
        
        end_d = last_trading_date()
        start_d = (end_d - pd.Timedelta(days=4)).normalize()
        
        # Get benchmarks
        benchmarks = load_benchmarks()
        all_tickers = portfolio_tickers + benchmarks
        
        for ticker in all_tickers:
            try:
                fetch = download_price_data(ticker, start=start_d, end=(end_d + pd.Timedelta(days=1)), progress=False)
                data = fetch.df
                
                if data.empty or len(data) < 2:
                    rows.append([ticker, "—", "—", "—"])
                    continue
                
                price = float(data["Close"].iloc[-1].item())
                last_price = float(data["Close"].iloc[-2].item())
                volume = float(data["Volume"].iloc[-1].item())
                
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
    
    def _format_portfolio_table(self, portfolio_df: pd.DataFrame) -> str:
        """Format portfolio data with enhanced date range and P&L information
        
        Design decisions:
        - Colors enhance human readability but are stripped during copy/paste
        - Consistent column alignment makes data easy for LLMs to parse
        - Shows both daily and total P&L for comprehensive performance context
        - Position open dates provide historical context
        - Minimal separators save context space while maintaining structure
        """
        if portfolio_df.empty:
            return "No current holdings"
        
        # Load trade log to get position open dates
        trade_log_df = None
        try:
            trade_log_df = pd.read_csv(TRADE_LOG_CSV)
            # Handle PST timezone properly - remove PST suffix and localize to PST
            trade_log_df['Date'] = trade_log_df['Date'].astype(str).str.replace(" PST", " -0800")
            trade_log_df['Date'] = pd.to_datetime(trade_log_df['Date'], format="mixed", utc=True)
        except Exception:
            trade_log_df = None
        
        # Get current date for context
        current_date = last_trading_date().strftime("%Y-%m-%d")
        s, e = trading_day_window()
        
        # Create enhanced portfolio display with colors
        # Color scheme: Cyan=tickers, Yellow=headers/prices, Blue=dates, Green/Red=P&L
        lines = []
        lines.append(f"{Fore.CYAN}Portfolio Snapshot - {current_date}{Style.RESET_ALL}")
        lines.append(f"{Fore.YELLOW}{'Ticker':<10} {'Company':<25} {'Opened':<8} {'Shares':<8} {'Buy Price':<10} {'Current':<10} {'Total P&L':<10} {'Daily P&L':<10}{Style.RESET_ALL}")
        
        for _, row in portfolio_df.iterrows():
            ticker = str(row.get('ticker', ''))
            company_name = get_company_name(ticker)
            # Truncate long company names
            display_name = company_name[:22] + "..." if len(company_name) > 25 else company_name
            
            # Get position open date
            open_date = "N/A"
            if trade_log_df is not None:
                ticker_trades = trade_log_df[trade_log_df['Ticker'] == ticker]
                if not ticker_trades.empty:
                    open_date = ticker_trades['Date'].min().strftime("%m/%d")
            
            # Fetch current price data
            try:
                fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
                if not fetch.df.empty and "Close" in fetch.df.columns:
                    current_price = float(fetch.df['Close'].iloc[-1].item())
                    buy_price = float(row.get('buy_price', 0))
                    shares = float(row.get('shares', 0))
                    
                    # Calculate total P&L since position opened
                    if buy_price > 0:
                        total_pnl_pct = ((current_price - buy_price) / buy_price) * 100
                        total_pnl = f"{total_pnl_pct:+.1f}%"
                    else:
                        total_pnl = "N/A"
                    
                    # Calculate daily P&L (today vs yesterday)
                    if len(fetch.df) > 1:
                        prev_price = float(fetch.df['Close'].iloc[-2].item())
                        daily_pnl_pct = ((current_price - prev_price) / prev_price) * 100
                        daily_pnl = f"{daily_pnl_pct:+.1f}%"
                    else:
                        daily_pnl = "N/A"
                    
                    current_price_str = f"${current_price:.2f}"
                else:
                    current_price_str = "N/A"
                    total_pnl = "N/A"
                    daily_pnl = "N/A"
            except Exception:
                current_price_str = "N/A"
                total_pnl = "N/A"
                daily_pnl = "N/A"
            
            # Color code P&L values - Green for positive, Red for negative
            # This makes performance immediately visible to humans while preserving data for LLMs
            total_pnl_colored = total_pnl
            daily_pnl_colored = daily_pnl
            if total_pnl != "N/A" and total_pnl.startswith(('+', '-')):
                total_pnl_colored = f"{Fore.GREEN if total_pnl.startswith('+') else Fore.RED}{total_pnl}{Style.RESET_ALL}"
            if daily_pnl != "N/A" and daily_pnl.startswith(('+', '-')):
                daily_pnl_colored = f"{Fore.GREEN if daily_pnl.startswith('+') else Fore.RED}{daily_pnl}{Style.RESET_ALL}"
            
            # Format each row with consistent colors and alignment
            # Colors help humans scan data quickly, alignment helps LLMs parse structure
            lines.append(f"{Fore.CYAN}{ticker:<10}{Style.RESET_ALL} {display_name:<25} {Fore.BLUE}{open_date:<8}{Style.RESET_ALL} {shares:<8.4f} {Fore.BLUE}${row.get('buy_price', 0):<9.2f}{Style.RESET_ALL} {Fore.YELLOW}{current_price_str:<10}{Style.RESET_ALL} {total_pnl_colored:<10} {daily_pnl_colored:<10}")
        
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
            set_data_dir(Path(data_dir))
            
        # Load portfolio data
        portfolio_file = self.data_dir / "llm_portfolio_update.csv"
        
        if not portfolio_file.exists():
            print(f"❌ Portfolio file not found: {portfolio_file}")
            print("Please run the main trading script first to create portfolio data.")
            return
            
        try:
            llm_portfolio, cash = load_latest_portfolio_state(str(portfolio_file))
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
        today = check_weekend()
        
        # Generate the prompt with optimized formatting for both humans and LLMs
        # Design: Clean headers, colored data, minimal separators to save context space
        print(f"\n📋 Daily Results — {today}")
        print("Copy everything below and paste into your LLM:")
        
        # Market data table with colors for human readability
        # Colors are stripped during copy/paste, so they don't affect LLM context
        print(f"\n{Fore.CYAN}[ Price & Volume ]{Style.RESET_ALL}")
        header = ["Ticker", "Close", "% Chg", "Volume"]
        colw = [10, 12, 9, 15]
        print(f"{Fore.YELLOW}{header[0]:<{colw[0]}} {header[1]:>{colw[1]}} {header[2]:>{colw[2]}} {header[3]:>{colw[3]}}{Style.RESET_ALL}")
        for row in market_rows:
            # Color code percentage changes - Green for gains, Red for losses
            pct_change = str(row[2])
            pct_colored = pct_change
            if pct_change != "—" and pct_change.startswith(('+', '-')):
                pct_colored = f"{Fore.GREEN if pct_change.startswith('+') else Fore.RED}{pct_change}{Style.RESET_ALL}"
            
            print(f"{Fore.CYAN}{str(row[0]):<{colw[0]}}{Style.RESET_ALL} {Fore.YELLOW}{str(row[1]):>{colw[1]}}{Style.RESET_ALL} {pct_colored:>{colw[2]}} {Fore.BLUE}{str(row[3]):>{colw[3]}}{Style.RESET_ALL}")
            
        # Portfolio snapshot with enhanced formatting
        print(f"\n{Fore.CYAN}[ Portfolio Snapshot ]{Style.RESET_ALL}")
        print(self._format_portfolio_table(llm_portfolio))
            
        # Financial summary with color-coded labels for quick scanning
        print(f"\n{Fore.GREEN}Cash Balances:{Style.RESET_ALL} {cash_display}")
        print(f"{Fore.GREEN}Latest LLM Equity:{Style.RESET_ALL} ${total_equity:,.2f}")
        print(f"{Fore.BLUE}Maximum Drawdown:{Style.RESET_ALL} 0.00% (new portfolio)")
            
        # Fund ownership if available - shows contribution breakdown
        contributions_df = load_fund_contributions(str(self.data_dir))
        if not contributions_df.empty:
            ownership = calculate_ownership_percentages(str(self.data_dir))
            if ownership:
                print(f"\n{Fore.CYAN}[ Fund Ownership ]{Style.RESET_ALL}")
                for contributor, percentage in ownership.items():
                    print(f"{Fore.YELLOW}{contributor}:{Style.RESET_ALL} {Fore.BLUE}{percentage:.1f}%{Style.RESET_ALL}")
                    
        # Instructions section - the core trading guidance
        print(f"\n{Fore.CYAN}[ Your Instructions ]{Style.RESET_ALL}")
        instructions = self._get_daily_instructions()
        print(instructions)
        
        print(f"\n📋 End of prompt - copy everything above to your LLM")
        
    def generate_weekly_research_prompt(self, data_dir: Path | str | None = None) -> None:
        """Generate and display weekly deep research prompt"""
        if data_dir:
            set_data_dir(Path(data_dir))
            
        # Load portfolio data
        portfolio_file = self.data_dir / "llm_portfolio_update.csv"
        
        if not portfolio_file.exists():
            print(f"❌ Portfolio file not found: {portfolio_file}")
            print("Please run the main trading script first to create portfolio data.")
            return
            
        try:
            llm_portfolio, cash = load_latest_portfolio_state(str(portfolio_file))
        except Exception as e:
            print(f"❌ Error loading portfolio data: {e}")
            return
            
        # Format cash information
        cash_display, total_equity = self._format_cash_info(cash)
        
        # Calculate week and day (simplified - could be enhanced)
        today = datetime.now()
        # This is a simplified calculation - you might want to track actual experiment weeks
        start_date = datetime(2024, 6, 30)  # Approximate start of experiment
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
        print(self._format_portfolio_table(llm_portfolio))
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
    parser.add_argument("--data-dir", help="Data directory (default: my trading)")
    
    args = parser.parse_args()
    
    if args.type == "daily":
        generate_daily_prompt(args.data_dir)
    elif args.type == "weekly":
        generate_weekly_research_prompt(args.data_dir)
