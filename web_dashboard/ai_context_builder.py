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
    """Format holdings/positions data for LLM context.
    
    Args:
        positions_df: DataFrame with current positions
        fund: Fund name
        
    Returns:
        Formatted string with holdings data
    """
    if positions_df.empty:
        return f"Fund: {fund}\nHoldings: No current positions."
    
    # Select relevant columns
    cols_to_include = ['symbol', 'quantity', 'currency', 'cost_basis', 'market_value', 'unrealized_pnl', 'unrealized_pnl_pct']
    available_cols = [col for col in cols_to_include if col in positions_df.columns]
    
    # Format as structured text
    lines = [f"Fund: {fund}", f"Current Holdings ({len(positions_df)} positions):", ""]
    
    for idx, row in positions_df.iterrows():
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        quantity = row.get('quantity', row.get('shares', 0))
        currency = row.get('currency', 'CAD')
        cost_basis = row.get('cost_basis', 0)
        market_value = row.get('market_value', 0)
        pnl = row.get('unrealized_pnl', 0)
        pnl_pct = row.get('unrealized_pnl_pct', row.get('return_pct', 0))
        
        lines.append(f"  {symbol}:")
        lines.append(f"    Quantity: {quantity}")
        lines.append(f"    Cost Basis: {currency} ${cost_basis:,.2f}")
        lines.append(f"    Market Value: {currency} ${market_value:,.2f}")
        lines.append(f"    Unrealized P&L: {currency} ${pnl:,.2f} ({pnl_pct:+.2f}%)")
        lines.append("")
    
    # Add summary
    if 'market_value' in positions_df.columns:
        total_value = positions_df['market_value'].sum()
        lines.append(f"Total Portfolio Value: ${total_value:,.2f}")
    
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
    """Format trades data for LLM context.
    
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
    
    lines = [f"Recent Trades (showing {len(df)} of {len(trades_df)} total):", ""]
    
    # Select relevant columns
    cols_to_include = ['timestamp', 'symbol', 'action', 'quantity', 'price', 'currency', 'total_value', 'fund']
    available_cols = [col for col in cols_to_include if col in df.columns]
    
    for idx, row in df.iterrows():
        timestamp = row.get('timestamp', '')
        symbol = row.get('symbol', row.get('ticker', 'N/A'))
        action = row.get('action', 'N/A')
        quantity = row.get('quantity', 0)
        price = row.get('price', 0)
        currency = row.get('currency', 'CAD')
        total_value = row.get('total_value', 0)
        fund = row.get('fund', '')
        
        lines.append(f"  {timestamp} - {action.upper()} {quantity} {symbol} @ {currency} ${price:.2f} (Total: {currency} ${total_value:,.2f})")
        if fund:
            lines[-1] += f" [Fund: {fund}]"
    
    # Add summary statistics
    if 'action' in df.columns:
        buys = len(df[df['action'].str.upper() == 'BUY'])
        sells = len(df[df['action'].str.upper() == 'SELL'])
        lines.append(f"\nSummary: {buys} buys, {sells} sells")
    
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

