#!/usr/bin/env python3
"""
Show Complete LLM Prompt

This script shows you the complete prompt that you should copy and paste into your LLM.
"""

from market_config import get_daily_instructions, get_market_info, ACTIVE_MARKET
from dual_currency import load_cash_balances, format_cash_display
from trading_script import DATA_DIR, last_trading_date, download_price_data, trading_day_window
import pandas as pd
import numpy as np

def calculate_position_metrics(portfolio_df, cash_balance):
    """Calculate enhanced position metrics for portfolio display"""
    if portfolio_df.empty:
        return pd.DataFrame()
    
    # Get current prices for all positions
    s, e = trading_day_window()
    enhanced_df = portfolio_df.copy()
    
    current_prices = []
    pnl_amounts = []
    pnl_percentages = []
    position_values = []
    position_weights = []
    daily_pnl_amounts = []
    daily_pnl_percentages = []
    days_held = []
    
    total_portfolio_value = 0
    
    for _, row in portfolio_df.iterrows():
        ticker = str(row.get('ticker', ''))
        
        # Fetch current price and previous day's price for daily P&L
        fetch = download_price_data(ticker, start=s, end=e, auto_adjust=False, progress=False)
        if not fetch.df.empty and "Close" in fetch.df.columns:
            current_price = float(fetch.df['Close'].iloc[-1].item())
            # Get previous day's price for daily P&L calculation
            if len(fetch.df) > 1:
                prev_price = float(fetch.df['Close'].iloc[-2].item())
            else:
                prev_price = current_price  # If only one day of data, no daily change
        else:
            current_price = float(row.get('buy_price', 0))
            prev_price = current_price
        
        shares = float(row.get('shares', 0))
        buy_price = float(row.get('buy_price', 0))
        cost_basis = float(row.get('cost_basis', 0))
        
        # Calculate total P&L since purchase
        position_value = current_price * shares
        actual_cost_basis = buy_price * shares
        total_pnl_amount = position_value - actual_cost_basis
        total_pnl_percent = (total_pnl_amount / actual_cost_basis * 100) if actual_cost_basis > 0 else 0
        
        # Calculate daily P&L change
        daily_pnl_amount = (current_price - prev_price) * shares
        daily_pnl_percent = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
        
        # Calculate days held (simplified - in real system you'd track purchase dates)
        days_held_approx = 1  # Default to 1 day for now
        
        current_prices.append(current_price)
        pnl_amounts.append(total_pnl_amount)
        pnl_percentages.append(total_pnl_percent)
        position_values.append(position_value)
        daily_pnl_amounts.append(daily_pnl_amount)
        daily_pnl_percentages.append(daily_pnl_percent)
        days_held.append(days_held_approx)
        
        total_portfolio_value += position_value
    
    # Calculate position weights
    for i, value in enumerate(position_values):
        weight = (value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        position_weights.append(weight)
    
    # Add calculated columns
    enhanced_df['Current_Price'] = current_prices
    enhanced_df['Position_Value'] = position_values
    enhanced_df['Total_PnL_Amount'] = pnl_amounts
    enhanced_df['Total_PnL_Percent'] = pnl_percentages
    enhanced_df['Daily_PnL_Amount'] = daily_pnl_amounts
    enhanced_df['Daily_PnL_Percent'] = daily_pnl_percentages
    enhanced_df['Days_Held'] = days_held
    enhanced_df['Weight_Percent'] = position_weights
    
    return enhanced_df, total_portfolio_value

def format_enhanced_portfolio_display(enhanced_df):
    """Format the enhanced portfolio display with better metrics"""
    if enhanced_df.empty:
        return "No current holdings"
    
    lines = []
    lines.append("Ticker        Shares    Buy Price  Current   Total P&L  Daily P&L  Weight %")
    lines.append("                                 $      %      $      %")
    lines.append("-" * 85)
    
    for _, row in enhanced_df.iterrows():
        ticker = str(row.get('ticker', ''))[:12].ljust(12)
        shares = f"{float(row.get('shares', 0)):.4f}".rjust(8)  # Show fractional shares with 4 decimal places
        buy_price = f"${float(row.get('buy_price', 0)):.2f}".rjust(9)
        current = f"${float(row.get('Current_Price', 0)):.2f}".rjust(8)
        
        # Total P&L (since purchase)
        total_pnl_amount = f"${float(row.get('Total_PnL_Amount', 0)):+.2f}".rjust(9)
        total_pnl_percent = f"{float(row.get('Total_PnL_Percent', 0)):+.1f}%".rjust(8)
        
        # Daily P&L (today's change)
        daily_pnl_amount = f"${float(row.get('Daily_PnL_Amount', 0)):+.2f}".rjust(9)
        daily_pnl_percent = f"{float(row.get('Daily_PnL_Percent', 0)):+.1f}%".rjust(8)
        
        weight = f"{float(row.get('Weight_Percent', 0)):.1f}%".rjust(9)
        
        lines.append(f"{ticker} {shares} {buy_price} {current} {total_pnl_amount} {total_pnl_percent} {daily_pnl_amount} {daily_pnl_percent} {weight}")
    
    return "\n".join(lines)

def calculate_portfolio_risk_metrics(enhanced_df, total_portfolio_value, cash_balance):
    """Calculate basic risk metrics for the portfolio"""
    if enhanced_df.empty:
        return {
            'concentration_risk': 0,
            'cash_allocation': 100,
            'total_positions': 0,
            'largest_position': 0,
            'portfolio_volatility': 0
        }
    
    # Concentration risk (largest position as % of portfolio)
    if not enhanced_df.empty:
        max_weight = enhanced_df['Weight_Percent'].max()
        largest_position = enhanced_df.loc[enhanced_df['Weight_Percent'].idxmax(), 'ticker']
    else:
        max_weight = 0
        largest_position = "N/A"
    
    # Cash allocation
    total_equity = total_portfolio_value + cash_balance
    cash_allocation = (cash_balance / total_equity * 100) if total_equity > 0 else 100
    
    # Portfolio volatility (simplified - average of individual position volatilities)
    # This is a basic approximation - in practice you'd calculate portfolio volatility properly
    portfolio_volatility = enhanced_df['Total_PnL_Percent'].std() if len(enhanced_df) > 1 else 0
    
    return {
        'concentration_risk': max_weight,
        'largest_position': largest_position,
        'cash_allocation': cash_allocation,
        'total_positions': len(enhanced_df),
        'portfolio_volatility': portfolio_volatility
    }

def show_complete_prompt():
    """Display the complete LLM prompt for the current configuration"""
    
    print("=" * 80)
    print("COMPLETE LLM PROMPT FOR COPY/PASTE")
    print("=" * 80)
    print()
    
    # Market info
    market_info = get_market_info()
    print(f"Current Market Configuration: {market_info['name']}")
    print(f"Currency: {market_info['currency']}")
    print(f"Market Cap Range: {market_info['market_cap']}")
    print()
    
    # Show what to copy/paste
    print("COPY EVERYTHING BELOW THIS LINE:")
    print("-" * 80)
    
    # This would normally come from your trading script output
    print("================================================================")
    print(f"Daily Results — {last_trading_date().date().isoformat()}")
    print("================================================================")
    print()
    
    print("[ Price & Volume ]")
    print("Ticker            Close     % Chg          Volume")
    print("-------------------------------------------------")
    print("SPY              647.24    -0.29%      85,178,935")
    print("QQQ              576.06    +0.14%      68,342,532")
    print("IWM              237.77    +0.50%      47,542,498")
    print("^GSPTSE               —         —               —")
    print()
    
    # Load actual portfolio data for enhanced display
    try:
        from trading_script import load_latest_portfolio_state
        portfolio_df, cash = load_latest_portfolio_state(str(DATA_DIR / "llm_portfolio_update.csv"))
        
        # Calculate enhanced metrics
        enhanced_df, total_portfolio_value = calculate_position_metrics(portfolio_df, cash)
        risk_metrics = calculate_portfolio_risk_metrics(enhanced_df, total_portfolio_value, cash)
        
        print("[ Enhanced Portfolio Analysis ]")
        if not enhanced_df.empty:
            print(format_enhanced_portfolio_display(enhanced_df))
        else:
            print("No current holdings")
        print()
        
        # Risk metrics
        print("[ Portfolio Risk Metrics ]")
        print(f"Total Positions: {risk_metrics['total_positions']}")
        print(f"Largest Position: {risk_metrics['largest_position']} ({risk_metrics['concentration_risk']:.1f}%)")
        print(f"Cash Allocation: {risk_metrics['cash_allocation']:.1f}%")
        if risk_metrics['portfolio_volatility'] > 0:
            print(f"Portfolio Volatility: {risk_metrics['portfolio_volatility']:.1f}%")
        print()
        
        # Cash balance
        if ACTIVE_MARKET == "NORTH_AMERICAN":
            try:
                cash_balances = load_cash_balances(DATA_DIR)
                print(f"Cash Balances: {format_cash_display(cash_balances)}")
                print(f"Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
            except:
                print(f"Cash Balance: ${cash:,.2f}")
        else:
            print(f"Cash Balance: ${cash:,.2f}")
        print()
        
        # Portfolio summary
        if not enhanced_df.empty:
            total_pnl = enhanced_df['Total_PnL_Amount'].sum()
            daily_pnl = enhanced_df['Daily_PnL_Amount'].sum()
            total_equity = total_portfolio_value + cash
            
            # Calculate performance metrics
            total_pnl_percent = (total_pnl / (total_portfolio_value - total_pnl) * 100) if (total_portfolio_value - total_pnl) > 0 else 0
            daily_pnl_percent = (daily_pnl / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            print(f"[ Portfolio Summary ]")
            print(f"Total Portfolio Value: ${total_portfolio_value:,.2f}")
            print(f"Total P&L (since purchase): ${total_pnl:+,.2f} ({total_pnl_percent:+.1f}%)")
            print(f"Daily P&L (today's change): ${daily_pnl:+,.2f} ({daily_pnl_percent:+.1f}%)")
            print(f"Total Equity: ${total_equity:,.2f}")
            print()
            
            # Performance context
            if daily_pnl > 0:
                print(f"[ Daily Performance ]")
                print(f"📈 Portfolio gained ${daily_pnl:,.2f} today ({daily_pnl_percent:+.1f}%)")
            elif daily_pnl < 0:
                print(f"[ Daily Performance ]")
                print(f"📉 Portfolio lost ${abs(daily_pnl):,.2f} today ({daily_pnl_percent:+.1f}%)")
            else:
                print(f"[ Daily Performance ]")
                print(f"➡️ Portfolio unchanged today (${daily_pnl:+,.2f})")
            print()
            
            # Top performers analysis
            if len(enhanced_df) > 1:
                best_performer = enhanced_df.loc[enhanced_df['Total_PnL_Percent'].idxmax()]
                worst_performer = enhanced_df.loc[enhanced_df['Total_PnL_Percent'].idxmin()]
                
                print(f"[ Top Performers ]")
                print(f"🏆 Best: {best_performer['ticker']} ({best_performer['Total_PnL_Percent']:+.1f}%)")
                print(f"📉 Worst: {worst_performer['ticker']} ({worst_performer['Total_PnL_Percent']:+.1f}%)")
                print()
        
    except Exception as e:
        print(f"[ Portfolio Snapshot ]")
        print("Error loading portfolio data - using fallback display")
        print("Empty DataFrame")
        print("Columns: [ticker, shares, stop_loss, buy_price, cost_basis]")
        print("Index: []")
        print()
        
        # Cash balance fallback
        if ACTIVE_MARKET == "NORTH_AMERICAN":
            try:
                cash_balances = load_cash_balances(DATA_DIR)
                print(f"Cash Balances: {format_cash_display(cash_balances)}")
                print(f"Total (CAD equiv): ${cash_balances.total_cad_equivalent():,.2f}")
            except:
                print("Cash Balance: $289.05")
        else:
            print("Cash Balance: $289.05")
        print()
    
    # The key part - the instructions
    print("[ Your Instructions ]")
    instructions = get_daily_instructions()
    print(instructions)
    
    print()
    print("-" * 80)
    print("COPY EVERYTHING ABOVE THIS LINE")
    print()
    print("Then paste it into your preferred LLM (ChatGPT, Claude, Gemini, etc.)")

if __name__ == "__main__":
    show_complete_prompt()
