#!/usr/bin/env python3
"""
Show Complete LLM Prompt

This script shows you the complete prompt that you should copy and paste into your LLM.
"""

from market_config import get_daily_instructions, get_market_info, ACTIVE_MARKET
from dual_currency import load_cash_balances, format_cash_display
import argparse
from market_data.market_hours import MarketHours
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from display.console_output import _safe_emoji
import pandas as pd
import numpy as np
from pathlib import Path
import sys

def calculate_position_metrics(portfolio_df, cash_balance):
    """Calculate enhanced position metrics for portfolio display"""
    if portfolio_df.empty:
        return pd.DataFrame(), 0

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

        # Get current price from the row data
        current_price = float(row.get('current_price', row.get('buy_price', 0)))
        shares = float(row.get('shares', 0))
        buy_price = float(row.get('buy_price', 0))
        cost_basis = float(row.get('cost_basis', 0))

        # Use daily P&L from the data if available, otherwise calculate
        daily_pnl_str = row.get('daily_pnl', '$0.00')
        if daily_pnl_str and daily_pnl_str != 'N/A':
            # Parse the daily P&L string (e.g., "$123.45" -> 123.45)
            try:
                daily_pnl_amount = float(daily_pnl_str.replace('$', '').replace(',', '').replace('*', ''))
            except (ValueError, AttributeError):
                daily_pnl_amount = 0.0
        else:
            daily_pnl_amount = 0.0

        # Calculate total P&L since purchase
        position_value = current_price * shares
        actual_cost_basis = buy_price * shares
        total_pnl_amount = position_value - actual_cost_basis
        total_pnl_percent = (total_pnl_amount / actual_cost_basis * 100) if actual_cost_basis > 0 else 0

        # Calculate daily P&L percentage from the amount
        daily_pnl_percent = (daily_pnl_amount / position_value * 100) if position_value > 0 else 0

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
    lines.append("Ticker        Shares    Avg Price  Current   Total P&L        Daily P&L        5-Day P&L     Weight %")
    lines.append("                                              $      %            $      %          $      %")
    lines.append("-" * 104)
    
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
        
        # 5-Day P&L (use actual data if available)
        five_day_pnl_raw = str(row.get('five_day_pnl', 'N/A'))
        if five_day_pnl_raw != 'N/A' and '$' in five_day_pnl_raw:
            # Parse existing formatted string like "$+12.34 +5.6%"
            five_day_pnl_display = five_day_pnl_raw.rjust(15)
        else:
            five_day_pnl_display = "N/A".rjust(15)
        
        weight = f"{float(row.get('Weight_Percent', 0)):.1f}%".rjust(8)
        
        lines.append(f"{ticker} {shares} {buy_price} {current} {total_pnl_amount} {total_pnl_percent} {daily_pnl_amount} {daily_pnl_percent} {five_day_pnl_display} {weight}")
    
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

def show_complete_prompt(data_dir: str = None):
    """Display the complete LLM prompt for the current configuration
    
    Args:
        data_dir: Required data directory path
    """
    
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
    market_hours = MarketHours()
    print(f"Daily Results — {market_hours.last_trading_date_str()}")
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
        # Load portfolio using modular components (same as main script)
        from data.repositories.csv_repository import CSVRepository
        from portfolio.portfolio_manager import PortfolioManager

        if not data_dir:
            print("Error: Data directory is required")
            print("Usage: python show_prompt.py --data-dir <path>")
            return
        
        data_dir = Path(data_dir)
        repository = CSVRepository(data_dir)
        portfolio_manager = PortfolioManager(repository)

        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if latest_snapshot and latest_snapshot.positions:
            # Get portfolio snapshots for historical comparison
            portfolio_snapshots = portfolio_manager.get_portfolio_snapshots(limit=10)

            # Convert to enhanced format with daily P&L (same logic as main script)
            enhanced_positions = []
            for position in latest_snapshot.positions:
                pos_dict = {
                    'ticker': position.ticker,
                    'company': position.company or position.ticker,
                    'shares': float(position.shares),
                    'avg_price': float(position.avg_price),
                    'current_price': float(position.current_price) if position.current_price else float(position.avg_price),
                    'total_value': float(position.market_value) if position.market_value else 0,
                    'unrealized_pnl': float(position.unrealized_pnl) if position.unrealized_pnl else 0,
                    'cost_basis': float(position.cost_basis) if position.cost_basis else 0,
                    'opened_date': "N/A",  # Will be filled if available
                }

                # Calculate daily P&L using historical snapshots (same logic as main script)
                try:
                    daily_pnl_calculated = False
                    # Try to find daily P&L from multiple previous snapshots
                    for i in range(1, min(len(portfolio_snapshots), 4)):  # Check up to 3 previous snapshots
                        if len(portfolio_snapshots) > i:
                            previous_snapshot = portfolio_snapshots[-(i+1)]
                            # Find the same ticker in previous snapshot
                            prev_position = None
                            for prev_pos in previous_snapshot.positions:
                                if prev_pos.ticker == position.ticker:
                                    prev_position = prev_pos
                                    break

                            if prev_position and prev_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
                                daily_pnl_change = position.unrealized_pnl - prev_position.unrealized_pnl
                                pos_dict['daily_pnl'] = f"${daily_pnl_change:.2f}"
                                daily_pnl_calculated = True
                                break

                    if not daily_pnl_calculated:
                        # If no historical data, show current P&L as daily change for new positions
                        if position.unrealized_pnl is not None and abs(position.unrealized_pnl) > 0.01:
                            pos_dict['daily_pnl'] = f"${position.unrealized_pnl:.2f}*"  # * indicates new position
                        else:
                            pos_dict['daily_pnl'] = "$0.00"
                except Exception as e:
                    logger.debug(f"Could not calculate daily P&L for {position.ticker}: {e}")
                    pos_dict['daily_pnl'] = "$0.00"

                # Multi-day P&L calculation using historical data (5-day preferred, but show 2-4 day if available)
                try:
                    period_pnl_calculated = False
                    
                    # First try for 5-day P&L (snapshots 4-7 days back)
                    for i in range(4, min(len(portfolio_snapshots), 8)):  # Look for snapshots 4-7 days back
                        if len(portfolio_snapshots) > i:
                            period_snapshot = portfolio_snapshots[-(i+1)]
                            # Find the same ticker in historical snapshot
                            period_position = None
                            for period_pos in period_snapshot.positions:
                                if period_pos.ticker == position.ticker:
                                    period_position = period_pos
                                    break

                            if period_position and period_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
                                period_pnl_change = position.unrealized_pnl - period_position.unrealized_pnl
                                period_pct_change = ((position.current_price or position.avg_price) - (period_position.current_price or period_position.avg_price)) / (period_position.current_price or period_position.avg_price) * 100 if (period_position.current_price or period_position.avg_price) > 0 else 0
                                if period_pnl_change >= 0:
                                    pos_dict['five_day_pnl'] = f"${period_pnl_change:.2f} {period_pct_change:.1f}%"
                                else:
                                    pos_dict['five_day_pnl'] = f"${abs(period_pnl_change):.2f} {period_pct_change:.1f}%"
                                period_pnl_calculated = True
                                break
                    
                    # If no 5-day data, try for 2-4 day periods
                    if not period_pnl_calculated:
                        for days_back in [3, 2, 1]:  # Try 4-day, 3-day, 2-day periods
                            if len(portfolio_snapshots) > days_back:
                                period_snapshot = portfolio_snapshots[-(days_back+1)]
                                # Find the same ticker in historical snapshot
                                period_position = None
                                for period_pos in period_snapshot.positions:
                                    if period_pos.ticker == position.ticker:
                                        period_position = period_pos
                                        break

                                if period_position and period_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
                                    period_pnl_change = position.unrealized_pnl - period_position.unrealized_pnl
                                    period_pct_change = ((position.current_price or position.avg_price) - (period_position.current_price or period_position.avg_price)) / (period_position.current_price or period_position.avg_price) * 100 if (period_position.current_price or period_position.avg_price) > 0 else 0
                                    # Add day prefix to indicate partial period
                                    days_label = days_back + 1  # +1 because we're looking at snapshots back
                                    if period_pnl_change >= 0:
                                        pos_dict['five_day_pnl'] = f"{days_label}d: ${period_pnl_change:.2f} {period_pct_change:.1f}%"
                                    else:
                                        pos_dict['five_day_pnl'] = f"{days_label}d: ${abs(period_pnl_change):.2f} {period_pct_change:.1f}%"
                                    period_pnl_calculated = True
                                    break
                            
                            if period_pnl_calculated:
                                break
                    
                    if not period_pnl_calculated:
                        pos_dict['five_day_pnl'] = "N/A"
                except Exception as e:
                    pos_dict['five_day_pnl'] = "N/A"

                enhanced_positions.append(pos_dict)

            # Convert to DataFrame for display
            portfolio_df = pd.DataFrame(enhanced_positions)
            cash = 0.0  # Will be loaded separately
        else:
            portfolio_df = pd.DataFrame()
            cash = 0.0

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
                cash_balances = load_cash_balances(Path(data_dir))
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
            # Daily P&L percentage should be 0% when daily P&L amount is 0
            daily_pnl_percent = 0 if daily_pnl == 0 else (daily_pnl / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            print(f"[ Portfolio Summary ]")
            print(f"Total Portfolio Value: ${total_portfolio_value:,.2f}")
            print(f"Total P&L (since purchase): ${total_pnl:+,.2f} ({total_pnl_percent:+.1f}%)")
            print(f"Daily P&L (today's change): ${daily_pnl:+,.2f} ({daily_pnl_percent:+.1f}%)")
            print(f"Total Equity: ${total_equity:,.2f}")
            print()
            
            # Performance context
            if daily_pnl > 0:
                print(f"[ Daily Performance ]")
                print(f"{_safe_emoji('📈')} Portfolio gained ${daily_pnl:,.2f} today ({daily_pnl_percent:+.1f}%)")
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
        print(f"Error loading portfolio data: {e}")
        print("Empty DataFrame")
        print("Columns: [ticker, shares, stop_loss, buy_price, cost_basis]")
        print("Index: []")
        print()
        
        # Cash balance fallback
        if ACTIVE_MARKET == "NORTH_AMERICAN":
            try:
                cash_balances = load_cash_balances(Path(data_dir))
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

def main():
    """Main function for show_prompt script."""
    parser = argparse.ArgumentParser(description="Show complete LLM prompt")
    parser.add_argument("--data-dir", type=str, required=True, help="Data directory path")
    args = parser.parse_args()
    
    show_complete_prompt(args.data_dir)


if __name__ == "__main__":
    main()
