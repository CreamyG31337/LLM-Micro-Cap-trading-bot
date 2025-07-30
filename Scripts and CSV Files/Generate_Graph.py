import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# === Load and prepare ChatGPT portfolio ===
chatgpt_df = pd.read_csv("Scripts and CSV files/chatgpt_portfolio_update.csv")
chatgpt_totals = chatgpt_df[chatgpt_df['Ticker'] == 'TOTAL'].copy()
chatgpt_totals['Date'] = pd.to_datetime(chatgpt_totals['Date'])

# Add fake baseline row for June 27 (weekend)
baseline_date = pd.Timestamp("2025-06-27")
baseline_equity = 100  # Starting value
baseline_chatgpt_row = pd.DataFrame({
    "Date": [baseline_date],
    "Total Equity": [baseline_equity]   
    })
chatgpt_totals = pd.concat([baseline_chatgpt_row, chatgpt_totals], ignore_index=True).sort_values("Date")

# === Download and prepare Russell 2000 ===
start_date = baseline_date
end_date = chatgpt_totals['Date'].max()

sp500 = yf.download("^SPX", start=start_date, end=end_date + pd.Timedelta(days=1), progress=False)
sp500 = sp500.reset_index()

# Fix columns if downloaded with MultiIndex
if isinstance(sp500.columns, pd.MultiIndex):
    sp500.columns = sp500.columns.get_level_values(0)
# Real close price on June 27 (pulled from YF)
sp500_27_price = 6173.07

# Normalize to $100 baseline
sp500_scaling_factor = 100 / sp500_27_price
# create adjusted close col



sp500["SPX Value ($100 Invested)"] = sp500["Close"] * sp500_scaling_factor

# === Plot ===
plt.figure(figsize=(10, 6))
plt.style.use("seaborn-v0_8-whitegrid")
plt.plot(chatgpt_totals['Date'], chatgpt_totals["Total Equity"], label="ChatGPT ($100 Invested)", marker="o", color="blue", linewidth=2)
plt.plot(sp500['Date'], sp500["SPX Value ($100 Invested)"], label="S&P 500 ($100 Invested)", marker="o", color="orange", linestyle='--', linewidth=2)

final_date = chatgpt_totals['Date'].iloc[-1]
final_chatgpt = float(chatgpt_totals["Total Equity"].iloc[-1])
final_spx = sp500["SPX Value ($100 Invested)"].iloc[-1]

plt.text(final_date, final_chatgpt + 0.3, f"+{final_chatgpt - 100:.1f}%", color="blue", fontsize=9)
plt.text(final_date, final_spx + 0.9, f"+{final_spx - 100:.1f}%", color="orange", fontsize=9)

drawdown_date = pd.Timestamp("2025-07-11")
drawdown_value = 102.46
plt.text(drawdown_date + pd.Timedelta(days=0.5), drawdown_value - 0.5, "-7% Drawdown", color="red", fontsize=9)
plt.title("ChatGPT's Micro Cap Portfolio vs. S&P 500")
plt.xlabel("Date")
plt.ylabel("Value of $100 Investment")
plt.xticks(rotation=15)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()