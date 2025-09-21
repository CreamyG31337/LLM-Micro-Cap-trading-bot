import pandas as pd
import sys

try:
    df = pd.read_csv('trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv')
    print(f'Total rows: {len(df)}')
    print(f'Unique tickers: {df["Ticker"].nunique()}')
    print(f'Latest date: {df["Date"].max()}')
    print(f'Unique actions: {sorted(df["Action"].unique())}')
    print(f'Positions with BUY actions: {len(df[df["Action"] == "BUY"])}')
    print(f'Positions with HOLD actions: {len(df[df["Action"] == "HOLD"])}')
    print(f'Positions with SELL actions: {len(df[df["Action"] == "SELL"])}')

    # Get the most recent entries for each ticker
    latest_entries = df.sort_values('Date').groupby('Ticker').tail(1)
    print(f'Unique positions (latest entries): {len(latest_entries)}')
    print(f'Latest entries actions: {sorted(latest_entries["Action"].unique())}')

    # Show PnL summary
    hold_entries = latest_entries[latest_entries['Action'] == 'HOLD']
    if not hold_entries.empty:
        print(f'Total positions with HOLD: {len(hold_entries)}')
        print(f'Sample PnL values: {hold_entries["PnL"].head().tolist()}')
        print(f'Total PnL sum: {hold_entries["PnL"].sum()}')
        print(f'Average PnL: {hold_entries["PnL"].mean()}')
    else:
        print('No HOLD entries found in latest data')

except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
