#!/usr/bin/env python3
"""
Portfolio Performance Web Dashboard
A Flask web app to display trading bot portfolio performance using Supabase
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import plotly.graph_objs as go
import plotly.utils
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Import Supabase client
try:
    from supabase_client import SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    logger.warning("Supabase client not available. Install with: pip install supabase")
    SUPABASE_AVAILABLE = False

def get_supabase_client() -> Optional[SupabaseClient]:
    """Get Supabase client instance"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        return SupabaseClient()
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def load_portfolio_data() -> Dict:
    """Load and process portfolio data from Supabase"""
    try:
        client = get_supabase_client()
        if not client:
            logger.warning("Supabase not available, returning empty data")
            return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}}
        
        # Get current positions
        positions = client.get_current_positions()
        portfolio_df = pd.DataFrame(positions) if positions else pd.DataFrame()
        
        # Get recent trades
        trades = client.get_trade_log(limit=1000)
        trade_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        # Get cash balances
        cash_balances = client.get_cash_balances()
        
        return {
            "portfolio": portfolio_df,
            "trades": trade_df,
            "cash_balances": cash_balances
        }
    except Exception as e:
        logger.error(f"Error loading portfolio data: {e}")
        return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}}

def calculate_performance_metrics(portfolio_df: pd.DataFrame, trade_df: pd.DataFrame) -> Dict:
    """Calculate key performance metrics"""
    try:
        client = get_supabase_client()
        if client:
            # Use Supabase client for metrics calculation
            return client.get_performance_metrics()
        
        # Fallback to local calculation if Supabase not available
        if portfolio_df.empty:
            return {
                "total_value": 0,
                "total_cost_basis": 0,
                "unrealized_pnl": 0,
                "performance_pct": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            }
        
        # Calculate current portfolio metrics
        if 'total_market_value' in portfolio_df.columns:
            total_value = portfolio_df['total_market_value'].sum()
            total_cost_basis = portfolio_df['total_cost_basis'].sum()
            unrealized_pnl = portfolio_df['total_pnl'].sum()
        else:
            # Fallback for old CSV format
            current_positions = portfolio_df[portfolio_df.get('Total Value', 0) > 0]
            total_value = current_positions.get('Total Value', pd.Series([0])).sum()
            total_cost_basis = current_positions.get('Cost Basis', pd.Series([0])).sum()
            unrealized_pnl = current_positions.get('PnL', pd.Series([0])).sum()
        
        performance_pct = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
        
        # Calculate trade statistics
        if not trade_df.empty:
            total_trades = len(trade_df)
            if 'pnl' in trade_df.columns:
                winning_trades = len(trade_df[trade_df['pnl'] > 0])
                losing_trades = len(trade_df[trade_df['pnl'] < 0])
            else:
                winning_trades = len(trade_df[trade_df.get('PnL', 0) > 0])
                losing_trades = len(trade_df[trade_df.get('PnL', 0) < 0])
        else:
            total_trades = winning_trades = losing_trades = 0
        
        return {
            "total_value": round(total_value, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "performance_pct": round(performance_pct, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades
        }
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {
            "total_value": 0,
            "total_cost_basis": 0,
            "unrealized_pnl": 0,
            "performance_pct": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }

def create_performance_chart(portfolio_df: pd.DataFrame) -> str:
    """Create a Plotly performance chart"""
    try:
        client = get_supabase_client()
        if client:
            # Use Supabase for chart data
            daily_data = client.get_daily_performance_data(days=30)
            if not daily_data:
                return json.dumps({})
            
            df = pd.DataFrame(daily_data)
        else:
            # Fallback to local calculation
            if portfolio_df.empty:
                return json.dumps({})
            
            # Group by date and calculate daily totals
            daily_totals = []
            for date, group in portfolio_df.groupby(portfolio_df['Date'].dt.date):
                current_positions = group[group['Total Value'] > 0]
                if not current_positions.empty:
                    total_value = current_positions['Total Value'].sum()
                    total_cost_basis = current_positions['Cost Basis'].sum()
                    performance_pct = ((total_value - total_cost_basis) / total_cost_basis * 100) if total_cost_basis > 0 else 0
                    
                    daily_totals.append({
                        'date': date,
                        'value': total_value,
                        'cost_basis': total_cost_basis,
                        'performance_pct': performance_pct
                    })
            
            if not daily_totals:
                return json.dumps({})
            
            # Create DataFrame and sort by date
            df = pd.DataFrame(daily_totals).sort_values('date')
            df['performance_index'] = df['performance_pct'] + 100
        
        # Create Plotly chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['performance_index'],
            mode='lines+markers',
            name='Portfolio Performance',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=6)
        ))
        
        # Add break-even line
        fig.add_hline(y=100, line_dash="dash", line_color="gray", 
                     annotation_text="Break-even", annotation_position="bottom right")
        
        fig.update_layout(
            title="Portfolio Performance Over Time",
            xaxis_title="Date",
            yaxis_title="Performance Index (100 = Break-even)",
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    except Exception as e:
        logger.error(f"Error creating performance chart: {e}")
        return json.dumps({})

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/portfolio')
def api_portfolio():
    """API endpoint for portfolio data"""
    data = load_portfolio_data()
    metrics = calculate_performance_metrics(data['portfolio'], data['trades'])
    
    # Get current positions
    current_positions = []
    if not data['portfolio'].empty:
        # Handle both Supabase and CSV data formats
        if 'ticker' in data['portfolio'].columns:
            # Supabase format
            for _, row in data['portfolio'].iterrows():
                current_positions.append({
                    'ticker': row['ticker'],
                    'shares': round(row['total_shares'], 4),
                    'price': round(row['avg_price'], 2),
                    'cost_basis': round(row['total_cost_basis'], 2),
                    'market_value': round(row['total_market_value'], 2),
                    'pnl': round(row['total_pnl'], 2),
                    'pnl_pct': round((row['total_pnl'] / row['total_cost_basis'] * 100), 2) if row['total_cost_basis'] > 0 else 0
                })
        else:
            # CSV format fallback
            current_positions_df = data['portfolio'][data['portfolio'].get('Total Value', 0) > 0]
            for _, row in current_positions_df.iterrows():
                current_positions.append({
                    'ticker': row['Ticker'],
                    'shares': round(row['Shares'], 4),
                    'price': round(row['Price'], 2),
                    'cost_basis': round(row['Cost Basis'], 2),
                    'market_value': round(row['Total Value'], 2),
                    'pnl': round(row['PnL'], 2),
                    'pnl_pct': round((row['PnL'] / row['Cost Basis'] * 100), 2) if row['Cost Basis'] > 0 else 0
                })
    
    return jsonify({
        'metrics': metrics,
        'positions': current_positions,
        'cash_balances': data['cash_balances'],
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/performance-chart')
def api_performance_chart():
    """API endpoint for performance chart data"""
    data = load_portfolio_data()
    chart_data = create_performance_chart(data['portfolio'])
    return chart_data

@app.route('/api/recent-trades')
def api_recent_trades():
    """API endpoint for recent trades"""
    data = load_portfolio_data()
    
    if data['trades'].empty:
        return jsonify([])
    
    # Get last 10 trades
    recent_trades = data['trades'].tail(10).to_dict('records')
    
    # Format the data
    formatted_trades = []
    for trade in recent_trades:
        # Handle both Supabase and CSV formats
        if 'date' in trade:
            # Supabase format
            date_str = trade['date']
            ticker = trade['ticker']
            shares = trade['shares']
            price = trade['price']
            cost_basis = trade['cost_basis']
            pnl = trade['pnl']
            reason = trade['reason']
        else:
            # CSV format
            date_str = trade['Date'].strftime('%Y-%m-%d %H:%M')
            ticker = trade['Ticker']
            shares = trade['Shares']
            price = trade['Price']
            cost_basis = trade['Cost Basis']
            pnl = trade['PnL']
            reason = trade['Reason']
        
        formatted_trades.append({
            'date': date_str,
            'ticker': ticker,
            'shares': round(shares, 4),
            'price': round(price, 2),
            'cost_basis': round(cost_basis, 2),
            'pnl': round(pnl, 2),
            'reason': reason
        })
    
    return jsonify(formatted_trades)

if __name__ == '__main__':
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
