#!/usr/bin/env python3
"""
Portfolio Performance Web Dashboard
A Flask web app to display trading bot portfolio performance using Supabase
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
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
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-this")

# Set JWT secret for auth system
os.environ["JWT_SECRET"] = os.getenv("JWT_SECRET", "your-jwt-secret-change-this")

# Import Supabase client and auth
try:
    from supabase_client import SupabaseClient
    from auth import auth_manager, require_auth, require_admin, get_user_funds, is_admin
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

def load_portfolio_data(fund_name=None) -> Dict:
    """Load and process portfolio data from Supabase, optionally filtered by fund"""
    try:
        client = get_supabase_client()
        if not client:
            logger.warning("Supabase not available, returning empty data")
            return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}}

        # Get available funds
        available_funds = client.get_available_funds()

        if fund_name and fund_name not in available_funds:
            logger.warning(f"Fund '{fund_name}' not found, showing all funds")
            fund_name = None

        # Get data (filtered by fund if specified)
        positions = client.get_current_positions(fund=fund_name)
        trades = client.get_trade_log(limit=1000, fund=fund_name)
        cash_balances = client.get_cash_balances(fund=fund_name)

        # Convert to DataFrames for compatibility with existing code
        portfolio_df = pd.DataFrame(positions) if positions else pd.DataFrame()
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

        return {
            "portfolio": portfolio_df,
            "trades": trades_df,
            "cash_balances": cash_balances,
            "available_funds": available_funds,
            "current_fund": fund_name
        }
    except Exception as e:
        logger.error(f"Error loading portfolio data: {e}")
        return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}}

def calculate_performance_metrics(portfolio_df: pd.DataFrame, trade_df: pd.DataFrame, fund_name=None) -> Dict:
    """Calculate key performance metrics for a specific fund or all funds"""
    try:
        client = get_supabase_client()
        if client and fund_name:
            # Get metrics for specific fund
            positions = client.get_current_positions(fund=fund_name)
            trades = client.get_trade_log(limit=1000, fund=fund_name)

            total_value = sum(pos["total_market_value"] for pos in positions)
            total_cost_basis = sum(pos["total_cost_basis"] for pos in positions)
            unrealized_pnl = sum(pos["total_pnl"] for pos in positions)
            performance_pct = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0

            total_trades = len(trades)
            winning_trades = len([t for t in trades if t["pnl"] > 0])
            losing_trades = len([t for t in trades if t["pnl"] < 0])

            return {
                "total_value": round(total_value, 2),
                "total_cost_basis": round(total_cost_basis, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "performance_pct": round(performance_pct, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades
            }
        elif client:
            # Use Supabase client for combined metrics (legacy)
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
            
            # Load exchange rates for currency conversion
            from utils.currency_converter import load_exchange_rates, convert_usd_to_cad, is_us_ticker
            from pathlib import Path
            from decimal import Decimal
            
            exchange_rates = load_exchange_rates(Path("trading_data/funds/Project Chimera"))
            
            # Group by date and calculate daily totals
            daily_totals = []
            for date, group in portfolio_df.groupby(portfolio_df['Date'].dt.date):
                current_positions = group[group['Total Value'] > 0]
                if not current_positions.empty:
                    # Calculate totals with proper currency conversion
                    total_value_cad = Decimal('0')
                    total_cost_basis_cad = Decimal('0')
                    
                    for _, pos in current_positions.iterrows():
                        ticker = pos['Ticker']
                        value = Decimal(str(pos['Total Value']))
                        cost_basis = Decimal(str(pos['Cost Basis']))
                        
                        # Convert USD to CAD if needed
                        if is_us_ticker(ticker):
                            value_cad = convert_usd_to_cad(value, exchange_rates)
                            cost_basis_cad = convert_usd_to_cad(cost_basis, exchange_rates)
                        else:
                            value_cad = value
                            cost_basis_cad = cost_basis
                        
                        total_value_cad += value_cad
                        total_cost_basis_cad += cost_basis_cad
                    
                    # Convert back to float for compatibility
                    total_value = float(total_value_cad)
                    total_cost_basis = float(total_cost_basis_cad)
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
    """Main dashboard page - requires authentication"""
    # Check for session token
    token = request.cookies.get('session_token')
    if not token:
        return redirect(url_for('auth_page'))
    
    # Verify session
    user_data = auth_manager.verify_session(token)
    if not user_data:
        return redirect(url_for('auth_page'))
    
    fund = request.args.get('fund')
    return render_template('index.html', selected_fund=fund)

@app.route('/auth')
def auth_page():
    """Authentication page"""
    return render_template('auth.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
        
        # Authenticate with Supabase
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/auth/v1/token?grant_type=password",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password
            }
        )
        
        logger.info(f"Login attempt for {email}: Status {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Login failed: {response.text}")
        
        if response.status_code == 200:
            auth_data = response.json()
            user_id = auth_data["user"]["id"]
            
            # Create session token
            session_token = auth_manager.create_user_session(user_id, email)
            
            # Create response with cookie
            response = jsonify({
                "token": session_token,
                "user": {
                    "id": user_id,
                    "email": email
                }
            })
            
            # Set the session token as a cookie
            response.set_cookie('session_token', session_token, max_age=86400, httponly=True, secure=False)
            
            return response
        else:
            error_data = response.json() if response.text else {}
            error_code = error_data.get("error_code", "")
            error_msg = error_data.get("msg", "Invalid credentials")
            
            # Handle specific error cases
            if error_code == "email_not_confirmed":
                return jsonify({"error": "Please check your email and click the confirmation link before logging in."}), 401
            elif error_code == "invalid_credentials":
                return jsonify({"error": "Invalid email or password."}), 401
            else:
                return jsonify({"error": error_msg}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Handle user registration"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not email or not password or not name:
            return jsonify({"error": "Email, password, and name required"}), 400
        
        # Register with Supabase
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/auth/v1/signup",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password,
                "user_metadata": {
                    "full_name": name
                }
            }
        )
        
        logger.info(f"Registration attempt for {email}: Status {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Registration failed: {response.text}")
        
        if response.status_code == 200:
            return jsonify({"message": "Account created successfully! Please check your email and click the confirmation link to activate your account."})
        else:
            error_data = response.json() if response.text else {}
            error_code = error_data.get("error_code", "")
            error_msg = error_data.get("msg", "Registration failed")
            
            # Handle specific error cases
            if error_code == "email_address_invalid":
                return jsonify({"error": "Please enter a valid email address."}), 400
            elif error_code == "weak_password":
                return jsonify({"error": "Password is too weak. Please use at least 6 characters."}), 400
            elif error_code == "user_already_registered":
                return jsonify({"error": "An account with this email already exists."}), 400
            else:
                return jsonify({"error": error_msg}), 400
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    response = jsonify({"message": "Logged out successfully"})
    response.set_cookie('session_token', '', expires=0)
    return response

# =====================================================
# ADMIN ROUTES
# =====================================================

@app.route('/admin')
@require_auth
def admin_dashboard():
    """Admin dashboard page"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    return render_template('admin.html')

@app.route('/api/admin/users')
@require_admin
def api_admin_users():
    """Get all users with their fund assignments"""
    try:
        # Get users from user_profiles
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/list_users_with_funds",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            users = response.json()
            
            # Get stats
            stats = {
                "total_users": len(users),
                "total_funds": len(set(fund for user in users for fund in (user.get('funds') or []))),
                "total_assignments": sum(len(user.get('funds') or []) for user in users)
            }
            
            return jsonify({"users": users, "stats": stats})
        else:
            logger.error(f"Error getting users: {response.text}")
            return jsonify({"users": [], "stats": {"total_users": 0, "total_funds": 0, "total_assignments": 0}})
    except Exception as e:
        logger.error(f"Error in admin users API: {e}")
        return jsonify({"error": "Failed to load users"}), 500

@app.route('/api/admin/funds')
@require_admin
def api_admin_funds():
    """Get all available funds"""
    try:
        # Get unique funds from portfolio_positions
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/portfolio_positions",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            params={"select": "fund"}
        )
        
        if response.status_code == 200:
            funds = list(set(row['fund'] for row in response.json()))
            return jsonify({"funds": sorted(funds)})
        else:
            # Fallback to hardcoded funds
            return jsonify({"funds": ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]})
    except Exception as e:
        logger.error(f"Error getting funds: {e}")
        return jsonify({"funds": ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]})

@app.route('/api/admin/assign-fund', methods=['POST'])
@require_admin
def api_admin_assign_fund():
    """Assign a fund to a user"""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        fund_name = data.get('fund_name')
        
        if not user_email or not fund_name:
            return jsonify({"error": "User email and fund name required"}), 400
        
        # Use the database function to assign fund
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/assign_fund_to_user",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "user_email": user_email,
                "fund_name": fund_name
            }
        )
        
        if response.status_code == 200:
            return jsonify({"message": f"Fund '{fund_name}' assigned to {user_email}"})
        else:
            error_msg = response.json().get('message', 'Failed to assign fund') if response.text else 'Failed to assign fund'
            return jsonify({"error": error_msg}), 400
            
    except Exception as e:
        logger.error(f"Error assigning fund: {e}")
        return jsonify({"error": "Failed to assign fund"}), 500

@app.route('/api/admin/remove-fund', methods=['POST'])
@require_admin
def api_admin_remove_fund():
    """Remove a fund from a user"""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        fund_name = data.get('fund_name')
        
        if not user_email or not fund_name:
            return jsonify({"error": "User email and fund name required"}), 400
        
        # Get user ID first
        user_response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_profiles",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            params={"email": f"eq.{user_email}", "select": "user_id"}
        )
        
        if user_response.status_code != 200 or not user_response.json():
            return jsonify({"error": "User not found"}), 404
        
        user_id = user_response.json()[0]['user_id']
        
        # Remove fund assignment
        remove_response = requests.delete(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_funds",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            params={"user_id": f"eq.{user_id}", "fund_name": f"eq.{fund_name}"}
        )
        
        if remove_response.status_code in [200, 204]:
            return jsonify({"message": f"Fund '{fund_name}' removed from {user_email}"})
        else:
            return jsonify({"error": "Failed to remove fund"}), 400
            
    except Exception as e:
        logger.error(f"Error removing fund: {e}")
        return jsonify({"error": "Failed to remove fund"}), 500

@app.route('/api/funds')
@require_auth
def api_funds():
    """API endpoint for user's assigned funds"""
    try:
        user_funds = get_user_funds()
        return jsonify({"funds": user_funds})
    except Exception as e:
        logger.error(f"Error getting user funds: {e}")
        return jsonify({"funds": []})

@app.route('/api/portfolio')
@require_auth
def api_portfolio():
    """API endpoint for portfolio data"""
    fund = request.args.get('fund')
    
    # Verify user has access to this fund
    if fund and not auth_manager.check_fund_access(request.user_id, fund):
        return jsonify({"error": "Access denied to this fund"}), 403
    
    data = load_portfolio_data(fund)
    metrics = calculate_performance_metrics(data['portfolio'], data['trades'], fund)
    
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
        'available_funds': data.get('available_funds', []),
        'current_fund': data.get('current_fund'),
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/performance-chart')
@require_auth
def api_performance_chart():
    """API endpoint for performance chart data"""
    fund = request.args.get('fund')
    
    # Verify user has access to this fund
    if fund and not auth_manager.check_fund_access(request.user_id, fund):
        return jsonify({"error": "Access denied to this fund"}), 403
    
    data = load_portfolio_data(fund)
    chart_data = create_performance_chart(data['portfolio'])
    return chart_data

@app.route('/api/recent-trades')
@require_auth
def api_recent_trades():
    """API endpoint for recent trades"""
    fund = request.args.get('fund')
    
    # Verify user has access to this fund
    if fund and not auth_manager.check_fund_access(request.user_id, fund):
        return jsonify({"error": "Access denied to this fund"}), 403
    
    data = load_portfolio_data(fund)
    
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
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
