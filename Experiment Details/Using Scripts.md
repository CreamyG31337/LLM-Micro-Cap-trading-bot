# Scripts

**Note: NONE OF THE PROMPTS ARE AUTOMATED, MANUAL UPDATES AND DEEP RESEARCH IS REQUIRED**
## Generate_Graph.py

Pretty simple — it grabs the daily logs from `'chatgpt_portfolio_update.csv'` and then plots the results alongside S&P 500 returns (adjusted for $100).  
To run, just make sure there's data in `'chatgpt_portfolio_update.csv'`, then run the script to generate the plot.

---

## Trading_Script.py

The trading script tracks positions, logs trades, and prints daily results.

### 1. Daily Results

Gets trading data for the day (as long as the trading day has closed).
If it's not a trading day, it will use data from the previous day.
It will also print the updated portfolio and cash. **If any manual trades were made, be sure to copy both and update the code.**
By default the function also reports the Russell 2000 (`^RUT`), IWO, and XBI for comparison.

To add additional tickers without modifying the portfolio:

Before:

```python
# say we want data from SPY
for stock in chatgpt_portfolio + [{"ticker": "^RUT"}] + [{"ticker": "IWO"}] + [{"ticker": "XBI"}]:
    print(stock)
```

After:

```python
for stock in chatgpt_portfolio + [{"ticker": "^RUT"}] + [{"ticker": "IWO"}] + [{"ticker": "XBI"}] + [{"ticker": "SPY"}]:
    print(stock)
```
That's it!

### Process Portfolio
Handles stop-losses, updates `'chatgpt_portfolio_update.csv'`, and now prompts for manual trades before processing.

When prompted you can enter:

- `b` to log a manual buy (ticker, shares, buy price, and stop loss)
- `s` to log a manual sell (ticker, shares, and sell price)
- press **Enter** to skip

Any manual trades are saved to `chatgpt_trade_log.csv`.

### Putting It Together
At the bottom of your script, call:

```python
chatgpt_portfolio = process_portfolio(chatgpt_portfolio, cash)
daily_results(chatgpt_portfolio, cash)
```

`process_portfolio` will ask about manual trades and update the CSV files automatically before `daily_results` prints the day's metrics.
