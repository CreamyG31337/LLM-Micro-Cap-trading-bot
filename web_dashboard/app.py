#!/usr/bin/env python3
"""
Portfolio Performance Web Dashboard
A Flask web app to display trading bot portfolio performance using Supabase
"""

# Check critical dependencies first
try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for, session
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
from datetime import datetime, timedelta, date
from pathlib import Path
import yfinance as yf
import plotly.graph_objs as go
import plotly.utils
from typing import Dict, List, Optional, Tuple, Any
import logging
import requests
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup file logging to write to app.log
try:
    from log_handler import setup_logging
    setup_logging()
except ImportError:
    pass  # Fallback to basicConfig if log_handler not available

# Initialize Flask app with template and static folders
# serving static files at /assets to avoid conflict with Streamlit's /static
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static',
            static_url_path='/assets')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-this")

# FORCE DEBUG MODE - Ensures errors are visible
app.debug = True
app.config['PROPAGATE_EXCEPTIONS'] = True

# CSRF Protection (optional - can be enabled if Flask-WTF is installed)
try:
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)
    CSRF_ENABLED = True
    logger.info("CSRF protection enabled via Flask-WTF")
except ImportError:
    CSRF_ENABLED = False
    logger.warning("Flask-WTF not available - CSRF protection disabled. Install with: pip install flask-wtf")

# Configure CORS to allow credentials from Vercel deployment
CORS(app, 
     supports_credentials=True,
     origins=["https://webdashboard-hazel.vercel.app", "http://localhost:5000"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"])

# Set JWT secret for auth system
os.environ["JWT_SECRET"] = os.getenv("JWT_SECRET", "your-jwt-secret-change-this")

# Global error handler to expose tracebacks in response
@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    tb = traceback.format_exc()
    
    # Return JSON for API requests
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
            "traceback": tb
        }), 500

    # Return HTML for browser requests (visible on screen)
    return f"""
    <html>
        <head>
            <title>500 Internal Server Error</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 2rem; line-height: 1.5; }}
                h1 {{ color: #dc2626; border-bottom: 2px solid #fee2e2; padding-bottom: 0.5rem; }}
                pre {{ background: #f3f4f6; padding: 1.5rem; border-radius: 0.5rem; overflow-x: auto; font-size: 0.9em; border: 1px solid #e5e7eb; }}
                .error-msg {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; color: #1f2937; }}
            </style>
        </head>
        <body>
            <h1>500 Internal Server Error</h1>
            <div class="error-msg">{str(e)}</div>
            <pre>{tb}</pre>
        </body>
    </html>
    """, 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    
    # Handle non-HTTP exceptions (like 500s)
    import traceback
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception: {e}\n{tb}")
    
    # Return JSON for API requests
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({
            "error": "Unhandled Exception",
            "message": str(e),
            "traceback": tb
        }), 500
        
    # Return HTML for browser requests (visible on screen)
    return f"""
    <html>
        <head>
            <title>Application Error</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 2rem; line-height: 1.5; }}
                h1 {{ color: #dc2626; border-bottom: 2px solid #fee2e2; padding-bottom: 0.5rem; }}
                pre {{ background: #f3f4f6; padding: 1.5rem; border-radius: 0.5rem; overflow-x: auto; font-size: 0.9em; border: 1px solid #e5e7eb; }}
                .error-msg {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; color: #1f2937; }}
            </style>
        </head>
        <body>
            <h1>Unhandled Exception</h1>
            <div class="error-msg">{str(e)}</div>
            <pre>{tb}</pre>
        </body>
    </html>
    """, 500

# Import Supabase client, auth, and repository system
try:
    from supabase_client import SupabaseClient
    from auth import auth_manager, require_auth, require_admin, get_user_funds, is_admin
    SUPABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("🔔 SOLUTION: Activate the virtual environment first!")
    logger.error("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    logger.error("   Then run: python app.py")
    SUPABASE_AVAILABLE = False

# Import repository system (optional - only needed for portfolio routes)
try:
    from data.repositories.repository_factory import RepositoryFactory
    REPOSITORY_AVAILABLE = True
except ImportError:
    RepositoryFactory = None
    REPOSITORY_AVAILABLE = False
    logger.debug("Repository system not available (optional for Settings page)")

def get_supabase_client() -> Optional[SupabaseClient]:
    """Get Supabase client instance"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        return SupabaseClient()
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def get_navigation_context(current_page: str = None) -> Dict[str, Any]:
    """Get navigation context for Flask templates"""
    try:
        from shared_navigation import get_navigation_links, is_page_migrated
        from user_preferences import get_user_preference
        from flask_auth_utils import get_user_email_flask
        
        # Get navigation links
        links = get_navigation_links()
        is_v2_enabled = get_user_preference('v2_enabled', default=False)
        
        # Build navigation context
        nav_links = []
        for link in links:
            # Determine if link should be shown
            show = True
            
            # Check if page is migrated and v2 is enabled
            if is_page_migrated(link['page']) and not is_v2_enabled:
                # Don't show migrated pages if v2 is disabled
                show = False
            
            # Check service availability for specific pages
            if link['page'] == 'social_sentiment' or link['page'] == 'etf_holdings':
                # These require Postgres
                try:
                    from postgres_client import PostgresClient
                    client = PostgresClient()
                    if not client.test_connection():
                        show = False
                except Exception:
                    show = False

            
            # AI Assistant - always show (let the page handle Ollama unavailability)
            
            # Determine URL (use Flask route if migrated and v2 enabled)
            url = link['url']
            if is_page_migrated(link['page']) and is_v2_enabled:
                url = link['url']  # Already points to Flask route
            
            nav_links.append({
                'name': link['name'],
                'url': url,
                'icon': link['icon'],
                'show': show,
                'active': current_page == link['page']
            })
        
        return {
            'navigation_links': nav_links,
            'is_admin': is_admin() if hasattr(request, 'user_id') else False
        }
    except Exception as e:
        logger.warning(f"Error building navigation context: {e}")
        return {
            'navigation_links': [],
            'is_admin': False
        }







# Register Blueprints
try:
    from routes.research_routes import research_bp
    app.register_blueprint(research_bp, url_prefix='/v2')
    logger.debug("Registered Research Blueprint at /v2")
except Exception as e:
    logger.error(f"Failed to register Research Blueprint: {e}")

def load_portfolio_data(fund_name=None) -> Dict:
    """Load and process portfolio data from Supabase (web app only - no CSV fallback)"""
    if not REPOSITORY_AVAILABLE:
        logger.error("Repository system not available - cannot load portfolio data")
        return {
            "portfolio": pd.DataFrame(),
            "trades": pd.DataFrame(),
            "cash_balances": {"CAD": 0.0, "USD": 0.0},
            "available_funds": [],
            "current_fund": None,
            "error": "Repository system not available. Please check data.repositories module."
        }
    
    try:
        # Use repository system to load from Supabase
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
            return {
                "portfolio": pd.DataFrame(),
                "trades": pd.DataFrame(),
                "cash_balances": {"CAD": 0.0, "USD": 0.0},
                "available_funds": available_funds,
                "current_fund": None,
                "error": f"Fund '{fund_name}' not found"
            }

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
        logger.error(f"Error loading portfolio data from Supabase: {e}")
        return {
            "portfolio": pd.DataFrame(),
            "trades": pd.DataFrame(),
            "cash_balances": {"CAD": 0.0, "USD": 0.0},
            "available_funds": [],
            "current_fund": None,
            "error": f"Failed to load data from Supabase: {str(e)}"
        }

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
    
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme
        
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        fund = request.args.get('fund')
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='dashboard')
        
        return render_template('index.html', 
                             selected_fund=fund,
                             user_email=user_email,
                             user_theme=user_theme,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        fund = request.args.get('fund')
        # Fallback with minimal context
        nav_context = get_navigation_context(current_page='dashboard')
        return render_template('index.html', 
                             selected_fund=fund,
                             user_email='User',
                             user_theme='system',
                             **nav_context)

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
            
            # Set the session token as a cookie (Flask legacy)
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

            # Set the auth token as a cookie (Streamlit/Supabase compatible)
            # This is the REAL Supabase access token required for RLS and auth.uid()
            if "access_token" in auth_data:
                # Default Supabase expiry is 3600s (1 hour)
                expires_in = auth_data.get("expires_in", 3600)
                response.set_cookie(
                    'auth_token', 
                    auth_data["access_token"], 
                    max_age=expires_in, 
                    httponly=True, 
                    secure=is_production,
                    samesite='None' if is_production else 'Lax'
                )
                
                # Also set refresh token if available so client can refresh if needed
                if "refresh_token" in auth_data:
                    response.set_cookie(
                        'refresh_token', 
                        auth_data["refresh_token"], 
                        max_age=86400 * 30, # 30 days usually
                        httponly=True, 
                        secure=is_production,
                        samesite='None' if is_production else 'Lax'
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
    
    # Clear session_token (Flask login)
    response.set_cookie(
        'session_token', 
        '', 
        expires=0,
        secure=is_production,
        samesite='None' if is_production else 'Lax'
    )
    
    # Clear auth_token (Streamlit login) to prevent auto-login loop
    response.set_cookie(
        'auth_token', 
        '', 
        expires=0,
        secure=is_production,
        samesite='None' if is_production else 'Lax'
    )
    
    # Clear refresh_token
    response.set_cookie(
        'refresh_token', 
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
            result_data = response.json()
            if isinstance(result_data, dict):
                # New JSON response format
                if result_data.get('success'):
                    return jsonify(result_data), 200
                elif result_data.get('already_assigned'):
                    return jsonify(result_data), 200  # Return 200 but with warning info
                else:
                    return jsonify(result_data), 400
            else:
                # Legacy boolean response
                return jsonify({"message": f"Fund '{fund_name}' assigned to {user_email}"}), 200
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
                logger.debug(f"Returning Supabase funds: {funds}")
                return jsonify({"funds": funds})
        
        # Fallback to CSV configuration
        config_file = Path("../repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            funds = config.get("repository", {}).get("available_funds", [])
            logger.debug(f"Returning CSV config funds: {funds}")
            return jsonify({"funds": funds})
        
        # Final fallback
        funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
        logger.debug(f"Returning hardcoded fallback funds: {funds}")
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

@app.route('/v2/logs/debug')
@require_auth
def logs_debug():
    """Debug endpoint to check admin status without requiring admin"""
    try:
        from flask_auth_utils import get_user_email_flask, get_user_id_flask
        from auth import is_admin
        from supabase_client import SupabaseClient
        
        user_email = get_user_email_flask()
        user_id = get_user_id_flask()
        request_user_id = getattr(request, 'user_id', None)
        admin_status = is_admin() if hasattr(request, 'user_id') else False
        
        # Check user profile directly in database
        profile_role = None
        profile_error = None
        try:
            token = request.cookies.get('auth_token') or request.cookies.get('session_token')
            if token and len(token.split('.')) == 3:
                # Use SupabaseClient with user token (handles auth properly)
                client = SupabaseClient(user_token=token)
                # Query user_profiles table directly
                result = client.supabase.table('user_profiles').select('role, email').eq('user_id', request_user_id).execute()
                if result.data and len(result.data) > 0:
                    profile_role = result.data[0].get('role')
                else:
                    profile_error = "No profile found"
        except Exception as e:
            profile_error = str(e)
            logger.error(f"Error querying user_profiles: {e}", exc_info=True)
        
        # Try RPC call directly
        rpc_result = None
        rpc_error = None
        try:
            token = request.cookies.get('auth_token') or request.cookies.get('session_token')
            if token and request_user_id and len(token.split('.')) == 3:
                # Use SupabaseClient with user token (handles auth properly)
                client = SupabaseClient(user_token=token)
                rpc_response = client.supabase.rpc('is_admin', {'user_uuid': request_user_id}).execute()
                rpc_result = rpc_response.data
        except Exception as e:
            rpc_error = str(e)
            logger.error(f"Error calling is_admin RPC: {e}", exc_info=True)
        
        return jsonify({
            "user_email": user_email,
            "user_id": user_id,
            "request_user_id": request_user_id,
            "is_admin": admin_status,
            "profile_role": profile_role,
            "profile_error": profile_error,
            "rpc_result": rpc_result,
            "rpc_error": rpc_error,
            "auth_token_present": bool(request.cookies.get('auth_token')),
            "session_token_present": bool(request.cookies.get('session_token'))
        })
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/v2/logs')
@require_admin
def logs_page():
    """Admin logs viewer page (Flask v2)"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme
        
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='admin_logs')
        
        logger.debug(f"Rendering logs page for user: {user_email}")
        
        return render_template('logs.html', 
                             user_email=user_email,
                             user_theme=user_theme,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error rendering logs page: {e}", exc_info=True)
        user_theme = 'system'
        nav_context = get_navigation_context(current_page='admin_logs')
        return render_template('logs.html', 
                             user_email='Admin',
                             user_theme=user_theme,
                             **nav_context)

@app.route('/api/logs/application')
@require_admin
def api_logs_application():
    """Get application logs with filtering"""
    try:
        from log_handler import read_logs_from_file
        
        # Get query parameters
        level = request.args.get('level', 'INFO + ERROR')
        limit = int(request.args.get('limit', 100))
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        
        # Handle special "INFO + ERROR" filter
        if level == "All":
            level_filter = None
        elif level == "INFO + ERROR":
            level_filter = ["INFO", "ERROR"]
        else:
            level_filter = level
        
        # Get exclude_modules parameter (default to excluding heartbeat)
        exclude_heartbeat = request.args.get('exclude_heartbeat', 'true').lower() == 'true'
        exclude_modules = []
        if exclude_heartbeat:
            exclude_modules.append('scheduler.scheduler_core.heartbeat')
        
        # Get all filtered logs
        all_logs = read_logs_from_file(
            n=None,
            level=level_filter,
            search=search if search else None,
            return_all=True,
            exclude_modules=exclude_modules if exclude_modules else None
        )
        
        # Reverse for newest first
        all_logs = list(reversed(all_logs))
        
        # Pagination
        total = len(all_logs)
        start = (page - 1) * limit
        end = start + limit
        logs = all_logs[start:end]
        
        # Format logs for JSON
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                'timestamp': log['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'level': log['level'],
                'module': log['module'],
                'message': log['message']
            })
        
        return jsonify({
            'logs': formatted_logs,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit if total > 0 else 1
        })
        
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/ollama')
@require_admin
def api_logs_ollama():
    """Get Ollama logs from ollama.log file"""
    try:
        import os
        from pathlib import Path
        
        log_file = Path(__file__).parent / 'logs' / 'ollama.log'
        
        if not log_file.exists():
            return jsonify({
                'logs': [],
                'total': 0,
                'page': 1,
                'pages': 1,
                'error': 'Ollama log file not found. Ensure volume mapping is configured.'
            })
        
        # Read file (tail approach for large files)
        limit = int(request.args.get('limit', 100))
        page = int(request.args.get('page', 1))
        search = request.args.get('search', '')
        
        # Read last N lines (simple approach for now)
        # For large files, read from end
        file_size = log_file.stat().st_size
        if file_size == 0:
            return jsonify({
                'logs': [],
                'total': 0,
                'page': 1,
                'pages': 1
            })
        
        # Read up to 5MB from end for efficiency
        buffer_size = min(5 * 1024 * 1024, file_size)
        with open(log_file, 'rb') as f:
            f.seek(max(0, file_size - buffer_size))
            buffer = f.read().decode('utf-8', errors='ignore')
        
        lines = buffer.split('\n')
        if file_size > buffer_size:
            lines = lines[1:]  # Skip first partial line
        
        # Apply search filter
        if search:
            lines = [line for line in lines if search.lower() in line.lower()]
        
        # Reverse for newest first
        lines = list(reversed(lines))
        
        # Pagination
        total = len(lines)
        start = (page - 1) * limit
        end = start + limit
        paginated_lines = lines[start:end]
        
        # Format logs (Ollama logs don't have structured format, so treat each line as a message)
        formatted_logs = []
        for line in paginated_lines:
            # Try to extract timestamp if present, otherwise use current time
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing - if line starts with timestamp-like pattern, extract it
            # Otherwise treat entire line as message
            formatted_logs.append({
                'timestamp': '',  # Ollama logs may not have timestamps
                'level': 'INFO',  # Default level
                'module': 'ollama',
                'message': line
            })
        
        return jsonify({
            'logs': formatted_logs,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit if total > 0 else 1
        })
        
    except Exception as e:
        logger.error(f"Error fetching Ollama logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
@require_admin
def api_logs_clear():
    """Clear application logs"""
    try:
        import os
        log_file = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
        if os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("")
            return jsonify({'success': True, 'message': 'Logs cleared'})
        return jsonify({'success': False, 'error': 'Log file not found'}), 404
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/v2/settings')
@require_auth
def settings_page():
    """User preferences/settings page (Flask v2)"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_timezone, get_user_currency, get_user_theme, get_user_preference
        
        user_email = get_user_email_flask()
        current_timezone = get_user_timezone() or 'America/Los_Angeles'
        current_currency = get_user_currency() or 'CAD'
        current_theme = get_user_theme() or 'system'
        
        # Get v2_enabled with fallback
        is_v2_enabled = get_user_preference('v2_enabled', default=False)
        if is_v2_enabled is False:
            # Fallback: try getting from all preferences
            try:
                from user_preferences import get_all_user_preferences
                all_prefs = get_all_user_preferences()
                if isinstance(all_prefs, dict) and 'v2_enabled' in all_prefs:
                    fallback_value = all_prefs['v2_enabled']
                    if isinstance(fallback_value, bool):
                        is_v2_enabled = fallback_value
                    elif isinstance(fallback_value, str) and fallback_value.lower() in ('true', 'false'):
                        is_v2_enabled = fallback_value.lower() == 'true'
                    elif fallback_value:
                        is_v2_enabled = bool(fallback_value)
            except Exception:
                pass
        
        # Debug logging
        logger.debug(f"[SETTINGS DEBUG] Loaded preferences - timezone: {current_timezone}, currency: {current_currency}, theme: {current_theme}, v2_enabled: {is_v2_enabled} (type: {type(is_v2_enabled).__name__})")
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='settings')
        
        return render_template('settings.html',
                             user_email=user_email,
                             current_timezone=current_timezone,
                             current_currency=current_currency,
                             current_theme=current_theme,
                             user_theme=current_theme,
                             is_v2_enabled=is_v2_enabled,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        return jsonify({"error": "Failed to load settings page"}), 500

@app.route('/api/settings/timezone', methods=['POST'])
@require_auth
def update_timezone():
    """Update user timezone preference"""
    try:
        from user_preferences import set_user_timezone
        from flask_auth_utils import get_user_id_flask
        
        data = request.get_json()
        timezone = data.get('timezone')
        
        if not timezone:
            return jsonify({"success": False, "error": "Timezone is required"}), 400
        
        user_id = get_user_id_flask()
        logger.debug(f"Updating timezone for user {user_id} to {timezone}")
        
        result = set_user_timezone(timezone)
        if result:
            logger.info(f"Successfully updated timezone to {timezone}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to update timezone - set_user_timezone returned False for user {user_id}")
            return jsonify({"success": False, "error": "Failed to save timezone. Check server logs for details."}), 500
            
    except Exception as e:
        logger.error(f"Error updating timezone: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@app.route('/api/settings/currency', methods=['POST'])
@require_auth
def update_currency():
    """Update user currency preference"""
    try:
        from user_preferences import set_user_currency
        from flask_auth_utils import get_user_id_flask
        
        data = request.get_json()
        currency = data.get('currency')
        
        if not currency:
            return jsonify({"success": False, "error": "Currency is required"}), 400
        
        user_id = get_user_id_flask()
        logger.debug(f"Updating currency for user {user_id} to {currency}")
        
        result = set_user_currency(currency)
        if result:
            logger.info(f"Successfully updated currency to {currency}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to update currency - set_user_currency returned False for user {user_id}")
            return jsonify({"success": False, "error": "Failed to save currency. Check server logs for details."}), 500
            
    except Exception as e:
        logger.error(f"Error updating currency: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@app.route('/api/settings/theme', methods=['POST'])
@require_auth
def update_theme():
    """Update user theme preference"""
    try:
        from user_preferences import set_user_theme
        from flask_auth_utils import get_user_id_flask
        
        data = request.get_json()
        theme = data.get('theme')
        
        if not theme:
            return jsonify({"success": False, "error": "Theme is required"}), 400
        
        user_id = get_user_id_flask()
        logger.debug(f"Updating theme for user {user_id} to {theme}")
        
        result = set_user_theme(theme)
        if result:
            logger.info(f"Successfully updated theme to {theme}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to update theme - set_user_theme returned False for user {user_id}")
            return jsonify({"success": False, "error": "Failed to save theme. Check server logs for details."}), 500
            
    except Exception as e:
        logger.error(f"Error updating theme: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@app.route('/api/settings/v2_enabled', methods=['POST'])
@require_auth
def update_v2_enabled():
    """Update v2 beta enabled preference"""
    try:
        from user_preferences import set_user_preference
        from flask_auth_utils import get_user_id_flask
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Missing request body"}), 400
            
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({"success": False, "error": "Missing enabled parameter"}), 400
        
        user_id = get_user_id_flask()
        logger.debug(f"Updating v2_enabled for user {user_id} to {enabled}")
        
        # Debug: capture any exception from set_user_preference
        try:
            result = set_user_preference('v2_enabled', enabled)
            logger.debug(f"set_user_preference returned: {result} (type: {type(result)})")
        except Exception as pref_error:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"set_user_preference raised exception: {pref_error}\n{tb}")
            return jsonify({"success": False, "error": f"Preference error: {str(pref_error)}", "traceback": tb}), 500
            
        if result:
            logger.info(f"Successfully updated v2_enabled to {enabled}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to update v2_enabled - set_user_preference returned False")
            return jsonify({"success": False, "error": "set_user_preference returned False - check server logs"}), 500
    except Exception as e:
        logger.error(f"Error updating v2 enabled: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@app.route('/api/settings/ai_model', methods=['POST'])
@require_auth
def update_ai_model():
    """Update user AI model preference"""
    try:
        from user_preferences import set_user_ai_model
        from flask_auth_utils import get_user_id_flask
        
        data = request.get_json()
        model = data.get('model')
        
        if not model:
            return jsonify({"success": False, "error": "Model is required"}), 400
        
        user_id = get_user_id_flask()
        logger.debug(f"Updating AI model for user {user_id} to {model}")
        
        result = set_user_ai_model(model)
        if result:
            logger.info(f"Successfully updated AI model to {model}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to update AI model - set_user_ai_model returned False")
            return jsonify({"success": False, "error": "Failed to save model preference"}), 500
            
    except Exception as e:
        logger.error(f"Error updating AI model: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

@app.route('/api/settings/debug', methods=['GET'])
@require_auth
def settings_debug():
    """Debug endpoint to test preference saving"""
    try:
        from user_preferences import set_user_preference, get_user_preference, _get_user_id, _is_authenticated
        from flask_auth_utils import get_user_id_flask, get_auth_token
        from supabase_client import SupabaseClient
        
        user_id = get_user_id_flask()
        token = get_auth_token()
        is_authenticated = _is_authenticated()
        
        # Test creating client
        client = None
        client_error = None
        try:
            client = SupabaseClient(user_token=token) if token else SupabaseClient()
        except Exception as e:
            client_error = str(e)
        
        # Test RPC call
        rpc_result = None
        rpc_error = None
        if client:
            try:
                # Test with a simple preference
                test_result = client.supabase.rpc('set_user_preference', {
                    'pref_key': 'test_key',
                    'pref_value': json.dumps('test_value')
                }).execute()
                rpc_result = test_result.data
            except Exception as e:
                rpc_error = str(e)
                logger.error(f"RPC test failed: {e}", exc_info=True)
        
        return jsonify({
            "user_id": user_id,
            "token_present": bool(token),
            "token_length": len(token) if token else 0,
            "is_authenticated": is_authenticated,
            "client_created": client is not None,
            "client_error": client_error,
            "rpc_result": rpc_result,
            "rpc_error": rpc_error
        })
    except Exception as e:
        logger.error(f"Error in settings debug: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================================
# Ticker Details Page (Flask v2)
# ============================================================================

@app.route('/v2/ticker')
@require_auth
def ticker_details_page():
    """Ticker details page (Flask v2)"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme
        
        user_email = get_user_email_flask()
        ticker = request.args.get('ticker', '').upper().strip()
        user_theme = get_user_theme() or 'system'
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='ticker_details')
        
        return render_template('ticker_details.html',
                             user_email=user_email,
                             ticker=ticker,
                             user_theme=user_theme,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error loading ticker details page: {e}")
        return jsonify({"error": "Failed to load ticker details page"}), 500

@app.route('/api/v2/ticker/list')
@require_auth
def api_ticker_list():
    """Get list of all available tickers for dropdown"""
    try:
        # Simple caching with module-level dict
        import time
        if not hasattr(api_ticker_list, '_cache') or not hasattr(api_ticker_list, '_cache_time'):
            api_ticker_list._cache = None
            api_ticker_list._cache_time = 0
        
        # Check cache (60s TTL)
        current_time = time.time()
        if api_ticker_list._cache and (current_time - api_ticker_list._cache_time) < 60:
            return jsonify({"tickers": api_ticker_list._cache})
        
        # Import and fetch tickers
        try:
            from utils.db_utils import get_all_unique_tickers
            tickers = get_all_unique_tickers()
        except (ImportError, ModuleNotFoundError):
            # Fallback if utils.db_utils not available
            logger.warning("utils.db_utils not available, returning empty ticker list")
            tickers = []
        
        # Sort and cache
        tickers = sorted(tickers) if tickers else []
        api_ticker_list._cache = tickers
        api_ticker_list._cache_time = current_time
        
        return jsonify({"tickers": tickers})
    except Exception as e:
        logger.error(f"Error fetching ticker list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ticker/info')
@require_auth
def api_ticker_info():
    """Get comprehensive ticker information"""
    try:
        ticker = request.args.get('ticker', '').upper().strip()
        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400
        
        # Initialize clients with role-based access
        from postgres_client import PostgresClient
        from supabase_client import SupabaseClient
        from flask_auth_utils import get_user_id_flask
        from auth import is_admin
        
        # Check if user is admin
        user_is_admin = is_admin()
        
        # Initialize Supabase client with appropriate access
        if user_is_admin:
            supabase_client = SupabaseClient(use_service_role=True)
        else:
            # For regular users, use auth_token from cookie (it IS the access token)
            auth_token = request.cookies.get('auth_token')
            supabase_client = SupabaseClient(user_token=auth_token) if auth_token else None
        
        # Initialize Postgres client
        try:
            postgres_client = PostgresClient()
        except Exception as e:
            logger.warning(f"PostgresClient initialization failed: {e}")
            postgres_client = None
        
        if not supabase_client and not postgres_client:
            return jsonify({"error": "Unable to connect to databases"}), 500
        
        # Get ticker info
        from ticker_utils import get_ticker_info
        ticker_data = get_ticker_info(ticker, supabase_client, postgres_client)
        
        # Convert datetime objects to ISO strings for JSON serialization
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            return obj
        
        # Recursively serialize the response
        import json as json_lib
        ticker_data_str = json_lib.dumps(ticker_data, default=serialize_datetime)
        ticker_data = json_lib.loads(ticker_data_str)
        
        return jsonify(ticker_data)
    except Exception as e:
        logger.error(f"Error fetching ticker info for {ticker}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ticker/price-history')
@require_auth
def api_ticker_price_history():
    """Get price history for a ticker"""
    try:
        ticker = request.args.get('ticker', '').upper().strip()
        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400
        
        days = int(request.args.get('days', 90))
        
        # Initialize Supabase client with role-based access
        from supabase_client import SupabaseClient
        from auth import is_admin
        
        if is_admin():
            supabase_client = SupabaseClient(use_service_role=True)
        else:
            # For regular users, use auth_token from cookie (it IS the access token)
            auth_token = request.cookies.get('auth_token')
            supabase_client = SupabaseClient(user_token=auth_token) if auth_token else None
        
        if not supabase_client:
            return jsonify({"error": "Unable to connect to database"}), 500
        
        # Get price history
        from ticker_utils import get_ticker_price_history
        price_df = get_ticker_price_history(ticker, supabase_client, days=days)
        
        # Convert DataFrame to JSON
        if price_df.empty:
            return jsonify({"data": []})
        
        # Convert dates to ISO strings
        price_df = price_df.copy()
        if 'date' in price_df.columns:
            price_df['date'] = price_df['date'].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
        
        return jsonify({"data": price_df.to_dict('records')})
    except Exception as e:
        logger.error(f"Error fetching price history for {ticker}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ticker/chart')
@require_auth
def api_ticker_chart():
    """Get Plotly chart JSON for ticker price history"""
    try:
        ticker = request.args.get('ticker', '').upper().strip()
        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400
        
        use_solid = request.args.get('use_solid', 'false').lower() == 'true'
        
        # Initialize Supabase client
        from supabase_client import SupabaseClient
        from auth import is_admin
        
        if is_admin():
            supabase_client = SupabaseClient(use_service_role=True)
        else:
            # For regular users, use auth_token from cookie (it IS the access token)
            auth_token = request.cookies.get('auth_token')
            supabase_client = SupabaseClient(user_token=auth_token) if auth_token else None
        
        if not supabase_client:
            return jsonify({"error": "Unable to connect to database"}), 500
        
        # Get price history
        from ticker_utils import get_ticker_price_history
        price_df = get_ticker_price_history(ticker, supabase_client, days=90)
        
        if price_df.empty:
            return jsonify({"error": "No price data available"}), 404
        
        # Create chart
        from chart_utils import create_ticker_price_chart
        all_benchmarks = ['sp500', 'qqq', 'russell2000', 'vti']
        fig = create_ticker_price_chart(
            price_df,
            ticker,
            show_benchmarks=all_benchmarks,
            show_weekend_shading=True,
            use_solid_lines=use_solid
        )
        
        # Convert Plotly figure to JSON
        import plotly.utils
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Return as JSON response
        from flask import Response
        return Response(graph_json, mimetype='application/json')
    except Exception as e:
        logger.error(f"Error generating chart for {ticker}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ticker/external-links')
@require_auth
def api_ticker_external_links():
    """Get external links for a ticker"""
    try:
        ticker = request.args.get('ticker', '').upper().strip()
        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400
        
        exchange = request.args.get('exchange', None)
        
        from ticker_utils import get_ticker_external_links
        links = get_ticker_external_links(ticker, exchange=exchange)
        
        return jsonify(links)
    except Exception as e:
        logger.error(f"Error fetching external links for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/search', methods=['POST'])
@require_auth
def api_ai_search():
    """Perform web search"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        from searxng_client import get_searxng_client
        client = get_searxng_client()
        
        if not client:
            return jsonify({"error": "Search is unavailable"}), 503
            
        results = client.search(query)
        return jsonify({"results": results})
        
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/preview_context', methods=['POST'])
@require_auth
def api_ai_preview_context():
    """Preview the AI context (debug mode) - Shows the raw data tables sent to LLM"""
    try:
        from flask_auth_utils import get_user_id_flask
        from ai_context_builder import (
            format_holdings, format_thesis, format_trades, 
            format_performance_metrics, format_cash_balances,
            format_price_volume_table, format_fundamentals_table
        )
        from streamlit_utils import (
            get_current_positions, get_trade_log, get_cash_balances,
            calculate_portfolio_value_over_time, get_fund_thesis_data,
            calculate_performance_metrics
        )
        
        data = request.get_json()
        fund = data.get('fund')
        
        if not fund:
            return jsonify({"error": "No fund specified"}), 400

        user_id = get_user_id_flask()
        context_parts = []
        
        # --- Always Included: Holdings ---
        positions_df = get_current_positions(fund)
        trades_df = get_trade_log(limit=100, fund=fund)
        
        include_pv = data.get('include_price_volume', True)
        include_fund = data.get('include_fundamentals', True)
        
        if not positions_df.empty:
            holdings_text = format_holdings(
                positions_df,
                fund,
                trades_df=trades_df,
                include_price_volume=include_pv,
                include_fundamentals=include_fund
            )
            context_parts.append(holdings_text)
        
        # --- Always Included: Performance Metrics ---
        try:
            metrics = calculate_performance_metrics(fund)
            portfolio_df = calculate_portfolio_value_over_time(fund, days=365)
            if metrics:
                context_parts.append(format_performance_metrics(metrics, portfolio_df))
        except Exception as e:
            logger.warning(f"Error loading performance metrics: {e}")
        
        # --- Always Included: Cash Balances ---
        try:
            cash = get_cash_balances(fund)
            if cash:
                context_parts.append(format_cash_balances(cash))
        except Exception as e:
            logger.warning(f"Error loading cash balances: {e}")
        
        # --- Optional: Thesis ---
        if data.get('include_thesis', False):
            try:
                thesis_data = get_fund_thesis_data(fund)
                if thesis_data:
                    context_parts.append(format_thesis(thesis_data))
            except Exception as e:
                logger.warning(f"Error loading thesis: {e}")
        
        # --- Optional: Trades ---
        if data.get('include_trades', False):
            try:
                if not trades_df.empty:
                    context_parts.append(format_trades(trades_df, limit=100))
            except Exception as e:
                logger.warning(f"Error loading trades: {e}")
        
        # Combine all parts
        context_string = "\n\n---\n\n".join(context_parts) if context_parts else "No context data available"
        
        return jsonify({
            "success": True, 
            "context": context_string,
            "char_count": len(context_string)
        })
        
    except Exception as e:
        logger.error(f"Error generating context preview: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================================
# AI Assistant Routes (Flask v2)
# ============================================================================

@app.route('/v2/ai_assistant')
@require_auth
def ai_assistant_page():
    """AI Assistant chat interface page (Flask v2)"""
    try:
        from flask_auth_utils import get_user_email_flask
        from user_preferences import get_user_theme, get_user_ai_model
        from streamlit_utils import get_available_funds
        from ollama_client import list_available_models, check_ollama_health
        from searxng_client import check_searxng_health
        
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        default_model = get_user_ai_model()
        
        # Get available funds
        available_funds = get_available_funds()
        
        # Get available models
        ollama_models = list_available_models()
        ollama_available = check_ollama_health()
        searxng_available = check_searxng_health()
        
        # Check for WebAI models
        try:
            from ai_service_keys import get_model_display_name
            webai_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-pro"]
            has_webai = True
        except (ImportError, FileNotFoundError):
            webai_models = []
            has_webai = False
        
        # Get navigation context
        nav_context = get_navigation_context(current_page='ai_assistant')
        
        return render_template('ai_assistant.html',
                             user_email=user_email,
                             user_theme=user_theme,
                             default_model=default_model,
                             available_funds=available_funds,
                             ollama_models=ollama_models,
                             ollama_available=ollama_available,
                             searxng_available=searxng_available,
                             webai_models=webai_models,
                             has_webai=has_webai,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error loading AI assistant page: {e}", exc_info=True)
        return jsonify({"error": "Failed to load AI assistant page"}), 500

@app.route('/api/v2/ai/models', methods=['GET'])
@require_auth
def api_ai_models():
    """Get available AI models"""
    try:
        from ollama_client import list_available_models
        try:
            from ai_service_keys import get_model_display_name
        except ImportError:
            def get_model_display_name(m): return m

        all_models = list_available_models()
        
        formatted_models = []
        for model in all_models:
            is_webai = model.startswith('gemini-')
            display_name = model
            
            if is_webai:
                try:
                    display_name = get_model_display_name(model)
                    # Add sparkle to webai models if not already there
                    if 'AI' in display_name or 'Gemini' in display_name:
                         display_name = f"✨ {display_name}"
                except:
                    pass
            
            formatted_models.append({
                'id': model,
                'name': display_name,
                'type': 'webai' if is_webai else 'ollama'
            })
        
        return jsonify({"models": formatted_models})
    except Exception as e:
        logger.error(f"Error fetching AI models: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/context/build', methods=['POST'])
# Context build endpoint - v2
@require_auth
def api_ai_context_build():
    """Build context string with portfolio data tables (called by JS before chat)"""
    try:
        from flask_auth_utils import get_user_id_flask
        from ai_context_builder import (
            format_holdings, format_thesis, format_trades, 
            format_performance_metrics, format_cash_balances
        )
        from streamlit_utils import (
            get_current_positions, get_trade_log, get_cash_balances,
            calculate_portfolio_value_over_time, get_fund_thesis_data,
            calculate_performance_metrics
        )
        
        data = request.get_json()
        fund = data.get('fund')
        
        logger.info(f"[Context Build] Request received for fund: {fund}")
        
        if not fund:
            logger.warning("[Context Build] No fund specified, returning empty context")
            return jsonify({"context_string": "", "char_count": 0})

        context_parts = []
        
        # --- Always Included: Holdings with all data tables ---
        positions_df = get_current_positions(fund)
        trades_df = get_trade_log(limit=100, fund=fund)
        
        logger.info(f"[Context Build] Positions count: {len(positions_df) if positions_df is not None else 0}")
        logger.info(f"[Context Build] Trades count: {len(trades_df) if trades_df is not None else 0}")
        
        include_pv = data.get('include_price_volume', True)
        include_fund = data.get('include_fundamentals', True)
        
        if not positions_df.empty:
            holdings_text = format_holdings(
                positions_df,
                fund,
                trades_df=trades_df,
                include_price_volume=include_pv,
                include_fundamentals=include_fund
            )
            context_parts.append(holdings_text)
            logger.info(f"[Context Build] Holdings text length: {len(holdings_text)}")
        else:
            logger.warning(f"[Context Build] No positions found for fund: {fund}")
        
        # --- Always Included: Performance Metrics ---
        try:
            metrics = calculate_performance_metrics(fund)
            portfolio_df = calculate_portfolio_value_over_time(fund, days=365)
            if metrics:
                context_parts.append(format_performance_metrics(metrics, portfolio_df))
                logger.info(f"[Context Build] Performance metrics added")
        except Exception as e:
            logger.warning(f"Error loading performance metrics: {e}")
        
        # --- Always Included: Cash Balances ---
        try:
            cash = get_cash_balances(fund)
            if cash:
                context_parts.append(format_cash_balances(cash))
                logger.info(f"[Context Build] Cash balances added")
        except Exception as e:
            logger.warning(f"Error loading cash balances: {e}")
        
        # --- Optional: Thesis ---
        if data.get('include_thesis', False):
            try:
                thesis_data = get_fund_thesis_data(fund)
                if thesis_data:
                    context_parts.append(format_thesis(thesis_data))
            except Exception as e:
                logger.warning(f"Error loading thesis: {e}")
        
        # --- Optional: Trades ---
        if data.get('include_trades', False):
            try:
                if trades_df is not None and not trades_df.empty:
                    context_parts.append(format_trades(trades_df, limit=100))
            except Exception as e:
                logger.warning(f"Error loading trades: {e}")
        
        # Combine all parts
        context_string = "\n\n---\n\n".join(context_parts) if context_parts else ""
        
        logger.info(f"[Context Build] Final context length: {len(context_string)} chars, {len(context_parts)} parts")
        
        return jsonify({
            "context_string": context_string,
            "char_count": len(context_string)
        })
        
    except Exception as e:
        logger.error(f"Error building context: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/context', methods=['GET', 'POST'])
@require_auth
def api_ai_context():
    """Get or update context items"""
    try:
        from flask_auth_utils import get_user_id_flask
        from chat_context import ContextItemType, ContextItem
        import json as json_lib
        
        user_id = get_user_id_flask()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        # Initialize context in session if needed
        if 'ai_context_items' not in session:
            session['ai_context_items'] = []
        
        if request.method == 'GET':
            # Return current context items
            context_items = session.get('ai_context_items', [])
            # Convert to serializable format
            items = []
            for item_dict in context_items:
                items.append({
                    'item_type': item_dict['item_type'],
                    'fund': item_dict.get('fund'),
                    'metadata': item_dict.get('metadata', {})
                })
            return jsonify({"items": items})
        
        elif request.method == 'POST':
            # Add or remove context item
            data = request.get_json()
            action = data.get('action')  # 'add' or 'remove'
            item_type_str = data.get('item_type')
            fund = data.get('fund')
            metadata = data.get('metadata', {})
            
            try:
                item_type = ContextItemType(item_type_str)
            except ValueError:
                return jsonify({"error": f"Invalid item type: {item_type_str}"}), 400
            
            context_items = session.get('ai_context_items', [])
            
            # Create item dict for comparison
            item_dict = {
                'item_type': item_type_str,
                'fund': fund,
                'metadata': metadata
            }
            
            if action == 'add':
                # Check if already exists
                if item_dict not in context_items:
                    context_items.append(item_dict)
                    session['ai_context_items'] = context_items
                    return jsonify({"success": True, "message": "Item added"})
                else:
                    return jsonify({"success": False, "message": "Item already exists"})
            
            elif action == 'remove':
                if item_dict in context_items:
                    context_items.remove(item_dict)
                    session['ai_context_items'] = context_items
                    return jsonify({"success": True, "message": "Item removed"})
                else:
                    return jsonify({"success": False, "message": "Item not found"})
            
            elif action == 'clear':
                session['ai_context_items'] = []
                return jsonify({"success": True, "message": "All items cleared"})
            
            else:
                return jsonify({"error": f"Invalid action: {action}"}), 400
    
    except Exception as e:
        logger.error(f"Error managing context: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500





@app.route('/api/v2/ai/repository', methods=['POST'])
@require_auth
def api_ai_repository():
    """Search research repository (RAG)"""
    try:
        from ollama_client import get_ollama_client, check_ollama_health
        from research_repository import ResearchRepository
        
        if not check_ollama_health():
            return jsonify({"error": "Ollama unavailable (required for embeddings)"}), 503
        
        data = request.get_json()
        user_query = data.get('query', '')
        max_results = data.get('max_results', 3)
        min_similarity = data.get('min_similarity', 0.6)
        
        # Generate embedding
        client = get_ollama_client()
        if not client:
            return jsonify({"error": "Ollama client not available"}), 503
        
        query_embedding = client.generate_embedding(user_query)
        if not query_embedding:
            return jsonify({"error": "Failed to generate embedding"}), 500
        
        # Search repository
        repo = ResearchRepository()
        articles = repo.search_similar_articles(
            query_embedding=query_embedding,
            limit=max_results,
            min_similarity=min_similarity
        )
        
        return jsonify({
            "success": True,
            "articles": articles
        })
    
    except Exception as e:
        logger.error(f"Error searching repository: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/portfolio-intelligence', methods=['POST'])
@require_auth
def api_ai_portfolio_intelligence():
    """Check portfolio news from research repository"""
    try:
        from research_repository import ResearchRepository
        from streamlit_utils import get_current_positions
        
        data = request.get_json()
        fund = data.get('fund')
        
        if not fund:
            return jsonify({"error": "Fund is required"}), 400
        
        # Initialize repository
        repo = ResearchRepository()
        
        # Get portfolio tickers
        portfolio_tickers = set()
        positions_df = get_current_positions(fund)
        if not positions_df.empty and 'ticker' in positions_df.columns:
            portfolio_tickers = {t.strip().upper() for t in positions_df['ticker'].dropna().unique()}
        
        if not portfolio_tickers:
            return jsonify({
                "success": False,
                "message": "No positions found in current portfolio to check.",
                "matching_articles": []
            })
        
        # Fetch recent articles
        recent_articles = repo.get_recent_articles(limit=50, days=7)
        
        # Filter for holdings
        matching_articles = []
        seen_titles = set()
        
        for article in recent_articles:
            article_tickers = article.get('tickers')
            if not article_tickers:
                continue
            
            art_ticker_set = {t.upper() for t in article_tickers}
            matches = art_ticker_set.intersection(portfolio_tickers)
            
            if matches and article['title'] not in seen_titles:
                matching_articles.append({
                    'title': article.get('title'),
                    'matched_holdings': list(matches),
                    'summary': article.get('summary', 'No summary'),
                    'conclusion': article.get('conclusion', 'N/A'),
                    'source': article.get('source', 'Unknown'),
                    'published_at': article.get('published_at', '')
                })
                seen_titles.add(article['title'])
        
        return jsonify({
            "success": True,
            "matching_articles": matching_articles,
            "count": len(matching_articles)
        })
    
    except Exception as e:
        logger.error(f"Error checking portfolio news: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v2/ai/chat', methods=['POST'])
@require_auth
def api_ai_chat():
    """Handle chat message and stream AI response"""
    try:
        from flask import Response, stream_with_context
        from flask_auth_utils import get_user_id_flask
        from chat_context import ContextItemType
        from ai_context_builder import (
            format_holdings, format_thesis, format_trades,
            format_performance_metrics, format_cash_balances
        )
        from streamlit_utils import (
            get_current_positions, get_trade_log, get_cash_balances,
            calculate_portfolio_value_over_time, get_fund_thesis_data,
            calculate_performance_metrics
        )
        from ai_prompts import get_system_prompt
        from search_utils import format_search_results
        from research_utils import escape_markdown
        import json as json_lib
        
        user_id = get_user_id_flask()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        data = request.get_json()
        user_query = data.get('query', '')
        model = data.get('model')
        fund = data.get('fund')
        context_items = data.get('context_items', [])
        conversation_history = data.get('conversation_history', [])
        include_search = data.get('include_search', False)
        include_repository = data.get('include_repository', False)
        search_results = data.get('search_results')  # Pre-computed search results
        repository_articles = data.get('repository_articles')  # Pre-computed repository results
        
        if not user_query:
            return jsonify({"error": "Query is required"}), 400
        
        # Use pre-built context string if provided (from caching), otherwise build it
        context_string = data.get('context_string', '')
        
        if not context_string:
            # Build context string from items
            context_parts = []
            
            for item_dict in context_items:
                item_type_str = item_dict['item_type']
                item_fund = item_dict.get('fund') or fund
                
                try:
                    item_type = ContextItemType(item_type_str)
                except ValueError:
                    continue
                
                try:
                    if item_type == ContextItemType.HOLDINGS:
                        positions_df = get_current_positions(item_fund)
                        trades_df = get_trade_log(limit=1000, fund=item_fund) if item_fund else None
                        include_pv = data.get('include_price_volume', True)
                        include_fund = data.get('include_fundamentals', True)
                        context_parts.append(
                            format_holdings(
                                positions_df,
                                item_fund or "Unknown",
                                trades_df=trades_df,
                                include_price_volume=include_pv,
                                include_fundamentals=include_fund
                            )
                        )
                    elif item_type == ContextItemType.THESIS:
                        thesis_data = get_fund_thesis_data(item_fund or "")
                        if thesis_data:
                            context_parts.append(format_thesis(thesis_data))
                    elif item_type == ContextItemType.TRADES:
                        limit = item_dict.get('metadata', {}).get('limit', 100)
                        trades_df = get_trade_log(limit=limit, fund=item_fund)
                        context_parts.append(format_trades(trades_df, limit))
                    elif item_type == ContextItemType.METRICS:
                        portfolio_df = calculate_portfolio_value_over_time(item_fund, days=365) if item_fund else None
                        metrics = calculate_performance_metrics(item_fund) if item_fund else {}
                        context_parts.append(format_performance_metrics(metrics, portfolio_df))
                    elif item_type == ContextItemType.CASH_BALANCES:
                        cash = get_cash_balances(item_fund) if item_fund else {}
                        context_parts.append(format_cash_balances(cash))
                except Exception as e:
                    logger.warning(f"Error loading {item_type_str}: {e}")
                    continue
            
            context_string = "\n\n---\n\n".join(context_parts) if context_parts else ""
        
        # Add search results if provided (always add these dynamically)
        if search_results and search_results.get('formatted'):
            if context_string:
                context_string = f"{context_string}\n\n---\n\n{search_results['formatted']}"
            else:
                context_string = search_results['formatted']
        
        # Add repository articles if provided (always add these dynamically)
        if repository_articles:
            articles_text = "## Relevant Research from Repository:\n\n"
            for i, article in enumerate(repository_articles, 1):
                similarity = article.get('similarity', 0)
                title = article.get('title', 'Untitled')
                summary = escape_markdown(article.get('summary', article.get('content', '')[:300]))
                source = article.get('source', 'Unknown')
                published = article.get('published_at', '')
                
                articles_text += f"### Article {i} (Similarity: {similarity:.2%})\n"
                articles_text += f"**{title}**\n"
                articles_text += f"*Source: {source}"
                if published:
                    articles_text += f" | Published: {published}"
                articles_text += "*\n\n"
                if summary:
                    articles_text += f"{summary}\n\n"
                articles_text += "---\n\n"
            
            if context_string:
                context_string = f"{context_string}\n\n{articles_text}"
            else:
                context_string = articles_text
        
        # Generate prompt using context items
        # Simple prompt generation (can be enhanced later)
        if context_items:
            # Build a descriptive prompt based on context items
            item_types = [item.get('item_type') for item in context_items]
            if 'holdings' in item_types and 'thesis' in item_types:
                prompt = f"Based on the portfolio holdings and investment thesis provided above, analyze how well the current positions align with the stated investment strategy. {user_query}"
            elif 'trades' in item_types:
                prompt = f"Based on the trading activity data provided above, analyze recent trades and review trade patterns. {user_query}"
            elif 'metrics' in item_types:
                prompt = f"Based on the performance metrics data provided above, analyze portfolio performance. {user_query}"
            else:
                prompt = f"Based on the portfolio data provided above, {user_query}"
        else:
            prompt = user_query
        
        # Combine context and prompt
        full_prompt = prompt
        if context_string:
            full_prompt = f"{context_string}\n\n{prompt}"
        
        # Get system prompt
        system_prompt = get_system_prompt()
        
        # Check if using WebAI or Ollama
        if model and model.startswith("gemini-"):
            # WebAI (non-streaming)
            try:
                from webai_wrapper import PersistentConversationSession
                from ai_service_keys import get_model_display_name_short
                
                # Get or create session
                session_key = f'webai_session_{user_id}'
                if session_key not in session:
                    session[session_key] = PersistentConversationSession(
                        session_id=user_id,
                        auto_refresh=False,
                        model=model,
                        system_prompt=system_prompt
                    )
                
                webai_session = session[session_key]
                
                # For WebAI, include instructions in message
                webai_instructions = (
                    "You are an AI portfolio assistant. Analyze the provided portfolio data, "
                    "news, and research articles to provide insights. Be concise and actionable.\n\n"
                )
                webai_message = webai_instructions + full_prompt
                
                # Send message (non-streaming)
                full_response = webai_session.send_sync(webai_message)
                
                return jsonify({
                    "response": full_response,
                    "model": model,
                    "streaming": False
                })
            
            except Exception as e:
                logger.error(f"WebAI error: {e}", exc_info=True)
                return jsonify({"error": f"WebAI error: {str(e)}"}), 500
        
        else:
            # Ollama (streaming)
            from ollama_client import get_ollama_client
            
            client = get_ollama_client()
            if not client:
                return jsonify({"error": "Ollama client not available"}), 503
            
            def generate():
                """Generator for streaming response"""
                try:
                    for chunk in client.query_ollama(
                        prompt=full_prompt,
                        model=model or "granite3.2:8b",
                        stream=True,
                        temperature=None,
                        max_tokens=None,
                        system_prompt=system_prompt
                    ):
                        yield f"data: {json_lib.dumps({'chunk': chunk, 'done': False})}\n\n"
                    
                    # Send done signal
                    yield f"data: {json_lib.dumps({'chunk': '', 'done': True})}\n\n"
                
                except Exception as e:
                    logger.error(f"Streaming error: {e}", exc_info=True)
                    error_msg = json_lib.dumps({'error': str(e), 'done': True})
                    yield f"data: {error_msg}\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'  # Disable nginx buffering
                }
            )
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the app
    # Use port 5001 to avoid conflict with NFT calculator app on port 5000
    port = int(os.getenv('FLASK_PORT', '5001'))
    app.run(debug=True, host='0.0.0.0', port=port)
