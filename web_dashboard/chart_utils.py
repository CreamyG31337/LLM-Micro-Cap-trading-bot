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
    """Add light gray shading for weekends (Friday close to Monday open).
    
    This helps users understand when markets were closed.
    Shades from Friday 16:00 (market close) to Monday 00:00.
    """
    # Normalize to date-only (midnight) to avoid time component misalignment
    start_date_only = start_date.date() if isinstance(start_date, datetime) else start_date
    end_date_only = end_date.date() if isinstance(end_date, datetime) else end_date
    
    # Handle case where chart starts on weekend (Saturday or Sunday)
    # If start date is Saturday (5) or Sunday (6), shade from previous Friday
    start_weekday = start_date_only.weekday()
    if start_weekday == 5:  # Saturday
        # Find previous Friday
        days_back = 1  # Saturday to Friday
        prev_friday = start_date_only - timedelta(days=days_back)
        friday_close = datetime.combine(prev_friday, datetime.min.time()) + timedelta(hours=16)
        monday = datetime.combine(start_date_only + timedelta(days=2), datetime.min.time())  # Monday 00:00
        
        fig.add_vrect(
            x0=friday_close,
            x1=monday,
            fillcolor="rgba(128, 128, 128, 0.1)",
            layer="below",
            line_width=0,
        )
    elif start_weekday == 6:  # Sunday
        # Find previous Friday
        days_back = 2  # Sunday to Friday
        prev_friday = start_date_only - timedelta(days=days_back)
        friday_close = datetime.combine(prev_friday, datetime.min.time()) + timedelta(hours=16)
        monday = datetime.combine(start_date_only + timedelta(days=1), datetime.min.time())  # Monday 00:00
        
        fig.add_vrect(
            x0=friday_close,
            x1=monday,
            fillcolor="rgba(128, 128, 128, 0.1)",
            layer="below",
            line_width=0,
        )
    
    # Iterate by date (not datetime) to ensure proper alignment
    current_date = start_date_only
    while current_date <= end_date_only:
        # Friday = 4 (start weekend shading at market close)
        if current_date.weekday() == 4:  # Friday
            # Shade from Friday 16:00 (market close) to Monday 00:00
            friday_close = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=16)
            monday = datetime.combine(current_date + timedelta(days=3), datetime.min.time())  # Monday 00:00
            
            fig.add_vrect(
                x0=friday_close,
                x1=monday,
                fillcolor="rgba(128, 128, 128, 0.1)",
                layer="below",
                line_width=0,
            )
            # Move to next week
            current_date += timedelta(days=7)
        else:
            current_date += timedelta(days=1)


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
    show_weekend_shading: bool = True,
    use_solid_lines: bool = False
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
                # Filter to portfolio date range - ensure datetime types match
                bench_data = bench_data[
                    (bench_data['Date'] >= pd.Timestamp(start_date)) & 
                    (bench_data['Date'] <= pd.Timestamp(end_date))
                ]
                
                if not bench_data.empty:
                    # Calculate benchmark return for label
                    bench_return = bench_data['normalized'].iloc[-1] - 100
                    
                    # Use solid or dashed lines based on preference
                    line_style = {} if use_solid_lines else {'dash': 'dash'}
                    
                    fig.add_trace(go.Scatter(
                        x=bench_data['Date'],
                        y=bench_data['normalized'],
                        mode='lines',
                        name=f"{config['name']} ({bench_return:+.2f}%)",
                        line=dict(color=config['color'], width=3, **line_style),
                        opacity=0.8,
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
    # Check for either pnl or unrealized_pnl column
    pnl_col = None
    if 'unrealized_pnl' in positions_df.columns:
        pnl_col = 'unrealized_pnl'
    elif 'pnl' in positions_df.columns:
        pnl_col = 'pnl'
    
    if positions_df.empty or pnl_col is None:
        fig = go.Figure()
        fig.add_annotation(
            text="No P&L data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Sort by P&L
    df = positions_df.sort_values(pnl_col, ascending=False).copy()
    
    # Limit to top/bottom 20 for readability
    if len(df) > 40:
        top = df.head(20)
        bottom = df.tail(20)
        df = pd.concat([top, bottom]).sort_values(pnl_col, ascending=False)
    
    # Color bars based on positive/negative
    colors = ['#10b981' if pnl >= 0 else '#ef4444' for pnl in df[pnl_col]]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=df[pnl_col],
        marker_color=colors,
        text=[f"${pnl:,.2f}" for pnl in df[pnl_col]],
        textposition='outside'
    ))
    
    title = "P&L by Position"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Ticker",
        yaxis_title="Unrealized P&L ($)",
        template='plotly_white',
        height=500,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_currency_exposure_chart(positions_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a pie chart showing USD vs CAD stock holdings exposure"""
    if positions_df.empty or 'currency' not in positions_df.columns or 'market_value' not in positions_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No currency data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Group by currency and sum market values
    currency_totals = positions_df.groupby('currency')['market_value'].sum().reset_index()
    currency_totals = currency_totals.sort_values('market_value', ascending=False)
    
    # Calculate percentages
    total_value = currency_totals['market_value'].sum()
    currency_totals['percentage'] = (currency_totals['market_value'] / total_value * 100).round(1)
    
    # Color scheme: Blue for USD, Red for CAD
    colors = []
    for curr in currency_totals['currency']:
        if curr == 'USD':
            colors.append('#3b82f6')  # Blue
        elif curr == 'CAD':
            colors.append('#ef4444')  # Red
        else:
            colors.append('#9ca3af')  # Gray for others
    
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=currency_totals['currency'],
        values=currency_totals['market_value'],
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>%{percent}<extra></extra>'
    ))
    
    title = "Currency Exposure (Stock Holdings)"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        template='plotly_white',
        height=400,
        showlegend=True
    )
    
    return fig


def create_sector_allocation_chart(positions_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a pie chart showing sector allocation of portfolio holdings"""
    if positions_df.empty or 'ticker' not in positions_df.columns or 'market_value' not in positions_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No position data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Fetch sector info for each ticker using yfinance
    sector_data = []
    for idx, row in positions_df.iterrows():
        ticker = row['ticker']
        market_value = row['market_value']
        
        try:
            # Fetch stock info from yfinance
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get sector (will be None for ETFs or if data unavailable)
            sector = info.get('sector', 'Unknown')
            if not sector or sector == '':
                sector = 'Other/ETF'
            
            sector_data.append({
                'ticker': ticker,
                'sector': sector,
                'market_value': market_value
            })
        except Exception as e:
            # If we can't fetch data, categorize as Unknown
            sector_data.append({
                'ticker': ticker,
                'sector': 'Unknown',
                'market_value': market_value
            })
    
    if not sector_data:
        fig = go.Figure()
        fig.add_annotation(
            text="Unable to fetch sector data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Aggregate by sector
    sector_df = pd.DataFrame(sector_data)
    sector_totals = sector_df.groupby('sector')['market_value'].sum().reset_index()
    sector_totals = sector_totals.sort_values('market_value', ascending=False)
    
    # Color palette for sectors
    sector_colors = {
        'Technology': '#3b82f6',
        'Financial Services': '#10b981',
        'Healthcare': '#ef4444',
        'Consumer Cyclical': '#f59e0b',
        'Industrials': '#8b5cf6',
        'Energy': '#f97316',
        'Basic Materials': '#06b6d4',
        'Consumer Defensive': '#84cc16',
        'Real Estate': '#ec4899',
        'Communication Services': '#6366f1',
        'Utilities': '#14b8a6',
        'Other/ETF': '#9ca3af',
        'Unknown': '#6b7280'
    }
    
    colors = [sector_colors.get(sector, '#9ca3af') for sector in sector_totals['sector']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=sector_totals['sector'],
        values=sector_totals['market_value'],
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>%{percent}<extra></extra>'
    ))
    
    title = "Sector Allocation"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        template='plotly_white',
        height=500,
        showlegend=True
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
def create_individual_holdings_chart(
    holdings_df: pd.DataFrame,
    fund_name: Optional[str] = None,
    show_benchmarks: Optional[List[str]] = None,
    show_weekend_shading: bool = True,
    use_solid_lines: bool = False
) -> go.Figure:
    """Create a chart showing individual stock performance vs benchmarks.
    
    Args:
        holdings_df: DataFrame with columns: ticker, date, performance_index
        fund_name: Optional fund name for title
        show_benchmarks: List of benchmark keys to display
        show_weekend_shading: Add weekend shading
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if holdings_df.empty:
        fig.add_annotation(
            text="No holdings data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Get date range
    start_date = pd.to_datetime(holdings_df['date']).min()
    end_date = pd.to_datetime(holdings_df['date']).max()
    
    # Color palette for stocks
    stock_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
    ]
    
    # Plot each stock
    tickers = holdings_df['ticker'].unique()
    for idx, ticker in enumerate(sorted(tickers)):
        ticker_data = holdings_df[holdings_df['ticker'] == ticker].copy()
        ticker_data = ticker_data.sort_values('date')
        
        if len(ticker_data) < 2:
            continue  # Skip if insufficient data
        
        # Calculate return for label
        final_perf = ticker_data['performance_index'].iloc[-1]
        stock_return = final_perf - 100
        
        color = stock_colors[idx % len(stock_colors)]
        
        fig.add_trace(go.Scatter(
            x=ticker_data['date'],
            y=ticker_data['performance_index'],
            mode='lines',
            name=f"{ticker} ({stock_return:+.2f}%)",
            line=dict(color=color, width=1.5),
            hovertemplate=f'{ticker}<br>%{{x|%Y-%m-%d}}<br>%{{y:,.2f}}<extra></extra>'
        ))
    
    # Add benchmarks
    if show_benchmarks:
        for bench_key in show_benchmarks:
            if bench_key not in BENCHMARK_CONFIG:
                continue
                
            config = BENCHMARK_CONFIG[bench_key]
            bench_data = _fetch_benchmark_data(config['ticker'], start_date, end_date)
            
            if bench_data is not None and not bench_data.empty:
                # Filter to portfolio date range - strip timezone for comparison
                start_naive = pd.Timestamp(start_date).tz_localize(None) if hasattr(start_date, 'tzinfo') and start_date.tzinfo else pd.Timestamp(start_date)
                end_naive = pd.Timestamp(end_date).tz_localize(None) if hasattr(end_date, 'tzinfo') and end_date.tzinfo else pd.Timestamp(end_date)
                
                bench_data = bench_data[
                    (bench_data['Date'] >= start_naive) & 
                    (bench_data['Date'] <= end_naive)
                ]
                
                if not bench_data.empty:
                    bench_return = bench_data['normalized'].iloc[-1] - 100
                    
                    # Use solid or dashed lines based on preference
                    line_style = {} if use_solid_lines else {'dash': 'dash'}
                    
                    fig.add_trace(go.Scatter(
                        x=bench_data['Date'],
                        y=bench_data['normalized'],
                        mode='lines',
                        name=f"{config['name']} ({bench_return:+.2f}%)",
                        line=dict(color=config['color'], width=3, **line_style),
                        opacity=0.8,
                        hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>'
                    ))
    
    # Add weekend shading
    if show_weekend_shading:
        _add_weekend_shading(fig, start_date, end_date)
    
    # Add baseline reference
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="gray",
        opacity=0.5,
        annotation_text="Baseline (0%)",
        annotation_position="right"
    )
    
    # Layout
    title = f"Individual Stock Performance"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title="Date",
        yaxis_title="Performance Index (Baseline 100)",
        hovermode='x unified',
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
    )
    
    return fig


def create_investor_allocation_chart(investors_df: pd.DataFrame, fund_name: Optional[str] = None) -> go.Figure:
    """Create a pie chart showing investor allocation by contribution amount
    
    Args:
        investors_df: DataFrame with columns: contributor_display, net_contribution, ownership_pct
                     contributor_display is already privacy-masked (Investor 1, Investor 2, etc.)
        fund_name: Optional fund name for title
    
    Returns:
        Plotly Figure object
    """
    if investors_df.empty or 'contributor_display' not in investors_df.columns or 'net_contribution' not in investors_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No investor data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Color palette for investors (varied colors)
    investor_colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#06b6d4', '#84cc16', '#ec4899', '#6366f1', '#14b8a6',
        '#f97316', '#a855f7', '#22c55e', '#eab308', '#f43f5e'
    ]
    
    # Assign colors cycling through palette
    colors = [investor_colors[i % len(investor_colors)] for i in range(len(investors_df))]
    
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=investors_df['contributor_display'],
        values=investors_df['net_contribution'],
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Investment: $%{value:,.2f}<br>%{percent}<extra></extra>'
    ))
    
    title = "Investor Allocation"
    if fund_name:
        title += f" - {fund_name}"
    
    fig.update_layout(
        title=title,
        template='plotly_white',
        height=500,
        showlegend=True
    )
    
    return fig
