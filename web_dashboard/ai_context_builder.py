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


def format_holdings(positions_df: pd.DataFrame, fund: str) -> str:
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
        
    Returns:
        Formatted string with holdings data in compact table format
    """
    if positions_df.empty:
        return f"Fund: {fund}\nHoldings: No current positions."
    
    # Header with new columns
    lines = [
        f"Fund: {fund}",
        f"Holdings ({len(positions_df)} positions):",
        "",
        # Enriched header - includes Daily P&L and Sector
        "Ticker    | Sector          | Qty     | Price    | Mkt Value  | Daily P&L | Total P&L | Return",
        "----------|-----------------|---------|----------|------------|-----------|-----------|-------"
    ]
    
    total_cost = 0.0
    total_value = 0.0
    total_pnl = 0.0
    total_daily_pnl = 0.0
    
    for idx, row in positions_df.iterrows():
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        quantity = row.get('quantity', row.get('shares', 0))
        currency = row.get('currency', 'CAD')
        cost_basis = row.get('cost_basis', 0)
        market_value = row.get('market_value', 0)
        pnl = row.get('unrealized_pnl', 0)
        pnl_pct = row.get('unrealized_pnl_pct', row.get('return_pct', 0))
        current_price = row.get('current_price', row.get('price', 0))
        
        # Get daily P&L from view (may be None/null)
        daily_pnl = row.get('daily_pnl', 0)
        daily_pnl_pct = row.get('daily_pnl_pct', 0)
        
        # Get sector from securities join (nested dict)
        sector = "N/A"
        securities = row.get('securities')
        if securities:
            if isinstance(securities, dict):
                sector = securities.get('sector', 'N/A') or 'N/A'
            elif isinstance(securities, list) and len(securities) > 0:
                # If it's a list, take first item
                sector = securities[0].get('sector', 'N/A') if isinstance(securities[0], dict) else 'N/A'
        
        # Track totals
        total_cost += float(cost_basis) if cost_basis else 0
        total_value += float(market_value) if market_value else 0
        total_pnl += float(pnl) if pnl else 0
        total_daily_pnl += float(daily_pnl) if daily_pnl else 0
        
        # Format with reduced precision for token efficiency
        qty_str = f"{float(quantity):.2f}" if quantity else "0.00"
        price_str = f"${float(current_price):.2f}" if current_price else "-"
        value_str = f"${float(market_value):,.0f}" if market_value else "-"
        pnl_str = f"{'+' if float(pnl) >= 0 else ''}{float(pnl):,.0f}" if pnl else "0"
        pct_str = f"{float(pnl_pct):+.1f}%" if pnl_pct else "0.0%"
        
        # Format daily P&L (may be 0 or None)
        if daily_pnl and daily_pnl != 0:
            daily_str = f"{'+' if float(daily_pnl) >= 0 else ''}{float(daily_pnl):,.0f}"
        else:
            daily_str = "-"
        
        # Truncate sector to fit column width
        sector_str = str(sector)[:15] if sector != "N/A" else "N/A"
        
        # Single line per holding (token-efficient)
        lines.append(f"{symbol:<9} | {sector_str:<15} | {qty_str:>7} | {price_str:>8} | {value_str:>10} | {daily_str:>9} | {pnl_str:>9} | {pct_str:>6}")
    
    # Summary row
    if total_value > 0:
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        daily_summary = f"{'+' if total_daily_pnl >= 0 else ''}{total_daily_pnl:>8,.0f}" if total_daily_pnl != 0 else "-"
        lines.append("----------|-----------------|---------|----------|------------|-----------|-----------|-------")
        lines.append(f"{'TOTAL':<9} | {'':15} |         | {'':8} | ${total_value:>9,.0f} | {daily_summary:>9} | {'+' if total_pnl >= 0 else ''}{total_pnl:>8,.0f} | {total_pnl_pct:+.1f}%")
    
    return "\n".join(lines)


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
        timestamp = row.get('timestamp', '')
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        action = row.get('action', 'N/A')
        quantity = row.get('quantity', 0)
        price = row.get('price', 0)
        currency = row.get('currency', 'CAD')
        total_value = row.get('total_value', 0)
        
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
        action_str = action.upper()[:4] if action else "-"  # BUY or SELL
        
        lines.append(f"{date_str:<8} | {action_str:<6} | {symbol:<9} | {qty_str:>7} | {price_str:>8} | {total_str:>9}")
    
    # Add summary statistics
    if 'action' in df.columns:
        buys = len(df[df['action'].str.upper() == 'BUY'])
        sells = len(df[df['action'].str.upper() == 'SELL'])
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
    
    # Portfolio value over time summary
    if portfolio_df is not None and not portfolio_df.empty:
        if 'date' in portfolio_df.columns and 'value' in portfolio_df.columns:
            lines.append("\nPortfolio Value Over Time:")
            lines.append(f"  Start Date: {portfolio_df['date'].min()}")
            lines.append(f"  End Date: {portfolio_df['date'].max()}")
            lines.append(f"  Start Value: ${portfolio_df['value'].iloc[0]:,.2f}")
            lines.append(f"  End Value: ${portfolio_df['value'].iloc[-1]:,.2f}")
            
            if len(portfolio_df) > 1:
                growth = ((portfolio_df['value'].iloc[-1] - portfolio_df['value'].iloc[0]) / portfolio_df['value'].iloc[0]) * 100
                lines.append(f"  Period Growth: {growth:+.2f}%")
    
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
            elif 'action' in item.columns or 'timestamp' in item.columns:
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

