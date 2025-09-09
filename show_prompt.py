#!/usr/bin/env python3
"""
Show Complete LLM Prompt

This script shows you the complete prompt that you should copy and paste into your LLM.
"""

from market_config import get_daily_instructions, get_market_info, ACTIVE_MARKET
from dual_currency import load_cash_balances, format_cash_display
from trading_script import DATA_DIR, last_trading_date
import pandas as pd

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
    
    print("[ Portfolio Snapshot ]")
    print("Empty DataFrame")
    print("Columns: [ticker, shares, stop_loss, buy_price, cost_basis]")
    print("Index: []")
    
    # Cash balance
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
    
    print("[ Holdings ]")
    print("Empty DataFrame")
    print("Columns: [ticker, shares, stop_loss, buy_price, cost_basis]")
    print("Index: []")
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
