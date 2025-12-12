#!/usr/bin/env python3
"""
Chart utilities for creating performance graphs with Plotly.

Features:
- Portfolio value and normalized performance charts
- Benchmark comparison (S&P 500, QQQ, Russell 2000, VTI)
- Weekend shading to highlight market closures
- P&L by position charts
- Trade timeline charts
"""

import pandas as pd
import plotly.graph_objs as go
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import yfinance as yf


# Benchmark configuration
BENCHMARK_CONFIG = {
    'sp500': {'ticker': '^GSPC', 'name': 'S&P 500', 'color': '#ff7f0e'},
    'qqq': {'ticker': 'QQQ', 'name': 'Nasdaq-100 (QQQ)', 'color': '#2ca02c'},
    'russell2000': {'ticker': '^RUT', 'name': 'Russell 2000', 'color': '#d62728'},
    'vti': {'ticker': 'VTI', 'name': 'Total Market (VTI)', 'color': '#9467bd'}
}


def _add_weekend_shading(fig: go.Figure, start_date: datetime, end_date: datetime) -> None:
    """Add light gray shading for weekends (Saturday-Sunday).
    
    This helps users understand when markets were closed.
    """
    current = start_date
    while current <= end_date:
        # Saturday = 5, Sunday = 6
        if current.weekday() == 5:  # Saturday
            # Shade from Saturday 00:00 to Sunday 23:59
            saturday = current
            sunday = current + timedelta(days=1)
            
            fig.add_vrect(
                x0=saturday,
                x1=sunday + timedelta(hours=23, minutes=59),
                fillcolor="rgba(128, 128, 128, 0.1)",
                layer="below",
                line_width=0,
            )
        current += timedelta(days=1)


def _fetch_benchmark_data(ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
    """Fetch benchmark data from Yahoo Finance and normalize to 100 baseline."""
    try:
        # Add buffer days to ensure we get data
        buffer_start = start_date - timedelta(days=5)
        buffer_end = end_date + timedelta(days=2)
        
        data = yf.download(ticker, start=buffer_start, end=buffer_end, progress=False, auto_adjust=False)
        
        if data.empty:
            return None
        
        data = data.reset_index()
        
        # Handle MultiIndex columns from yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Find the baseline close price at or near portfolio start date
        data['Date'] = pd.to_datetime(data['Date'])
        
        # Get close on start date (or nearest previous trading day)
        baseline_data = data[data['Date'].dt.date <= start_date.date()]
        if not baseline_data.empty:
            baseline_close = baseline_data['Close'].iloc[-1]
        else:
            baseline_close = data['Close'].iloc[0]
        
        # Normalize to 100 baseline
        data['normalized'] = (data['Close'] / baseline_close) * 100
        
        return data[['Date', 'Close', 'normalized']]
        
    except Exception as e:
        print(f"Error fetching benchmark {ticker}: {e}")
        return None


def create_portfolio_value_chart(
    portfolio_df: pd.DataFrame, 
    fund_name: Optional[str] = None, 
    show_normalized: bool = False,
    show_benchmarks: Optional[List[str]] = None,
    show_weekend_shading: bool = True
) -> go.Figure:
    """Create a line chart showing portfolio value/performance over time.
    
    Args:
        portfolio_df: DataFrame with portfolio data (date, value, performance_index, etc)
        fund_name: Optional fund name for title
        show_normalized: If True, shows performance index (baseline 100) instead of raw value
        show_benchmarks: List of benchmark keys to display (e.g., ['sp500', 'qqq'])
        show_weekend_shading: If True, adds gray shading for weekends
    """
    if portfolio_df.empty or 'date' not in portfolio_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Sort by date
    df = portfolio_df.sort_values('date').copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Create the chart
    fig = go.Figure()
    
    # Determine which column to use for y-axis
    if show_normalized and 'performance_index' in df.columns:
        y_col = 'performance_index'
        y_label = "Performance Index (Baseline 100)"
        chart_name = "Portfolio"
        # Add reference line at 100
        fig.add_hline(y=100, line_dash="dash", line_color="gray", 
                      annotation_text="Baseline", annotation_position="right")
    elif 'value' in df.columns:
        y_col = 'value'
        y_label = "Portfolio Value ($)"
        chart_name = "Portfolio Value"
    elif 'total_value' in df.columns:
        y_col = 'total_value'
        y_label = "Portfolio Value ($)"
        chart_name = "Portfolio Value"
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="No value data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Calculate return percentage for label
    if len(df) > 1 and 'performance_pct' in df.columns:
        current_return = df['performance_pct'].iloc[-1]
        label_suffix = f" ({current_return:+.2f}%)"
    else:
        label_suffix = ""
    
    # Add portfolio trace
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df[y_col],
        mode='lines+markers',
        name=f'{chart_name}{label_suffix}',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=4),
        hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>'
    ))
    
    # Add benchmarks if requested (only for normalized view)
    if show_normalized and show_benchmarks and 'performance_index' in df.columns:
        start_date = df['date'].min()
        end_date = df['date'].max()
        
        for bench_key in show_benchmarks:
            if bench_key not in BENCHMARK_CONFIG:
                continue
                
            config = BENCHMARK_CONFIG[bench_key]
            bench_data = _fetch_benchmark_data(config['ticker'], start_date, end_date)
            
            if bench_data is not None and not bench_data.empty:
                # Filter to portfolio date range
                bench_data = bench_data[
                    (bench_data['Date'] >= start_date) & 
                    (bench_data['Date'] <= end_date)
                ]
                
                if not bench_data.empty:
                    # Calculate benchmark return for label
                    bench_return = bench_data['normalized'].iloc[-1] - 100
                    
                    fig.add_trace(go.Scatter(
                        x=bench_data['Date'],
                        y=bench_data['normalized'],
                        mode='lines',
                        name=f"{config['name']} ({bench_return:+.2f}%)",
                        line=dict(color=config['color'], width=2, dash='dash'),
                        hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>'
                    ))
    
    # Add weekend shading
    if show_weekend_shading and len(df) > 1:
        _add_weekend_shading(fig, df['date'].min(), df['date'].max())
    
    # Title
    title = f"Portfolio {'Performance' if show_normalized else 'Value'} Over Time"
    if fund_name:
        title += f" - {fund_name}"
    if show_benchmarks and show_normalized:
        title += " vs Benchmarks"
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        hovermode='x unified',
        template='plotly_white',
        height=500,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
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


def create_trades_timeline_chart(trades_df: pd.DataFrame, fund_name: Optional[str] = None,
                                  show_weekend_shading: bool = True) -> go.Figure:
    """Create a timeline chart showing trades over time"""
    required_cols = ['date', 'action', 'shares', 'price']
    if trades_df.empty or not all(col in trades_df.columns for col in required_cols):
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
    buys = df[df['action'].str.upper() == 'BUY'].groupby('date')['trade_value'].sum()
    sells = df[df['action'].str.upper() == 'SELL'].groupby('date')['trade_value'].sum()
    
    fig = go.Figure()
    
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys.index,
            y=buys.values,
            mode='markers',
            name='Buys',
            marker=dict(color='#10b981', size=10, symbol='triangle-up')
        ))
    
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells.index,
            y=sells.values,
            mode='markers',
            name='Sells',
            marker=dict(color='#ef4444', size=10, symbol='triangle-down')
        ))
    
    # Add weekend shading
    if show_weekend_shading and len(df) > 0:
        _add_weekend_shading(fig, df['date'].min(), df['date'].max())
    
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


def get_available_benchmarks() -> Dict[str, str]:
    """Return available benchmark options for UI."""
    return {key: config['name'] for key, config in BENCHMARK_CONFIG.items()}
