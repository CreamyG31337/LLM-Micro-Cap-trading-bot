#!/usr/bin/env python3
"""
AI Context Builder
==================

Formats dashboard data objects into LLM-friendly text/JSON.
Converts portfolio data, trades, metrics, etc. into structured context for AI analysis.
"""

import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import sys
from pathlib import Path

# Add project root to path for market data imports
# ai_context_builder.py is in web_dashboard/, so parent is the project root
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def format_holdings(
    positions_df: pd.DataFrame, 
    fund: str,
    trades_df: Optional[pd.DataFrame] = None,
    include_price_volume: bool = True,
    include_fundamentals: bool = True
) -> str:
    """Format holdings/positions data for LLM context in compact table format.
    
    Token Optimization Notes:
    - Uses single-line per holding (vs 5 lines before) = ~70% token reduction
    - Quantities use 2 decimals max (was 4)
    - Removes redundant labels, uses column headers instead
    - Follows console app's prompt_generator.py format for consistency
    - Includes Daily P&L and Sector for richer analysis
    
    Args:
        positions_df: DataFrame with current positions
        fund: Fund name
        trades_df: Optional DataFrame with trade history for opened date lookup
        include_price_volume: If True, include Price & Volume table (default: True)
        include_fundamentals: If True, include Company Fundamentals table (default: True)
        
    Returns:
        Formatted string with holdings data in compact table format
    """
    if positions_df.empty:
        return f"Fund: {fund}\nHoldings: No current positions."
    
    sections = []
    
    # Section 1: Price & Volume Table (optional)
    if include_price_volume:
        price_volume_table = format_price_volume_table(positions_df)
        if price_volume_table:
            sections.append(price_volume_table)
    
    # Section 2: Portfolio Snapshot Table (always included)
    portfolio_snapshot = _format_portfolio_snapshot_table(positions_df, fund, trades_df)
    sections.append(portfolio_snapshot)
    
    # Section 3: Company Fundamentals Table (optional)
    if include_fundamentals:
        fundamentals_table = format_fundamentals_table(positions_df)
        if fundamentals_table:
            sections.append(fundamentals_table)
    
    return "\n\n".join(sections)


def _format_portfolio_snapshot_table(
    positions_df: pd.DataFrame, 
    fund: str,
    trades_df: Optional[pd.DataFrame] = None
) -> str:
    """Format the main portfolio snapshot table with all position details."""
    lines = [
        f"[ Portfolio Snapshot ]",
        f"Fund: {fund}",
        f"Holdings ({len(positions_df)} positions):",
        "",
        "Ticker    | Company                  | Opened  | Shares  | Avg Price | Current  | Total Value | % Port | Total P&L        | Daily P&L        | 5-Day P&L",
        "----------|--------------------------|---------|---------|------------|----------|-------------|--------|-----------------|------------------|-----------"
    ]
    
    # Build opened date lookup from trades_df - find first BUY for each ticker
    opened_dates = {}
    if trades_df is not None and not trades_df.empty:
        # Get ticker column (try both 'ticker' and 'symbol')
        ticker_col = 'ticker' if 'ticker' in trades_df.columns else 'symbol'
        timestamp_col = 'timestamp' if 'timestamp' in trades_df.columns else 'date'
        
        # Filter BUY trades only - infer from reason field
        if 'reason' in trades_df.columns:
            # Infer from reason field - only include non-SELL trades
            def is_buy_trade(reason):
                if pd.isna(reason) or reason is None:
                    return True  # Default to BUY if no reason
                reason_lower = str(reason).lower()
                return not ('sell' in reason_lower or 'limit sell' in reason_lower or 'market sell' in reason_lower)
            buy_trades = trades_df[trades_df['reason'].apply(is_buy_trade)].copy()
        else:
            # No way to determine action, assume all are BUY trades
            buy_trades = trades_df.copy()
        
        if not buy_trades.empty:
            # Convert timestamp to datetime for sorting
            try:
                buy_trades['_parsed_timestamp'] = pd.to_datetime(buy_trades[timestamp_col])
            except:
                buy_trades['_parsed_timestamp'] = pd.NaT
            
            # Group by ticker and find earliest BUY trade
            for ticker in buy_trades[ticker_col].unique():
                if pd.isna(ticker) or not ticker:
                    continue
                
                ticker_buys = buy_trades[buy_trades[ticker_col] == ticker]
                if not ticker_buys.empty:
                    # Sort by timestamp and get first
                    ticker_buys_sorted = ticker_buys.sort_values('_parsed_timestamp')
                    first_buy = ticker_buys_sorted.iloc[0]
                    timestamp = first_buy.get('_parsed_timestamp')
                    
                    if pd.notna(timestamp):
                        opened_dates[ticker] = timestamp
    
    # Calculate total portfolio value for % Port
    total_portfolio_value = sum(float(row.get('market_value', 0) or 0) for _, row in positions_df.iterrows())
    
    total_cost = 0.0
    total_value = 0.0
    total_pnl = 0.0
    total_daily_pnl = 0.0
    
    for idx, row in positions_df.iterrows():
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        quantity = float(row.get('quantity', row.get('shares', 0)) or 0)
        currency = row.get('currency', 'CAD')
        cost_basis = float(row.get('cost_basis', 0) or 0)
        market_value = float(row.get('market_value', 0) or 0)
        pnl = float(row.get('unrealized_pnl', 0) or 0)
        pnl_pct = float(row.get('unrealized_pnl_pct', row.get('return_pct', 0)) or 0)
        current_price = float(row.get('current_price', row.get('price', 0)) or 0)
        
        # Get daily P&L from view (may be None/null)
        daily_pnl = float(row.get('daily_pnl', 0) or 0)
        daily_pnl_pct = float(row.get('daily_pnl_pct', 0) or 0)
        
        # Get 5-day P&L from view
        five_day_pnl = float(row.get('five_day_pnl', 0) or 0)
        five_day_pnl_pct = float(row.get('five_day_pnl_pct', 0) or 0)
        
        # Get company name (truncate to 25 chars, matching console app format)
        company = row.get('company', '')
        if company:
            company_str = str(company)[:22] + "..." if len(str(company)) > 25 else str(company)
        else:
            company_str = symbol[:25]
        
        # Get opened date
        opened_date_str = "N/A"
        if symbol in opened_dates:
            try:
                opened_date_str = opened_dates[symbol].strftime('%m-%d-%y')
            except:
                pass
        
        # Calculate avg price
        avg_price = (cost_basis / quantity) if quantity > 0 else 0.0
        avg_price_str = f"${avg_price:.2f}" if avg_price > 0 else "N/A"
        
        # Calculate % Port
        pct_port = (market_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
        pct_port_str = f"{pct_port:.1f}%"
        
        # Format Total P&L (combine dollar and percentage)
        if pnl != 0:
            total_pnl_str = f"${pnl:+,.2f} {pnl_pct:+.1f}%"
        else:
            total_pnl_str = "$0.00 0.0%"
        
        # Format Daily P&L (combine dollar and percentage)
        if daily_pnl != 0 and daily_pnl_pct != 0:
            daily_pnl_str = f"${daily_pnl:+,.2f} {daily_pnl_pct:+.1f}%"
        elif daily_pnl != 0:
            daily_pnl_str = f"${daily_pnl:+,.2f}"
        else:
            daily_pnl_str = "$0.00 0.0%"
        
        # Format 5-Day P&L (combine dollar and percentage)
        if five_day_pnl != 0 and five_day_pnl_pct != 0:
            five_day_pnl_str = f"${five_day_pnl:+,.2f} {five_day_pnl_pct:+.1f}%"
        elif five_day_pnl != 0:
            five_day_pnl_str = f"${five_day_pnl:+,.2f}"
        else:
            five_day_pnl_str = "N/A"
        
        # Track totals
        total_cost += cost_basis
        total_value += market_value
        total_pnl += pnl
        total_daily_pnl += daily_pnl
        
        # Format row
        lines.append(
            f"{symbol:<9} | {company_str:<25} | {opened_date_str:<8} | {quantity:>7.1f} | {avg_price_str:>10} | "
            f"${current_price:>7.2f} | ${market_value:>10,.0f} | {pct_port_str:>6} | {total_pnl_str:>16} | "
            f"{daily_pnl_str:>16} | {five_day_pnl_str:>10}"
        )
    
    # Summary row
    if total_value > 0:
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        daily_summary = f"${total_daily_pnl:+,.2f}" if total_daily_pnl != 0 else "$0.00"
        lines.append("----------|--------------------------|---------|---------|------------|----------|-------------|--------|-----------------|------------------|-----------")
        lines.append(
            f"{'TOTAL':<9} | {'':25} | {'':8} | {'':8} | {'':10} | {'':9} | ${total_value:>10,.0f} | {'':6} | "
            f"${total_pnl:+,.2f} {total_pnl_pct:+.1f}% | {daily_summary:>16} | {'':10}"
        )
    
    return "\n".join(lines)


def format_price_volume_table(positions_df: pd.DataFrame) -> str:
    """Format Price & Volume table for portfolio tickers.
    
    Uses data from positions_df (current_price, yesterday_price already in DB view).
    Only fetches volume data from MarketDataFetcher since it's not in the DB.
    
    Args:
        positions_df: DataFrame with current positions (from get_current_positions)
                     Expected columns: ticker, current_price, yesterday_price, etc.
        
    Returns:
        Formatted string with Price & Volume data
    """
    if positions_df.empty:
        return ""
    
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"[ai_context_builder.format_price_volume_table] Processing {len(positions_df)} positions")
    
    lines = [
        "[ Price & Volume ]",
        "Ticker            | Close     | % Chg       | Volume  | Avg Vol (30d)",
        "------------------|-----------|-------------|---------|---------------"
    ]
    
    # Try to import MarketDataFetcher for volume data ONLY
    market_fetcher = None
    market_hours = None
    try:
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from market_data.market_hours import MarketHours
        from config.settings import get_settings
        
        settings = get_settings()
        price_cache = PriceCache(settings=settings)
        market_fetcher = MarketDataFetcher(cache_instance=price_cache)
        market_hours = MarketHours(settings=settings)
        logger.debug(f"[ai_context_builder.format_price_volume_table] MarketDataFetcher initialized")
    except Exception as e:
        logger.warning(f"[ai_context_builder.format_price_volume_table] MarketDataFetcher not available: {e}")
    
    for idx, row in positions_df.iterrows():
        ticker = row.get('symbol', row.get('ticker', 'N/A'))
        
        # USE EXISTING DATA FROM DB (don't fetch!)
        current_price = float(row.get('current_price', 0) or 0)
        yesterday_price = float(row.get('yesterday_price', 0) or 0)
        
        # Calculate % change from DB data
        pct_change_str = "N/A"
        if yesterday_price > 0 and current_price > 0:
            pct_change = ((current_price - yesterday_price) / yesterday_price) * 100
            pct_change_str = f"{pct_change:+.2f}%"
        
        # ONLY fetch volume (not in DB)
        volume_str = "N/A"
        avg_vol_str = "N/A"
        
        if market_fetcher and market_hours:
            try:
                start_d, end_d = market_hours.trading_day_window()
                start_d = end_d - pd.Timedelta(days=90)  # 90 days for avg volume calc
                
                result = market_fetcher.fetch_price_data(ticker, start_d, end_d)
                if not result.df.empty and "Volume" in result.df.columns:
                    # Get volume from last day
                    if len(result.df) > 0:
                        volume = float(result.df["Volume"].iloc[-1])
                        if pd.notna(volume) and volume > 0:
                            volume_str = f"{int(volume/1000):,}K" if volume >= 1000 else f"{int(volume):,}"
                    
                    # Calculate 30-day average volume
                    vol_series = result.df["Volume"].dropna()
                    if not vol_series.empty:
                        avg_volume = vol_series.tail(30).mean()
                        if pd.notna(avg_volume) and avg_volume > 0:
                            avg_vol_str = f"{int(avg_volume/1000):,}K" if avg_volume >= 1000 else f"{int(avg_volume):,}"
            except Exception as e:
                logger.debug(f"[ai_context_builder.format_price_volume_table] Volume fetch failed for {ticker}: {e}")
        
        price_str = f"{current_price:,.2f}" if current_price > 0 else "N/A"
        lines.append(f"{ticker:<18} | {price_str:>9} | {pct_change_str:>11} | {volume_str:>7} | {avg_vol_str:>14}")
    
    return "\n".join(lines)


def format_fundamentals_table(positions_df: pd.DataFrame) -> str:
    """Format Company Fundamentals table for portfolio tickers.
    
    Uses securities data from positions_df FIRST (sector, industry, country, market_cap 
    already joined in DB). Only fetches P/E, Div%, 52W High/Low from yfinance.
    
    Args:
        positions_df: DataFrame with current positions (from get_current_positions)
                     Expected columns: ticker, securities (join with sector, industry, etc.)
        
    Returns:
        Formatted string with Company Fundamentals data
    """
    if positions_df.empty:
        return ""
    
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"[ai_context_builder.format_fundamentals_table] Processing {len(positions_df)} positions")
    
    lines = [
        "[ Company Fundamentals ]",
        "Ticker     | Sector               | Industry                  | Country  | Mkt Cap      | P/E    | Div %  | 52W High   | 52W Low",
        "-----------|---------------------|---------------------------|----------|--------------|--------|--------|------------|----------"
    ]
    
    # Try to import MarketDataFetcher ONLY for P/E, Div%, 52W High/Low (not in securities table)
    market_fetcher = None
    try:
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from config.settings import get_settings
        
        settings = get_settings()
        price_cache = PriceCache(settings=settings)
        market_fetcher = MarketDataFetcher(cache_instance=price_cache)
        logger.debug(f"[ai_context_builder.format_fundamentals_table] MarketDataFetcher ready for P/E, Div%, 52W")
    except Exception as e:
        logger.warning(f"[ai_context_builder.format_fundamentals_table] MarketDataFetcher not available: {e}")
    
    for idx, row in positions_df.iterrows():
        # pandas Series: use row['key'] or row.get('key') both work, but check for column existence
        ticker = row.get('ticker', row.get('symbol', 'N/A'))
        
        # 1. Try getting directly from row (if flat)
        sector = row.get('sector')
        industry = row.get('industry')
        country = row.get('country')
        
        # 2. If missing, try getting from securities join object
        market_cap = "N/A"
        securities = row.get('securities')
        
        if securities:
            # Handle both list and dict formats for joined data
            sec_data = {}
            if isinstance(securities, dict):
                sec_data = securities
            elif isinstance(securities, list) and len(securities) > 0:
                sec_data = securities[0] if isinstance(securities[0], dict) else {}
            
            # Fill in missing values from securities relation
            if not sector or str(sector) == 'N/A':
                sector = sec_data.get('sector')
            if not industry or str(industry) == 'N/A':
                industry = sec_data.get('industry')
            if not country or str(country) == 'N/A':
                country = sec_data.get('country')
                
            # Handle market cap
            raw_cap = sec_data.get('market_cap')
            if raw_cap and raw_cap != 'N/A':
                market_cap = _format_market_cap(raw_cap)
        
        # Final fallbacks and string conversion
        sector = str(sector) if sector and str(sector) != 'nan' else 'N/A'
        industry = str(industry) if industry and str(industry) != 'nan' else 'N/A'
        country = str(country) if country and str(country) != 'nan' else 'N/A'

        
        # SECOND: Only fetch P/E, Div%, 52W High/Low from yfinance (not in securities table)
        pe_ratio = "N/A"
        div_yield = "N/A"
        high_52w = "N/A"
        low_52w = "N/A"
        
        if market_fetcher:
            try:
                fundamentals = market_fetcher.fetch_fundamentals(ticker)
                if fundamentals:
                    # Only take P/E, Div%, 52W - sector/industry/country/market_cap already from DB
                    pe_ratio = fundamentals.get('trailingPE', 'N/A') or 'N/A'
                    div_yield = fundamentals.get('dividendYield', 'N/A') or 'N/A'
                    high_52w = fundamentals.get('fiftyTwoWeekHigh', 'N/A') or 'N/A'
                    low_52w = fundamentals.get('fiftyTwoWeekLow', 'N/A') or 'N/A'
            except Exception as e:
                logger.debug(f"[ai_context_builder.format_fundamentals_table] Fetch failed for {ticker}: {e}")
        
        # Check if ETF and provide better labeling
        is_etf = market_cap == 'ETF' or (isinstance(market_cap, str) and 'ETF' in str(market_cap).upper())
        if is_etf and sector == 'N/A':
            sector = 'ETF'
        if is_etf and industry == 'N/A':
            industry = 'ETF'
        
        # Truncate long values to fit columns
        sector_str = str(sector)[:20] if sector != "N/A" else "N/A"
        industry_str = str(industry)[:26] if industry != "N/A" else "N/A"
        country_str = str(country)[:8] if country != "N/A" else "N/A"
        market_cap_str = str(market_cap)[:12] if market_cap != "N/A" else "N/A"
        pe_str = str(pe_ratio)[:6] if pe_ratio != "N/A" else "N/A"
        div_str = str(div_yield)[:6] if div_yield != "N/A" else "N/A"
        high_str = str(high_52w)[:10] if high_52w != "N/A" else "N/A"
        low_str = str(low_52w)[:10] if low_52w != "N/A" else "N/A"
        
        lines.append(
            f"{ticker:<10} | {sector_str:<20} | {industry_str:<26} | {country_str:<8} | "
            f"{market_cap_str:<12} | {pe_str:<6} | {div_str:<6} | {high_str:<10} | {low_str}"
        )
    
    return "\n".join(lines)



def _format_market_cap(value) -> str:
    """Format market cap value into human-readable format (e.g., $1.2B, $500M).
    
    Args:
        value: Raw market cap value (int, float, or string)
        
    Returns:
        Formatted string like "$1.2B" or "$500M"
    """
    if value is None or value == 'N/A' or value == '':
        return 'N/A'
    
    # If already formatted (string starting with $), return as-is
    if isinstance(value, str):
        if value.startswith('$'):
            return value
        # Try to convert string to number
        try:
            value = float(value.replace(',', ''))
        except (ValueError, TypeError):
            return str(value)
    
    try:
        value = float(value)
        if value >= 1e12:
            return f"${value/1e12:.1f}T"
        elif value >= 1e9:
            return f"${value/1e9:.2f}B"
        elif value >= 1e6:
            return f"${value/1e6:.1f}M"
        elif value >= 1e3:
            return f"${value/1e3:.0f}K"
        else:
            return f"${value:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def format_thesis(thesis_data: Dict[str, Any]) -> str:
    """Format investment thesis data for LLM context.
    
    Args:
        thesis_data: Dictionary with thesis information
        
    Returns:
        Formatted string with thesis data
    """
    if not thesis_data:
        return "Investment Thesis: No thesis data available."
    
    lines = [f"Fund: {thesis_data.get('fund', 'Unknown')}", ""]
    
    title = thesis_data.get('title', '')
    if title:
        lines.append(f"Title: {title}")
    
    overview = thesis_data.get('overview', '')
    if overview:
        lines.append(f"\nOverview:\n{overview}")
    
    pillars = thesis_data.get('pillars', [])
    if pillars:
        lines.append("\nInvestment Pillars:")
        for pillar in pillars:
            name = pillar.get('name', '')
            allocation = pillar.get('allocation', '')
            thesis_text = pillar.get('thesis', '')
            
            lines.append(f"\n  {name} ({allocation}):")
            lines.append(f"    {thesis_text}")
    
    return "\n".join(lines)


def format_trades(trades_df: pd.DataFrame, limit: int = 100) -> str:
    """Format trades data for LLM context in compact table format.
    
    Token Optimization Notes:
    - Uses compact date format (MM-DD vs full timestamp)
    - Single line per trade with aligned columns
    - Removes redundant fund column if single fund
    - Quantities use 2 decimals max
    
    Args:
        trades_df: DataFrame with trade history
        limit: Maximum number of trades to include
        
    Returns:
        Formatted string with trades data
    """
    if trades_df.empty:
        return "Recent Trades: No trades found."
    
    # Limit number of trades
    df = trades_df.head(limit)
    
    lines = [
        f"Recent Trades ({len(df)} of {len(trades_df)} total):",
        "",
        "Date     | Action | Ticker    | Qty     | Price    | Total",
        "---------|--------|-----------|---------|----------|----------"
    ]
    
    for idx, row in df.iterrows():
        # Handle both 'timestamp' and 'date' columns from different data sources
        timestamp = row.get('timestamp') or row.get('date', '')
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        
        # Extract action from reason field (like dashboard does)
        action = 'BUY'  # Default to BUY
        reason = row.get('reason', '')
        if reason and isinstance(reason, str):
            reason_lower = reason.lower()
            if 'sell' in reason_lower or 'limit sell' in reason_lower or 'market sell' in reason_lower:
                action = 'SELL'
            elif 'drip' in reason_lower or 'dividend' in reason_lower:
                action = 'DRIP'
            # else: remains BUY (default)
        
        # Handle both 'quantity' and 'shares' columns
        quantity = row.get('quantity') or row.get('shares', 0)
        price = row.get('price', 0)
        currency = row.get('currency', 'CAD')
        # Calculate total_value if not present
        total_value = row.get('total_value')
        if not total_value and quantity and price:
            total_value = float(quantity) * float(price)
        
        # Compact date format (MM-DD-YY)
        date_str = "N/A"
        if timestamp:
            try:
                if hasattr(timestamp, 'strftime'):
                    date_str = timestamp.strftime('%m-%d-%y')
                elif isinstance(timestamp, str):
                    # Try to parse ISO format
                    date_str = timestamp[:10].replace('-', '/')[5:] if len(timestamp) >= 10 else timestamp[:8]
            except:
                date_str = str(timestamp)[:8]
        
        # Format with reduced precision
        qty_str = f"{float(quantity):.2f}" if quantity else "0"
        price_str = f"${float(price):.2f}" if price else "-"
        total_str = f"${float(total_value):,.0f}" if total_value else "-"
        action_str = action[:4].upper()  # BUY, SELL, or DRIP (truncated to 4 chars if needed)
        
        lines.append(f"{date_str:<8} | {action_str:<6} | {symbol:<9} | {qty_str:>7} | {price_str:>8} | {total_str:>9}")

    
    # Add summary statistics - infer from reason if available
    if 'reason' in df.columns:
        def is_sell(reason):
            if pd.isna(reason) or reason is None:
                return False
            reason_lower = str(reason).lower()
            return 'sell' in reason_lower or 'limit sell' in reason_lower or 'market sell' in reason_lower
        sells = df['reason'].apply(is_sell).sum()
        buys = len(df) - sells
        lines.append("")
        lines.append(f"Summary: {buys} buys, {sells} sells")
    
    return "\n".join(lines)


def format_performance_metrics(metrics: Dict[str, Any], portfolio_df: Optional[pd.DataFrame] = None) -> str:
    """Format performance metrics for LLM context.
    
    Args:
        metrics: Dictionary with performance metrics
        portfolio_df: Optional DataFrame with portfolio value over time
        
    Returns:
        Formatted string with metrics
    """
    if not metrics:
        return "Performance Metrics: No metrics available."
    
    lines = ["Performance Metrics:", ""]
    
    # Key metrics
    if 'total_return_pct' in metrics:
        lines.append(f"Total Return: {metrics['total_return_pct']:.2f}%")
    
    if 'current_value' in metrics:
        lines.append(f"Current Value: ${metrics['current_value']:,.2f}")
    
    if 'total_invested' in metrics:
        lines.append(f"Total Invested: ${metrics['total_invested']:,.2f}")
    
    if 'peak_gain_pct' in metrics and 'peak_date' in metrics:
        lines.append(f"Peak Gain: {metrics['peak_gain_pct']:.2f}% (on {metrics['peak_date']})")
    
    if 'max_drawdown_pct' in metrics and 'max_drawdown_date' in metrics:
        lines.append(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}% (on {metrics['max_drawdown_date']})")

    return "\n".join(lines)


def format_cash_balances(cash: Dict[str, float]) -> str:
    """Format cash balances for LLM context.
    
    Args:
        cash: Dictionary mapping currency codes to amounts
        
    Returns:
        Formatted string with cash balances
    """
    if not cash:
        return "Cash Balances: No cash positions."
    
    lines = ["Cash Balances:", ""]
    
    total_cad_equivalent = 0.0
    for currency, amount in cash.items():
        if amount > 0:
            lines.append(f"  {currency}: ${amount:,.2f}")
            # Note: Would need exchange rates for accurate CAD equivalent
            total_cad_equivalent += amount  # Simplified
    
    if len(cash) > 1:
        lines.append(f"\nTotal (simplified): ${total_cad_equivalent:,.2f}")
    
    return "\n".join(lines)


def format_investor_allocations(allocations: Dict[str, Any]) -> str:
    """Format investor allocations for LLM context.
    
    Args:
        allocations: Dictionary with investor allocation data
        
    Returns:
        Formatted string with investor allocations
    """
    if not allocations:
        return "Investor Allocations: No allocation data available."
    
    lines = ["Investor Allocations:", ""]
    
    # Handle different allocation formats
    if isinstance(allocations, dict):
        for investor, data in allocations.items():
            if isinstance(data, dict):
                value = data.get('value', 0)
                pct = data.get('percentage', 0)
                lines.append(f"  {investor}: ${value:,.2f} ({pct:.2f}%)")
            else:
                lines.append(f"  {investor}: {data}")
    
    return "\n".join(lines)


def format_sector_allocation(sector_data: Dict[str, float]) -> str:
    """Format sector allocation for LLM context.
    
    Args:
        sector_data: Dictionary mapping sector names to allocation percentages
        
    Returns:
        Formatted string with sector allocation
    """
    if not sector_data:
        return "Sector Allocation: No sector data available."
    
    lines = ["Sector Allocation:", ""]
    
    # Sort by percentage descending
    sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1], reverse=True)
    
    for sector, pct in sorted_sectors:
        lines.append(f"  {sector}: {pct:.2f}%")
    
    return "\n".join(lines)


def build_full_context(context_items: List[Any], fund: Optional[str] = None) -> str:
    """Build full context string from multiple context items.
    
    Args:
        context_items: List of context items (DataFrames, dicts, etc.)
        fund: Optional fund name
        
    Returns:
        Combined formatted context string
    """
    sections = []
    
    for item in context_items:
        if isinstance(item, pd.DataFrame):
            # Try to determine type from DataFrame
            if 'symbol' in item.columns and 'quantity' in item.columns:
                sections.append(format_holdings(item, fund or "Unknown"))
            elif 'reason' in item.columns or 'timestamp' in item.columns:
                sections.append(format_trades(item))
        elif isinstance(item, dict):
            if 'pillars' in item or 'thesis' in item or 'overview' in item:
                sections.append(format_thesis(item))
            elif 'total_return_pct' in item or 'current_value' in item:
                sections.append(format_performance_metrics(item))
            elif all(isinstance(k, str) and isinstance(v, (int, float)) for k, v in item.items()):
                # Could be cash balances or sector allocation
                if any('USD' in k or 'CAD' in k for k in item.keys()):
                    sections.append(format_cash_balances(item))
                else:
                    sections.append(format_sector_allocation(item))
    
    return "\n\n---\n\n".join(sections)

