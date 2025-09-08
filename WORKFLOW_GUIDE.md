# Daily Trading Workflow Guide

## 🔄 **How to Use the System Daily**

You only need to run **ONE script** each day. Here's the complete workflow:

### **Step 1: Run the Trading Script**
```bash
python trading_script.py --file "Start Your Own/chatgpt_portfolio_update.csv"
```

### **Step 2: What the Script Does**
1. **Loads your portfolio** from the CSV file
2. **Shows your cash balances** (CAD and USD if in North American mode)
3. **Asks if you want to make manual trades** (supports fractional shares - press Enter to skip)
4. **Fetches current market data** for benchmarks
5. **Generates performance metrics** (Sharpe ratio, drawdown, etc.)
6. **Creates the LLM prompt** with all your data

### **Step 3: Copy the LLM Prompt**
The script outputs a complete report that looks like this:

```
================================================================
Daily Results — 2025-09-05
================================================================

[ Price & Volume ]
Ticker            Close     % Chg          Volume
-------------------------------------------------
SPY              647.24    -0.29%      85,178,935
QQQ              576.06    +0.14%      68,342,532
IWM              237.77    +0.50%      47,542,498

[ Snapshot ]
Cash Balances: CAD $123.00 | USD $123.00
Total (CAD equiv): $289.05

[ Holdings ]
Empty DataFrame (or your current positions)

[ Your Instructions ]
Use this info to make decisions regarding your North American small-cap portfolio. You have complete control over every decision. Make any changes you believe are beneficial—no approval required.

INVESTMENT UNIVERSE:
- Canadian small-caps: CAD 50M - CAD 500M market cap (TSX/TSX Venture Exchange)  
- US small-caps: USD 40M - USD 400M market cap (NYSE, NASDAQ, etc.)
- You can trade in BOTH markets - choose the best opportunities regardless of country

CURRENCY MANAGEMENT:
- Canadian positions trade in CAD
- US positions trade in USD  
- You can maintain separate CAD/USD cash balances
- Consider currency exposure as part of your strategy

KEY CONSIDERATIONS:
- Compare opportunities across both markets
- Account for currency exchange rates (CAD/USD)
- Consider different trading hours (TSX vs US markets)
- Canadian regulatory environment (CSA) vs US (SEC)
- Liquidity differences between markets

TICKER FORMATS:
- Canadian: Use .TO suffix (e.g., SHOP.TO for TSX, ABC.V for TSX-V)
- US: No suffix needed (e.g., AAPL, TSLA)

Deep research is not permitted. Act at your discretion to achieve the best outcome.
If you do not make a clear indication to change positions IMMEDIATELY after this message, the portfolio remains unchanged for tomorrow.
You are encouraged to research both Canadian and US small-cap opportunities and choose the best prospects.

*Paste everything above into your preferred LLM (ChatGPT, Claude, Gemini, etc.)*
```

### **Step 4: Paste into Your LLM**
1. **Copy everything** from "Daily Results" to the end
2. **Paste into ChatGPT, Claude, Gemini, or your preferred LLM**
3. **Add context if needed:**
   ```
   You are a North American small-cap specialist. Analyze this portfolio data and recommend trades.
   ```

### **Step 5: Execute LLM Recommendations**
When your LLM responds with trade recommendations:
1. **Run the script again:**
   ```bash
   python trading_script.py --file "Start Your Own/chatgpt_portfolio_update.csv"
   ```
2. **Choose 'b' for buy or 's' for sell**
3. **Enter the recommended trades**
4. **Press Enter to continue** when done

## 🛠 **Troubleshooting**

### **If the prompt gets cut off:**
```bash
# Use this to see the complete prompt clearly
python show_prompt.py
```

### **If you want to see current configuration:**
```bash
python switch_market.py status
```

### **If you want to change market focus:**
```bash
python switch_market.py north_american  # Both US + Canada (recommended)
python switch_market.py canadian        # Canadian only
python switch_market.py us              # US only
```

## 📋 **Summary**
- **One script**: `trading_script.py` does everything
- **Daily routine**: Run script → Copy output → Paste to LLM → Execute trades
- **No multiple scripts**: Everything is integrated
- **Complete automation**: The script handles data, metrics, and prompt generation

The confusion might be because the terminal sometimes cuts off long outputs. The `show_prompt.py` script I created will show you exactly what to copy/paste if the main script output gets truncated.

## 🎯 **Your Daily Workflow**
1. `python trading_script.py --file "Start Your Own/chatgpt_portfolio_update.csv"`
2. Copy the complete output (from "Daily Results" onwards)
3. Paste into your preferred LLM
4. Execute the LLM's trade recommendations by running the script again
5. Repeat daily!

That's it! One script, one workflow, maximum AI-driven trading power! 🚀
