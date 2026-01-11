
from flask import Blueprint, jsonify, request, render_template, redirect, url_for
import logging
import time
import pandas as pd
from datetime import datetime, timezone
import json

from flask_auth_utils import get_user_email_flask
from user_preferences import get_user_theme, get_user_currency, get_user_selected_fund, get_user_preference
from app import get_navigation_context
from streamlit_utils import (
    get_current_positions,
    get_trade_log,
    get_cash_balances,
    calculate_portfolio_value_over_time,
    get_user_investment_metrics,
    get_fund_thesis_data,
    fetch_latest_rates_bulk,
    get_investor_count
)

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/v2/dashboard')
def dashboard_page():
    """Render the main dashboard page"""
    try:
        # Check V2 Preference
        v2_enabled = get_user_preference('v2_enabled', default=False)
        if not v2_enabled:
            # If V2 is disabled, redirect to Streamlit (root)
            return redirect('/')
            
        user_email = get_user_email_flask()
        user_theme = get_user_theme() or 'system'
        
        # Determine initial fund
        selected_fund = get_user_selected_fund()
        
        # Navigation context
        nav_context = get_navigation_context(current_page='dashboard')
        
        return render_template('dashboard.html',
                             user_email=user_email,
                             user_theme=user_theme,
                             initial_fund=selected_fund,
                             **nav_context)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}", exc_info=True)
        return render_template('error.html', error=str(e), user_theme='system')

@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get top-level dashboard metrics"""
    fund = request.args.get('fund')
    display_currency = get_user_currency() or 'CAD'
    
    start_time = time.time()
    
    try:
        # Fetch Data
        positions_df = get_current_positions(fund)
        cash_balances = get_cash_balances(fund)
        
        # Calculate Rates
        all_currencies = set()
        if not positions_df.empty:
            all_currencies.update(positions_df['currency'].fillna('CAD').astype(str).str.upper().unique().tolist())
        all_currencies.update([str(c).upper() for c in cash_balances.keys()])
        
        rate_map = fetch_latest_rates_bulk(list(all_currencies), display_currency)
        def get_rate(curr): return rate_map.get(str(curr).upper(), 1.0)
        
        # Metrics Calculation
        portfolio_value_no_cash = 0.0
        total_pnl = 0.0
        day_pnl = 0.0
        
        if not positions_df.empty:
            rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate)
            portfolio_value_no_cash = (positions_df['market_value'].fillna(0) * rates).sum()
            total_pnl = (positions_df['unrealized_pnl'].fillna(0) * rates).sum()
            
            if 'daily_pnl' in positions_df.columns:
                 day_pnl = (positions_df['daily_pnl'].fillna(0) * rates).sum()
        
        # Cash
        total_cash = 0.0
        for curr, amount in cash_balances.items():
            if amount > 0:
                total_cash += amount * get_rate(curr)
                
        total_value = portfolio_value_no_cash + total_cash
        
        # Percentages
        day_pnl_pct = 0.0
        if (total_value - day_pnl) > 0:
            day_pnl_pct = (day_pnl / (total_value - day_pnl)) * 100
            
        unrealized_pnl_pct = 0.0
        cost_basis = portfolio_value_no_cash - total_pnl
        if cost_basis > 0:
            unrealized_pnl_pct = (total_pnl / cost_basis) * 100
            
        # Thesis Data
        thesis = get_fund_thesis_data(fund) if fund else None
        
        response = {
            "total_value": total_value,
            "cash_balance": total_cash,
            "day_change": day_pnl,
            "day_change_pct": day_pnl_pct,
            "unrealized_pnl": total_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "display_currency": display_currency,
            "thesis": thesis,
            "from_cache": False,
            "processing_time": time.time() - start_time
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error calculating dashboard summary: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route('/api/dashboard/charts/performance', methods=['GET'])
def get_performance_chart():
    """Get portfolio value history for chart.
    
    GET /api/dashboard/charts/performance
    
    Query Parameters:
        fund (str): Fund name (optional)
        range (str): Time range - '1M', '3M', '6M', '1Y', or 'ALL' (default: 'ALL')
        
    Returns:
        JSON response with:
            - series (list): Array of series objects for ApexCharts:
                - name (str): Series name
                - data (list): Array of [timestamp_ms, value] pairs
            - color (str): Hex color code based on trend (green if positive, red if negative)
            
    Error Responses:
        500: Server error during data fetch
    """
    fund = request.args.get('fund')
    time_range = request.args.get('range', 'ALL') # '1M', '3M', '6M', '1Y', 'ALL'
    display_currency = get_user_currency() or 'CAD'
    
    try:
        days_map = {
            '1M': 30,
            '3M': 90,
            '6M': 180,
            '1Y': 365,
            'ALL': None
        }
        days = days_map.get(time_range)
        
        df = calculate_portfolio_value_over_time(fund, days=days, display_currency=display_currency)
        
        if df.empty:
            return jsonify({"data": []})
            
        # Format for ApexCharts: [[timestamp_ms, value], ...]
        # df should have 'date' and 'total_value' (or similar)
        # Check actual columns from calculate_portfolio_value_over_time
        # It typically returns: date, total_value, cash, invested
        
        data = []
        for _, row in df.iterrows():
            date_val = row['date']
            if date_val.tzinfo is None:
                # Naive datetime - assume UTC
                ts = int(date_val.replace(tzinfo=timezone.utc).timestamp() * 1000)
            else:
                # Already timezone-aware
                ts = int(date_val.timestamp() * 1000)
            val = row['total_value']
            data.append([ts, val])
            
        # Determine color based on trend (green if last > first)
        color = "#10B981" # Green
        if len(data) >= 2 and data[-1][1] < data[0][1]:
            color = "#EF4444" # Red
            
        return jsonify({
            "series": [{"name": "Portfolio Value", "data": data}],
            "color": color
        })
        
    except Exception as e:
        logger.error(f"Error fetching performance chart: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route('/api/dashboard/charts/allocation', methods=['GET'])
def get_allocation_charts():
    """Get allocation data (Sector, Asset Class, etc.).
    
    GET /api/dashboard/charts/allocation
    
    Query Parameters:
        fund (str): Fund name (optional)
        
    Returns:
        JSON response with:
            - sector (list): Array of sector allocation objects:
                - label (str): Sector name
                - value (float): Allocation value in display currency
            - asset_class (list): Array of asset class allocation objects (if implemented)
            
    Error Responses:
        500: Server error during data fetch
    """
    fund = request.args.get('fund')
    display_currency = get_user_currency() or 'CAD'
    
    try:
        positions_df = get_current_positions(fund)
        
        if positions_df.empty:
            return jsonify({"sector": [], "asset_class": []})
            
        # Need to convert values to display currency for accurate pie chart
        # Using simplified approach (assuming pre-calculated or bulk rate fetch)
        # Ideally pass display_currency to get_current_positions if it supported it, but it handles logic differently.
        # We'll do a quick conversion here similar to summary
        
        all_currencies = positions_df['currency'].fillna('CAD').astype(str).str.upper().unique().tolist()
        rate_map = fetch_latest_rates_bulk(all_currencies, display_currency)
        def get_rate(curr): return rate_map.get(str(curr).upper(), 1.0)
        
        rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate)
        positions_df['display_value'] = positions_df['market_value'].fillna(0) * rates
        
        # Sector Allocation
        # Use 'sector' column from securities join
        # Note: get_current_positions joins securities, but col names might be nested or flattened?
        # Looking at streamlit_utils.py: "securities(company_name, sector, industry...)"
        # PostgRest/Supabase usually returns nested dict unless flattened.
        # But `pd.json_normalize` might be needed if it's not handled.
        # Let's check `get_current_positions` implementation... it returns `pd.DataFrame(all_rows)`.
        # If headers are securities.sector it might be flattened or strict json.
        # Usually Supabase Python client returns nested dicts: row['securities']['sector'].
        
        # Let's normalize safely
        if 'securities' in positions_df.columns:
            # It's a column of dicts
            sec_df = pd.json_normalize(positions_df['securities'])
            positions_df['sector'] = sec_df['sector']
            # positions_df['industry'] = sec_df['industry']
        
        # Group by Sector
        sector_grp = positions_df.groupby('sector')['display_value'].sum().sort_values(ascending=False)
        total_val = sector_grp.sum()
        
        sector_data = []
        for sector, val in sector_grp.items():
            if not sector: sector = "Unknown"
            pct = (val / total_val) * 100
            if pct < 1: continue # Group small into other? Or just send all
            sector_data.append({"label": sector, "value": val})
            
        return jsonify({
            "sector": sector_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching allocation charts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route('/api/dashboard/holdings', methods=['GET'])
def get_holdings_data():
    """Get content for holdings table"""
    fund = request.args.get('fund')
    display_currency = get_user_currency() or 'CAD'
    
    try:
        positions_df = get_current_positions(fund)
        if positions_df.empty:
            return jsonify({"data": []})
            
        # Get rates
        all_currencies = positions_df['currency'].fillna('CAD').astype(str).str.upper().unique().tolist()
        rate_map = fetch_latest_rates_bulk(all_currencies, display_currency)
        def get_rate(curr): return rate_map.get(str(curr).upper(), 1.0)
        rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate)
        
        # Process data
        data = []
        for idx, row in positions_df.iterrows():
            ticker = row.get('ticker')
            
            # Handle nested securities data
            company_name = ticker # Default
            sector = ""
            if isinstance(row.get('securities'), dict):
                company_name = row['securities'].get('company_name') or ticker
                sector = row['securities'].get('sector') or ""
                
            qty = row.get('quantity', 0)
            price = row.get('average_buy_price', 0)
            current_price = row.get('current_price', 0)
            
            # Values in Display Currency
            rate = get_rate(row.get('currency', 'CAD'))
            market_val = (row.get('market_value', 0) or 0) * rate
            pnl = (row.get('unrealized_pnl', 0) or 0) * rate
            day_pnl = (row.get('daily_pnl', 0) or 0) * rate
            
            day_pnl_pct = 0.0
            prev_val = market_val - day_pnl
            if prev_val > 0:
                day_pnl_pct = (day_pnl / prev_val) * 100
            
            pnl_pct = 0.0
            cost = market_val - pnl
            if cost > 0:
                pnl_pct = (pnl / cost) * 100
                
            data.append({
                "ticker": ticker,
                "name": company_name,
                "sector": sector,
                "quantity": qty,
                "price": current_price * rate, # Price in display curr
                "value": market_val,
                "day_change": day_pnl,
                "day_change_pct": day_pnl_pct,
                "total_return": pnl,
                "total_return_pct": pnl_pct,
                "currency": row.get('currency', 'CAD') # Original currency
            })
            
        # Sort by value desc
        data.sort(key=lambda x: x['value'], reverse=True)
        
        return jsonify({"data": data})
        
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@dashboard_bp.route('/api/dashboard/activity', methods=['GET'])
def get_recent_activity():
    """Get recent transactions"""
    fund = request.args.get('fund')
    limit = int(request.args.get('limit', 10))
    display_currency = get_user_currency() or 'CAD'
    
    try:
        trades_df = get_trade_log(limit=limit, fund=fund)
        if trades_df.empty:
            return jsonify({"data": []})
        
        data = []
        for _, row in trades_df.iterrows():
            # Format logic
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
            ticker = row.get('ticker')
            action = "BUY" if row.get('shares', 0) > 0 else "SELL"
            
            data.append({
                "date": date_str,
                "ticker": ticker,
                "action": action,
                "shares": abs(row.get('shares', 0)),
                "price": row.get('price', 0),
                "amount": abs(row.get('amount', 0)) # Assuming amount col exists, else calculate
            })
            
        return jsonify({"data": data})
        
    except Exception as e:
        logger.error(f"Error fetching activity: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
