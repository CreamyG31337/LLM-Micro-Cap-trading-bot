import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import numpy as np 

# === Process one AI's portfolio ===
def process_portfolio(portfolio, label, starting_cash):
    results = []
    total_value = 0
    total_pnl = 0
    cash = starting_cash
    for _, stock in portfolio.iterrows():
        ticker = stock["ticker"]
        shares = int(stock["shares"])
        cost = stock["cost_basis"]
        stop = stock["stop_loss"]

        data = yf.Ticker(ticker).history(period="1d")

        if data.empty:
            print(f"[{label}] No data for {ticker}")
            row = {
                "Date": today,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": "",
                "Total Value": "",
                "PnL": "",
                "Action": "NO DATA",
                "Cash Balance": "",
                "Total Equity": ""
            }
        else:
            price = round(data["Close"].iloc[-1], 2)
            value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)

            if price <= stop:
                action = "SELL - Stop Loss Triggered"
                cash += value
                log_sell(label, ticker, shares, price, cost, pnl, action)
            else:
                action = "HOLD"
                total_value += value
                total_pnl += pnl

            row = {
                "Date": today,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": price,
                "Total Value": value,
                "PnL": pnl,
                "Action": action,
                "Cash Balance": "",
                "Total Equity": ""
            }

        results.append(row)

    # === Add TOTAL row ===
    total_row = {
        "Date": today,
        "Ticker": "TOTAL",
        "Shares": "",
        "Cost Basis": "",
        "Stop Loss": "",
        "Current Price": "",
        "Total Value": round(total_value, 2),
        "PnL": round(total_pnl, 2),
        "Action": "",
        "Cash Balance": round(cash, 2),
        "Total Equity": round(total_value + cash, 2)
    }
    results.append(total_row)

    # === Save to CSV ===
    file = f"{label.lower()}_portfolio_update.csv"
    df = pd.DataFrame(results)

    if os.path.exists(file):
        existing = pd.read_csv(file)
        existing = existing[existing["Date"] != today]  # Remove today's rows
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(file, index=False)
    return file, df

# === Trade Logger (purely for stoplosses)===
def log_sell(label, ticker, shares, price, cost, pnl):
    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Sold": shares,
        "Sell Price": price,
        "Cost Basis": cost,
        "PnL": pnl,
        "Reason": "AUTOMATED SELL - STOPLOSS TRIGGERED"
    }

    file = f"{label.lower()}_trade_log.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(file, index=False)

# === Manual Buy Logger ===

def log_manual_buy(buy_price, shares, ticker, cash, stoploss, chatgpt_portfolio):
    check = input(f"""You are currently trying to buy {ticker}.
                   If this a mistake enter 1.""")
    if check == "1":
        raise SystemExit("Please remove this function call.")

    data = yf.download(ticker, period="1d")
    if data.empty:
        SystemExit(f"error, could not find ticker {ticker}")
    if buy_price * shares > cash:
        SystemExit(f"error, you have {cash} but are trying to spend {buy_price * shares}. Are you sure you can do this?")
    pnl = 0.0

    log = {
            "Date": today,
            "Ticker": ticker,
            "Shares Bought": shares,
            "Buy Price": buy_price,
            "Cost Basis": buy_price * shares,
            "PnL": pnl,
            "Reason": "MANUAL BUY - New position"
            }

    file = "chatgpt_trade_log.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(file, index=False)
    new_trade = {"ticker": ticker, "shares": shares, "stop_loss": stoploss, "cost_basis": buy_price}
    new_trade = pd.DataFrame([new_trade])
    chatgpt_portfolio = pd.concat([chatgpt_portfolio, new_trade], ignore_index=True)
    return cash - shares * buy_price, chatgpt_portfolio


#work in progress currently

def log_manual_sell(buy_price, sell_price, pnl, shares, ticker, cash, chatgpt_portfolio):
    if isinstance(chatgpt_portfolio, list):
        chatgpt_portfolio = pd.DataFrame(chatgpt_portfolio)
    if ticker not in chatgpt_portfolio["ticker"].values:
        print(f"error, could not find ticker {ticker}")
    
    reason = input("""Why are you selling? 
If this is a mistake, enter 1. """)

    if reason == "1": 
        raise SystemExit("Delete this function call from the program.")

    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Bought": "",  # leave buy fields empty
        "Buy Price": "",
        "Cost Basis": buy_price * shares,  # original invested amount
        "PnL": pnl,
        "Reason": f"MANUAL SELL - {reason}",
        "Shares Sold": shares,
        "Sell Price": sell_price
    }
    file = "chatgpt_trade_log.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(file, index=False)
    chatgpt_portfolio = chatgpt_portfolio[chatgpt_portfolio["ticker"] != ticker]
    return cash + shares * sell_price, chatgpt_portfolio

# This is where chatGPT gets daily updates from
# I give it data on its portfolio and also other tickers if requested
# Right now it additionally wants "^RUT", "IWO", and "XBI"

def daily_results(chatgpt_portfolio):
    chatgpt_portfolio = chatgpt_portfolio.to_dict(orient="records")
    print(f"prices and updates for {today}")
    for stock in chatgpt_portfolio + [{"ticker": "^RUT"}] + [{"ticker": "IWO"}] + [{"ticker": "XBI"}]:
        ticker = stock['ticker']
        data = yf.download(ticker, period="2d")
        price = float(data['Close'].iloc[-1].item())
        last_price = float(data['Close'].iloc[-2].item())
        percent_change = ((price - last_price) / last_price) * 100
        volume = float(data['Volume'].iloc[-1].item())
        print(f"{ticker} closing price: {price:.2f}")
        print(f"{ticker} volume for today: ${volume:,}")
        print(f"percent change from the day before: {percent_change:.2f}%")
    chatgpt_df = pd.read_csv("chatgpt_portfolio_update.csv")

    # Filter TOTAL rows and get latest equity
    chatgpt_totals = chatgpt_df[chatgpt_df['Ticker'] == 'TOTAL'].copy() 
    chatgpt_totals['Date'] = pd.to_datetime(chatgpt_totals['Date'])
    final_date = chatgpt_totals['Date'].max()
    final_value = chatgpt_totals[chatgpt_totals['Date'] == final_date]
    final_equity = final_value['Total Equity'].values[0]
    print(f"Latest ChatGPT Equity: ${final_equity:.2f}")

# Define start and end date for Russell 2000

# Get Russell 2000 data
    russell = yf.download("^RUT", start="2025-06-27", end=final_date + pd.Timedelta(days=1))
    russell = russell.reset_index()[["Date", "Close"]].rename(columns={"Close": "Russell_Close"})


# Normalize to $100
    initial_price = russell["Russell_Close"].iloc[0].item()
    price_now = russell["Russell_Close"].iloc[-1].item()
    scaling_factor = 100 / initial_price
    russell_value = price_now * scaling_factor
    print(f"$100 Invested in the Russell 2000 Index: ${russell_value:.2f}")

    

# === Run Portfolio ===
today = datetime.today().strftime('%Y-%m-%d')
cash = 2.32

chatgpt_portfolio = [
    {"ticker": "ABEO", "shares": 6, "stop_loss": 4.90, "cost_basis": 5.77},
    {"ticker": "CADL", "shares": 5, "stop_loss": 4.03, "cost_basis": 5.04},
    {"ticker": "AZTR", "shares": 55, "stop_loss": 0.18, "cost_basis": 0.25},
    {"ticker": "IINN", "shares": 20, "stop_loss": 1.10, "cost_basis": 1.5},
]

portfolio = pd.DataFrame(chatgpt_portfolio)
cash, chatgpt_portfolio = log_manual_sell(5.04, 6.59, 8.5, 5, "CADL", cash, chatgpt_portfolio)
cash, chatgpt_portfolio = log_manual_buy(5.75, 6, "ACTU", cash, 4.89, chatgpt_portfolio)
portfolio = pd.DataFrame(chatgpt_portfolio)
chatgpt_file, chatgpt_df = process_portfolio(portfolio, "ChatGPT", cash)

daily_results(portfolio)