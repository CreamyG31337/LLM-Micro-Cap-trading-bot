import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# === Load and prepare ChatGPT portfolio ===
chatgpt_df = pd.read_csv("ChatGPT-Micro-Cap-Experiment/chatgpt_portfolio_update.csv")
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

# Normalize ChatGPT portfolio to $100 baseline
chatgpt_totals["ChatGPT ($100 Invested)"] = chatgpt_totals["Total Equity"] * (100 / baseline_equity)

# === Download and prepare Russell 2000 ===
start_date = baseline_date
end_date = chatgpt_totals['Date'].max()

russell = yf.download("^RUT", start=start_date, end=end_date + pd.Timedelta(days=1))
russell = russell.reset_index()

# Fix columns if downloaded with MultiIndex
if isinstance(russell.columns, pd.MultiIndex):
    russell.columns = russell.columns.get_level_values(0)

# Now clean and rename
russell = russell[["Date", "Close"]].rename(columns={"Close": "Russell_Close"})
russell["Date"] = pd.to_datetime(russell["Date"])

pre_june_30_price = 2172.53  # Real price for normalization

# Normalize Russell to $100 baseline
scaling_factor = 100 / pre_june_30_price
russell["Russell Value ($100 Invested)"] = russell["Russell_Close"] * scaling_factor

# === Plot ===
plt.figure(figsize=(10, 6))
plt.style.use("seaborn-v0_8-whitegrid")
plt.plot(chatgpt_totals['Date'], chatgpt_totals["ChatGPT ($100 Invested)"], label="ChatGPT ($100 Invested)", marker="o", color="blue", linewidth=2)
plt.plot(russell['Date'], russell["Russell Value ($100 Invested)"], label="Russell 2000 ($100 Invested)", marker="o", color="red", linestyle='--', linewidth=2)
final_date = chatgpt_totals['Date'].iloc[-1]
final_chatgpt = chatgpt_totals["ChatGPT ($100 Invested)"].iloc[-1]
final_russell = russell["Russell Value ($100 Invested)"].iloc[-1]
plt.text(final_date, final_chatgpt + 0.3, f"+{final_chatgpt - 100:.1f}%", color="blue", fontsize=9)
plt.text(final_date, final_russell + 0.3, f"+{final_russell - 100:.1f}%", color="red", fontsize=9)

plt.title("ChatGPT vs. Russell 2000")
plt.xlabel("Date")
plt.ylabel("Value of $100 Investment")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()