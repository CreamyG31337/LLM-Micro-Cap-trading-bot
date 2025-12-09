#!/usr/bin/env python3
"""
Chart utilities for creating performance graphs
"""

import pandas as pd
import plotly.graph_objs as go
from typing import Optional, List, Dict
from datetime import datetime


def create_portfolio_value_chart(portfolio_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a line chart showing portfolio value over time"""
    if portfolio_df.empty or 'date' not in portfolio_df.columns:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Sort by date
    df = portfolio_df.sort_values('date').copy()
    
    # Create the chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['value'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))
    
    title = f"Portfolio Value Over Time"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_performance_by_fund_chart(funds_data: Dict[str, float]) -> go.Figure:
    """Create a bar chart showing performance by fund"""
    if not funds_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    funds = list(funds_data.keys())
    values = list(funds_data.values())
    
    # Color bars based on positive/negative
    colors = ['#10b981' if v >= 0 else '#ef4444' for v in values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=funds,
        y=values,
        marker_color=colors,
        text=[f"${v:,.2f}" for v in values],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Performance by Fund",
        xaxis_title="Fund",
        yaxis_title="Value ($)",
        template='plotly_white',
        height=400
    )
    
    return fig


def create_pnl_chart(positions_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a bar chart showing P&L by position"""
    if positions_df.empty or 'pnl' not in positions_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Sort by P&L
    df = positions_df.sort_values('pnl', ascending=False).copy()
    
    # Limit to top/bottom 20 for readability
    if len(df) > 40:
        top = df.head(20)
        bottom = df.tail(20)
        df = pd.concat([top, bottom]).sort_values('pnl', ascending=False)
    
    # Color bars based on positive/negative
    colors = ['#10b981' if pnl >= 0 else '#ef4444' for pnl in df['pnl']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=df['pnl'],
        marker_color=colors,
        text=[f"${pnl:,.2f}" for pnl in df['pnl']],
        textposition='outside'
    ))
    
    title = "P&L by Position"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Ticker",
        yaxis_title="P&L ($)",
        template='plotly_white',
        height=500,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_trades_timeline_chart(trades_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a timeline chart showing trades over time"""
    if trades_df.empty or 'date' not in trades_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Group by date and type
    df = trades_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['trade_value'] = df['shares'] * df['price']
    
    # Separate buys and sells
    buys = df[df['type'].str.upper() == 'BUY'].groupby('date')['trade_value'].sum()
    sells = df[df['type'].str.upper() == 'SELL'].groupby('date')['trade_value'].sum()
    
    fig = go.Figure()
    
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys.index,
            y=buys.values,
            mode='markers',
            name='Buys',
            marker=dict(color='#10b981', size=8, symbol='triangle-up')
        ))
    
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells.index,
            y=sells.values,
            mode='markers',
            name='Sells',
            marker=dict(color='#ef4444', size=8, symbol='triangle-down')
        ))
    
    title = "Trades Timeline"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Trade Value ($)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


