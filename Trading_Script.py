import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import numpy as np 

# === PORTFOLIOS ===
chatgpt_portfolio = [
    {"ticker": "ABEO", "shares": 6, "stop_loss": 4.90, "cost_basis": 5.77},
    {"ticker": "CADL", "shares": 5, "stop_loss": 4.03, "cost_basis": 5.04},
    {"ticker": "AZTR", "shares": 55, "stop_loss": 0.18, "cost_basis": 0.25},
    {"ticker": "IINN", "shares": 20, "stop_loss": 1.10, "cost_basis": 1.5},
]

# === Get last cash from portfolio file ===
def get_latest_cash(filename):
    if os.path.isfile(filename):
        try:
            df = pd.read_csv(filename)
            latest = df[df["Ticker"] == "TOTAL"].sort_values("Date").iloc[-1]
            return float(latest["Cash Balance"])
        except:
            return 0.0
    return 0.0

# === Process one AI's portfolio ===
def process_portfolio(portfolio, label, starting_cash):
    results = []
    total_value = 0
    total_pnl = 0
    cash = starting_cash

    for stock in portfolio:
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

# === Trade Logger ===
def log_sell(label, ticker, shares, price, cost, pnl, reason):
    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Sold": shares,
        "Sell Price": price,
        "Cost Basis": cost,
        "PnL": pnl,
        "Reason": reason
    }

    file = f"{label.lower()}_trade_log.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(file, index=False)

# === Manual Buy Logger ===
def log_manual_buy(buy_price, shares, ticker, cash):
    data = yf.download(ticker, period="1d")
    if data.empty:
        print(f"error, could not find ticker {ticker}")
    #not useful cuz its a single row but who cares 
    price = data['Close']
    price = float(price.iloc[0])
    if price * shares > cash:
        print(f"error, you have {cash} but are trying to spend {price * shares}. Are you sure you can do this?")
    cost_basis = buy_price
    pnl = 0.0

    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Bought": shares,
        "Buy Price": buy_price,
        "Cost Basis": cost_basis,
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
    return cash - shares * price

#def log_manual_sell(buy_price, sell_price, shares, ticker, cash, chatgpt_portfolio):
    chatgpt_portfolio = pd.DataFrame(chatgpt_portfolio)
    if ticker == np.any(chatgpt_portfolio['Ticker']):
        print(f"error, could not find ticker {ticker}")
    #not useful cuz its a single row but who cares
    price = data['Close'].iloc[-1]
    if price * shares > cash:
        print(f"error, you have {cash} but are trying to spend {price * shares}. Are you sure you  can do this?")
    cost_basis = buy_price
    pnl = 0.0

    log = {
        "Date": today,
        "Ticker": ticker,
        "Shares Bought": shares,
        "Buy Price": buy_price,
        "Cost Basis": cost_basis,
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
    return cash - shares * price


def print_prices(chatgpt_portfolio):
    today = datetime.today().strftime('%Y-%m-%d')
    print(f"prices and updates for {today}")
    for stock in chatgpt_portfolio + [{"ticker": "^RUT"}] + [{"ticker": "IWO"}]:
        stock = stock['ticker']
        data = yf.download(stock, period="2d")
        price = float(data['Close'].iloc[-1].item())
        last_price = float(data['Close'].iloc[-2].item())
        percent_change = ((price - last_price) / last_price) * 100
        volume = float(data['Volume'].iloc[-1].item())
        print(f"{stock} closing price: {price:.2f}")
        print(f"{stock} volume for today: ${volume}")
        print(f"percent change from the day before: {percent_change:.2f}%")

    chatgpt_df = pd.read_csv("chatgpt_portfolio_update.csv")

# Filter TOTAL rows and convert Date to datetime
    # Filter TOTAL rows and get latest equity
    chatgpt_totals = chatgpt_df[chatgpt_df['Ticker'] == 'TOTAL'].copy() 
    chatgpt_totals['Date'] = pd.to_datetime(chatgpt_totals['Date'])
    final_date = chatgpt_totals['Date'].max()
    final_value = chatgpt_totals[chatgpt_totals['Date'] == final_date]
    final_equity = final_value['Total Equity'].values[0]
    print(f"Latest ChatGPT Equity: ${final_equity:.2f}")

# Define start and end date for Russell 2000
    start_date = chatgpt_totals['Date'].min()
    end_date = final_date

# Get Russell 2000 data
    russell = yf.download("^RUT", start="2025-06-27", end=end_date + pd.Timedelta(days=1))
    russell = russell.reset_index()[["Date", "Close"]].rename(columns={"Close": "Russell_Close"})


# Normalize to $100
    initial_price = russell["Russell_Close"].iloc[0].item()
    price_now = russell["Russell_Close"].iloc[-1].item()
    scaling_factor = 100 / initial_price
    russell_value = price_now * scaling_factor
    print(f"$100 Invested in the Russell 2000 Index: ${russell_value:.2f}")

    

# === Run Portfolio ===
today = datetime.today().strftime('%Y-%m-%d')
#chatgpt_cash = get_latest_cash("chatgpt_portfolio_update.csv") or 20.45
chatgpt_cash = 2.32

#chatgpt_cash = log_manual_buy(1.5, 20, "IINN", chatgpt_cash)

#chatgpt_file, chatgpt_df = process_portfolio(chatgpt_portfolio, "ChatGPT", chatgpt_cash)

#print(chatgpt_df)

print_prices(chatgpt_portfolio)