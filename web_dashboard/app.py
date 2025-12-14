#!/usr/bin/env python3
"""
Portfolio Performance Web Dashboard
A Flask web app to display trading bot portfolio performance using Supabase
"""

# Check critical dependencies first
try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for
except ImportError as e:
    print(f"❌ ERROR: {e}")
    print("🔔 SOLUTION: Activate the virtual environment first!")
    print("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    print("   Then run: python app.py")
    print("   You should see (venv) in your prompt when activated.")
    exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ ERROR: pandas not available")
    print("🔔 SOLUTION: Activate the virtual environment first!")
    print("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    exit(1)

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
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-this")

# Configure CORS to allow credentials from Vercel deployment
CORS(app, 
     supports_credentials=True,
     origins=["https://webdashboard-hazel.vercel.app", "http://localhost:5000"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"])

# Set JWT secret for auth system
os.environ["JWT_SECRET"] = os.getenv("JWT_SECRET", "your-jwt-secret-change-this")

# Import Supabase client, auth, and repository system
try:
    from supabase_client import SupabaseClient
    from auth import auth_manager, require_auth, require_admin, get_user_funds, is_admin
    from data.repositories.repository_factory import RepositoryFactory
    SUPABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("🔔 SOLUTION: Activate the virtual environment first!")
    logger.error("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    logger.error("   Then run: python app.py")
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

def load_csv_portfolio_data(fund_name=None) -> Dict:
    """Load portfolio data from CSV files as fallback when Supabase is not available"""
    try:
        # Load repository config
        config_file = Path("../repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            web_config = config.get("web_dashboard", {})
            available_funds = web_config.get("available_funds", [])
            default_fund = web_config.get("default_fund", "Project Chimera")
        else:
            available_funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
            default_fund = "Project Chimera"
        
        # Use specified fund or default
        current_fund = fund_name if fund_name and fund_name in available_funds else default_fund
        
        # Load CSV data from the specified fund directory
        fund_dir = Path(f"../trading_data/funds/{current_fund}")
        
        # Load portfolio data
        portfolio_file = fund_dir / "llm_portfolio_update.csv"
        portfolio_df = pd.DataFrame()
        if portfolio_file.exists():
            portfolio_df = pd.read_csv(portfolio_file)
            if 'Date' in portfolio_df.columns:
                portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'])
        
        # Load trade log
        trade_file = fund_dir / "llm_trade_log.csv"
        trades_df = pd.DataFrame()
        if trade_file.exists():
            trades_df = pd.read_csv(trade_file)
            if 'Date' in trades_df.columns:
                trades_df['Date'] = pd.to_datetime(trades_df['Date'])
        
        # Load cash balances
        cash_file = fund_dir / "cash_balances.json"
        cash_balances = {"CAD": 0.0, "USD": 0.0}
        if cash_file.exists():
            with open(cash_file, 'r') as f:
                cash_balances.update(json.load(f))
        
        logger.info(f"Loaded CSV data for fund: {current_fund}")
        return {
            "portfolio": portfolio_df,
            "trades": trades_df,
            "cash_balances": cash_balances,
            "available_funds": available_funds,
            "current_fund": current_fund
        }
    except Exception as e:
        logger.error(f"Error loading CSV portfolio data: {e}")
        return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}, "available_funds": [], "current_fund": None}

def get_data_source_config() -> str:
    """Get the configured data source from repository config"""
    try:
        config_file = Path("../repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config.get("web_dashboard", {}).get("data_source", "hybrid")
    except Exception:
        pass
    return "hybrid"  # Default fallback

def load_portfolio_data(fund_name=None) -> Dict:
    """Load and process portfolio data based on configured data source"""
    try:
        data_source = get_data_source_config()
        logger.info(f"Using data source: {data_source}")
        
        if data_source == "csv":
            logger.info("Configured for CSV-only mode")
            return load_csv_portfolio_data(fund_name)
        
        elif data_source == "supabase":
            logger.info("Configured for Supabase-only mode")
            try:
                # Use repository system for consistency
                repository = RepositoryFactory.create_repository(
                    'supabase',
                    url=os.getenv("SUPABASE_URL"),
                    key=os.getenv("SUPABASE_ANON_KEY"),
                    fund=fund_name
                )

                # Get available funds
                available_funds = repository.get_available_funds()
                if fund_name and fund_name not in available_funds:
                    logger.warning(f"Fund '{fund_name}' not found in Supabase")
                    return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}, "available_funds": available_funds, "current_fund": None, "error": f"Fund '{fund_name}' not found"}

                # Get data from Supabase using repository (filtered by fund if specified)
                positions = repository.get_current_positions(fund=fund_name)
                trades = repository.get_trade_log(limit=1000, fund=fund_name)
                cash_balances = repository.get_cash_balances()

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
                logger.error(f"Error using Supabase repository: {e}")
                return {"portfolio": pd.DataFrame(), "trades": pd.DataFrame(), "cash_balances": {"CAD": 0.0, "USD": 0.0}, "available_funds": [], "current_fund": None, "error": f"Supabase error: {e}"}
        
        else:  # hybrid mode (default)
            logger.info("Configured for hybrid mode (Supabase with CSV fallback)")
            try:
                # Try to use repository system first
                repository = RepositoryFactory.create_repository(
                    'supabase',
                    url=os.getenv("SUPABASE_URL"),
                    key=os.getenv("SUPABASE_ANON_KEY"),
                    fund=fund_name
                )

                # Get available funds
                available_funds = repository.get_available_funds()
                if fund_name and fund_name not in available_funds:
                    logger.warning(f"Fund '{fund_name}' not found in Supabase, falling back to CSV")
                    return load_csv_portfolio_data(fund_name)

                # Get data from Supabase using repository (filtered by fund if specified)
                positions = repository.get_current_positions(fund=fund_name)
                trades = repository.get_trade_log(limit=1000, fund=fund_name)
                cash_balances = repository.get_cash_balances()

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
                logger.warning(f"Supabase repository error, falling back to CSV data: {e}")
                return load_csv_portfolio_data(fund_name)
    except Exception as e:
        logger.error(f"Error loading portfolio data from Supabase, falling back to CSV: {e}")
        return load_csv_portfolio_data(fund_name)

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

def create_performance_chart(portfolio_df: pd.DataFrame, fund_name: Optional[str] = None) -> str:
    """Create a Plotly performance chart"""
    try:
        client = get_supabase_client()
        if client:
            # Use Supabase for chart data, filtered by fund
            daily_data = client.get_daily_performance_data(days=30, fund=fund_name)
            if not daily_data:
                return json.dumps({})
            
            df = pd.DataFrame(daily_data)
        else:
            # Fallback to local calculation
            if portfolio_df.empty:
                return json.dumps({})
            
            # Load exchange rates for currency conversion
            from utils.currency_converter import load_exchange_rates, convert_usd_to_cad, is_us_ticker
            from decimal import Decimal
            
            # Load exchange rates from common location (USD/CAD rates apply to all funds)
            exchange_rates_path = Path("trading_data/exchange_rates")
            if not exchange_rates_path.exists():
                # Fallback: try to find exchange rates in any fund directory
                funds_dir = Path("trading_data/funds")
                exchange_rates_path = None
                for fund_dir in funds_dir.iterdir():
                    if fund_dir.is_dir():
                        potential_path = fund_dir
                        if (potential_path / "exchange_rates.json").exists():
                            exchange_rates_path = potential_path
                            break
                if not exchange_rates_path:
                    exchange_rates_path = Path("trading_data/funds/Project Chimera")  # Final fallback
            
            exchange_rates = load_exchange_rates(exchange_rates_path)
            
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
            # Use secure cookies for production (Vercel), allow non-secure for local dev
            is_production = request.host != 'localhost:5000' and not request.host.startswith('127.0.0.1')
            response.set_cookie(
                'session_token', 
                session_token, 
                max_age=86400, 
                httponly=True, 
                secure=is_production,  # True for HTTPS (Vercel), False for localhost
                samesite='None' if is_production else 'Lax'  # None required for cross-origin cookies
            )
            
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
    is_production = request.host != 'localhost:5000' and not request.host.startswith('127.0.0.1')
    response.set_cookie(
        'session_token', 
        '', 
        expires=0,
        secure=is_production,
        samesite='None' if is_production else 'Lax'
    )
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
        # Try Supabase first
        client = get_supabase_client()
        if client:
            # Get funds from Supabase
            response = requests.get(
                f"{os.getenv('SUPABASE_URL')}/rest/v1/portfolio_positions",
                headers={
                    "apikey": os.getenv("SUPABASE_ANON_KEY"),
                    "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                data = response.json()
                funds = list(set([item.get('fund', '') for item in data if item.get('fund')]))
                logger.info(f"Returning Supabase funds: {funds}")
                return jsonify({"funds": funds})
        
        # Fallback to CSV configuration
        config_file = Path("../repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            funds = config.get("repository", {}).get("available_funds", [])
            logger.info(f"Returning CSV config funds: {funds}")
            return jsonify({"funds": funds})
        
        # Final fallback
        funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
        logger.info(f"Returning hardcoded fallback funds: {funds}")
        return jsonify({"funds": funds})
        
    except Exception as e:
        logger.error(f"Error getting user funds: {e}")
        # Return fallback funds on error
        return jsonify({"funds": ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]})

@app.route('/api/portfolio')
@require_auth
def api_portfolio():
    """API endpoint for portfolio data"""
    fund = request.args.get('fund')
    
    # Fund access check disabled for single-user setup
    # All authenticated users can access all funds
    
    data = load_portfolio_data(fund)
    metrics = calculate_performance_metrics(data['portfolio'], data['trades'], fund)
    
    # Get current positions
    current_positions = []
    if not data['portfolio'].empty:
        # Handle both Supabase and CSV data formats
        if 'ticker' in data['portfolio'].columns:
            # Supabase format - using latest_positions view with P&L calculations
            for _, row in data['portfolio'].iterrows():
                # Calculate market value and total P&L
                market_value = float(row['shares']) * float(row['price'])
                total_pnl = market_value - float(row['cost_basis'])
                
                current_positions.append({
                    'ticker': row['ticker'],
                    'shares': round(float(row['shares']), 4),
                    'price': round(float(row['price']), 2),
                    'cost_basis': round(float(row['cost_basis']), 2),
                    'market_value': round(market_value, 2),
                    'pnl': round(total_pnl, 2),
                    'pnl_pct': round((total_pnl / float(row['cost_basis']) * 100), 2) if float(row['cost_basis']) > 0 else 0.0,
                    # Add SQL-calculated P&L metrics
                    'daily_pnl_dollar': round(float(row.get('daily_pnl_dollar', 0)), 2),
                    'daily_pnl_pct': round(float(row.get('daily_pnl_pct', 0)), 2),
                    'weekly_pnl_dollar': round(float(row.get('weekly_pnl_dollar', 0)), 2),
                    'weekly_pnl_pct': round(float(row.get('weekly_pnl_pct', 0)), 2),
                    'monthly_pnl_dollar': round(float(row.get('monthly_pnl_dollar', 0)), 2),
                    'monthly_pnl_pct': round(float(row.get('monthly_pnl_pct', 0)), 2)
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
    
    # Fund access check disabled for single-user setup
    # All authenticated users can access all funds
    
    data = load_portfolio_data(fund)
    chart_data = create_performance_chart(data['portfolio'], fund)
    return chart_data

@app.route('/api/contributors')
@require_auth
def api_contributors():
    """API endpoint for fund contributors/holders"""
    fund = request.args.get('fund')
    
    if not fund:
        return jsonify({"error": "Fund parameter required"}), 400
    
    try:
        # Get contributor data from Supabase
        client = SupabaseClient()
        
        # Get contributor ownership data
        result = client.supabase.table('contributor_ownership').select('*').eq('fund', fund).execute()
        
        if not result.data:
            return jsonify([])
        
        # Format the data for frontend
        contributors = []
        total_net = sum([float(c['net_contribution']) for c in result.data])
        
        # NOTE: This API returns ownership percentages from the summary view.
        # For accurate per-contributor returns, use NAV-based calculations from:
        # - portfolio/position_calculator.py calculate_ownership_percentages()
        # - web_dashboard/streamlit_utils.py get_user_investment_metrics()
        for contributor in result.data:
            net_contrib = float(contributor['net_contribution'])
            ownership_pct = (net_contrib / total_net * 100) if total_net > 0 else 0
            
            contributors.append({
                'contributor': contributor['contributor'],
                'email': contributor['email'],
                'net_contribution': net_contrib,
                'total_contributions': float(contributor['total_contributions']),
                'total_withdrawals': float(contributor['total_withdrawals']),
                'ownership_percentage': round(ownership_pct, 2),
                'transaction_count': contributor['transaction_count'],
                'first_contribution': contributor['first_contribution'],
                'last_transaction': contributor['last_transaction']
            })
        
        # Sort by net contribution (highest first)
        contributors.sort(key=lambda x: x['net_contribution'], reverse=True)
        
        return jsonify({
            'contributors': contributors,
            'total_contributors': len(contributors),
            'total_net_contributions': total_net
        })
        
    except Exception as e:
        print(f"Error fetching contributors: {e}")
        return jsonify({"error": "Failed to fetch contributors"}), 500

@app.route('/api/recent-trades')
@require_auth
def api_recent_trades():
    """API endpoint for recent trades"""
    fund = request.args.get('fund')
    
    # Fund access check disabled for single-user setup
    # All authenticated users can access all funds
    
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

# =====================================================
# DEVELOPER/LLM SHARED DATA ACCESS
# =====================================================

@app.route('/dev')
@require_auth
def dev_home():
    """Developer tools home page"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    return render_template('dev_home.html')

@app.route('/dev/sql')
@require_auth
def sql_interface():
    """SQL query interface for debugging"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    return render_template('sql_interface.html')

@app.route('/dev/dashboard')
@require_auth
def dev_dashboard():
    """Developer dashboard with key metrics"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    return render_template('dev_dashboard.html')

@app.route('/api/dev/query', methods=['POST'])
@require_auth
def execute_sql():
    """Execute SQL query safely"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    
    try:
        query = request.json.get('query', '').strip()
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        # Basic safety checks
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        if any(keyword in query.upper() for keyword in dangerous_keywords):
            return jsonify({"error": "Query contains dangerous keywords. Only SELECT queries allowed."}), 400
        
        # Execute query
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Use raw SQL execution
        result = client.supabase.rpc('execute_sql', {'query': query}).execute()
        
        return jsonify({
            "success": True,
            "data": result.data,
            "count": len(result.data) if result.data else 0
        })
        
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        return jsonify({"error": f"Query execution failed: {str(e)}"}), 500

# =====================================================
# DATA EXPORT APIs FOR LLM ACCESS
# =====================================================

@app.route('/api/export/portfolio')
@require_auth
def export_portfolio():
    """Export portfolio data as JSON for LLM analysis"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    
    try:
        fund = request.args.get('fund')
        limit = int(request.args.get('limit', 1000))
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get portfolio positions
        query = client.supabase.table("portfolio_positions").select("*")
        if fund:
            query = query.eq("fund", fund)
        query = query.limit(limit)
        
        result = query.execute()
        
        return jsonify({
            "success": True,
            "data": result.data,
            "count": len(result.data),
            "fund": fund,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Portfolio export error: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route('/api/export/trades')
@require_auth
def export_trades():
    """Export trade data as JSON for LLM analysis"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    
    try:
        fund = request.args.get('fund')
        limit = int(request.args.get('limit', 1000))
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get trade log
        query = client.supabase.table("trade_log").select("*")
        if fund:
            query = query.eq("fund", fund)
        query = query.order("date", desc=True).limit(limit)
        
        result = query.execute()
        
        return jsonify({
            "success": True,
            "data": result.data,
            "count": len(result.data),
            "fund": fund,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Trades export error: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route('/api/export/performance')
@require_auth
def export_performance():
    """Export performance metrics for LLM analysis"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    
    try:
        days = int(request.args.get('days', 30))
        fund = request.args.get('fund')
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get performance data
        performance_data = client.get_performance_metrics()
        daily_data = client.get_daily_performance_data(days, fund=fund)
        
        return jsonify({
            "success": True,
            "performance": performance_data,
            "daily_data": daily_data,
            "days": days,
            "fund": fund,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Performance export error: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route('/api/export/cash')
@require_auth
def export_cash():
    """Export cash balance data for LLM analysis"""
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    
    try:
        fund = request.args.get('fund')
        
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get cash balances
        cash_balances = client.get_cash_balances(fund)
        
        return jsonify({
            "success": True,
            "data": cash_balances,
            "fund": fund,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Cash export error: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

if __name__ == '__main__':
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
