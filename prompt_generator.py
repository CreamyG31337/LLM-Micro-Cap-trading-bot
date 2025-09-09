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
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

# Import from trading_script for data access
from trading_script import (
    DATA_DIR, PORTFOLIO_CSV, 
    load_latest_portfolio_state, load_benchmarks, download_price_data,
    last_trading_date, check_weekend, set_data_dir,
    load_fund_contributions, calculate_ownership_percentages
)

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
        
        # Generate the prompt
        print("\n" + "=" * 80)
        print("📋 COPY EVERYTHING BELOW AND PASTE INTO YOUR LLM")
        print("=" * 80)
        print(f"Daily Results — {today}")
        print("=" * 80)
        
        # Market data table
        print("\n[ Price & Volume ]")
        header = ["Ticker", "Close", "% Chg", "Volume"]
        colw = [10, 12, 9, 15]
        print(f"{header[0]:<{colw[0]}} {header[1]:>{colw[1]}} {header[2]:>{colw[2]}} {header[3]:>{colw[3]}}")
        print("-" * sum(colw) + "-" * 3)
        for row in market_rows:
            print(f"{str(row[0]):<{colw[0]}} {str(row[1]):>{colw[1]}} {str(row[2]):>{colw[2]}} {str(row[3]):>{colw[3]}}")
            
        # Portfolio snapshot
        print("\n[ Portfolio Snapshot ]")
        if llm_portfolio.empty:
            print("No current holdings")
        else:
            print(llm_portfolio.to_string(index=False))
            
        # Cash and equity
        print(f"\nCash Balances: {cash_display}")
        print(f"Latest LLM Equity: ${total_equity:,.2f}")
        print("Maximum Drawdown: 0.00% (new portfolio)")
            
        # Fund ownership if available
        contributions_df = load_fund_contributions(str(self.data_dir))
        if not contributions_df.empty:
            ownership = calculate_ownership_percentages(str(self.data_dir))
            if ownership:
                print("\n[ Fund Ownership ]")
                for contributor, percentage in ownership.items():
                    print(f"{contributor}: {percentage:.1f}%")
                    
        # Instructions
        print("\n[ Your Instructions ]")
        instructions = self._get_daily_instructions()
        print(instructions)
        
        print("\n" + "=" * 80)
        print("📋 COPY EVERYTHING ABOVE AND PASTE INTO YOUR LLM")
        print("=" * 80)
        
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
        
        # Generate the deep research prompt
        print("\n" + "=" * 80)
        print("🔬 COPY EVERYTHING BELOW AND PASTE INTO YOUR LLM FOR DEEP RESEARCH")
        print("=" * 80)
        
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
        print("Cash Available")
        print(cash_display)
        print()
        print("Current Portfolio State")
        print("[ Holdings ]")
        if llm_portfolio.empty:
            print("No current holdings")
        else:
            print(llm_portfolio.to_string(index=False))
        print()
        print("[ Snapshot ]")
        print(f"Cash Balance: ${cash:,.2f}")
        print(f"Total Equity: ${total_equity:,.2f}")
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
        
        print("\n" + "=" * 80)
        print("🔬 COPY EVERYTHING ABOVE AND PASTE INTO YOUR LLM FOR DEEP RESEARCH")
        print("=" * 80)


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
