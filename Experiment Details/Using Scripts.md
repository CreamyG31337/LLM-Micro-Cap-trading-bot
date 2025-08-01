# Scripts

**Note: NONE OF THE PROMPTS ARE AUTOMATED, MANUAL UPDATES AND DEEP RESEARCH IS REQUIRED**
## Generate_Graph.py

Pretty simple — it grabs the daily logs from `'chatgpt_portfolio_update.csv'` and then plots the results alongside S&P 500 returns (adjusted for $100).  
To run, just make sure there's data in `'chatgpt_portfolio_update.csv'`, then run the script to generate the plot.

---

## Trading_Script.py

A little more complicated, the order of function calls are very important (listed at the bottom). There are 4 main functions:

### 1. Daily Results

Gets trading data for the day (as long as the trading day has closed).  
If it's not a trading day, it will use data from the previous day.
It will also print the updated portfolio and cash. **If any manual trades were made, be sure to copy both and update the code.**
It will print data for all tickers in the `chatgpt_portfolio` Python dictionary.  
To add additional tickers without modifying the portfolio:

Before:

```python
# say we want data from SPY
for stock in chatgpt_portfolio + [{"ticker": "^RUT"}]:
    print(stock)
```

After:

```python
for stock in chatgpt_portfolio + [{"ticker": "^RUT"}] + [{"ticker": "SPY"}]:
    print(stock)
```
That's it!
### Process Portfolio
Way simplier, automatically handles stoplosses and updating the `'chatgpt_portfolio_update.csv'`

### Manual Buy/Sell

Both require parameters. Here is manual_buy:
```python
log_manual_buy(buy_price, shares, ticker, cash, stoploss, chatgpt_portfolio)
```

Say I wanted to buy "F" (Ford), with a limit order of 12.00, share count of 10, and a stoploss of 9.00.

That would look like:
```python
log_manual_buy(12.00, 10, "F", cash, 9.00, chatgpt_portfolio)
```
Cash and chatgpt_portfolio are already vars, so leave as is.

Now, for manual_sell:
```python
log_manual_sell(sell_price, shares_sold, ticker, cash, chatgpt_portfolio)
```

If I wanted to sell 3 shares of PFE (Pfizer), with a limit order of 23.00:

That would look like:
```python
log_manual_sell(23.00, 3, "PFE", cash, chatgpt_portfolio)
```

**NOTE: BOTH ORDERS WILL EXECUTE THE ORDER NO MATTER WHAT. BE SURE TO CHECK VALIDITY.**

## Function Call Order
1. Manual buying and selling
2. Process Portfolio
3. Daily Results

How would all this look?
At the very bottom, put:
```python
log_manual_sell(23.00, 3, "PFE", cash, chatgpt_portfolio)
log_manual_buy(12.00, 10, "F", cash, 9.00, chatgpt_portfolio)
chatgpt_portfolio = process_portfolio(chatgpt_portfolio, cash)
daily_results(chatgpt_portfolio, cash)
```
Of course, if no manual buys or sells were made, don't add those function calls.
