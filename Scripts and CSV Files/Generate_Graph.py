import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from display.console_output import _safe_emoji

# Default to parent directory's 'my trading' folder, fallback to local directory
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "my trading"
DATA_DIR = str(DEFAULT_DATA_DIR) if DEFAULT_DATA_DIR.exists() else "Scripts and CSV Files"
PORTFOLIO_CSV = f"{DATA_DIR}/llm_portfolio_update.csv" if "my trading" in DATA_DIR else f"{DATA_DIR}/chatgpt_portfolio_update.csv"

# Save path in project root
RESULTS_PATH = Path("Results.png")  # NEW


def load_portfolio_totals() -> pd.DataFrame:
    """Load portfolio equity history including a baseline row."""
    llm_df = pd.read_csv(PORTFOLIO_CSV)
    
    # Try to find TOTAL rows first
    total_rows = llm_df[llm_df["Ticker"] == "TOTAL"].copy()
    
    if len(total_rows) > 0:
        # Use existing TOTAL rows
        llm_totals = total_rows
        llm_totals["Date"] = pd.to_datetime(llm_totals["Date"])
        llm_totals["Total Equity"] = pd.to_numeric(
            llm_totals["Total Equity"], errors="coerce"
        )
    else:
        # Calculate totals from individual positions when no TOTAL rows exist
        print("No TOTAL rows found. Calculating portfolio totals from individual positions...")
        
        # Convert date and clean data
        llm_df["Date"] = pd.to_datetime(llm_df["Date"])
        llm_df["Total Value"] = pd.to_numeric(llm_df["Total Value"], errors="coerce")
        llm_df["Cash Balance"] = pd.to_numeric(llm_df["Cash Balance"], errors="coerce")
        
        # Group by date and calculate totals
        daily_totals = []
        for date, group in llm_df.groupby("Date"):
            # Sum up all position values (excluding rows with NaN values)
            position_value = group["Total Value"].dropna().sum()
            
            # Get cash balance (use the last non-null value for the date)
            cash_balance = group["Cash Balance"].dropna()
            cash_balance = cash_balance.iloc[-1] if len(cash_balance) > 0 else 0.0
            
            total_equity = position_value + cash_balance
            daily_totals.append({"Date": date, "Total Equity": total_equity})
        
        llm_totals = pd.DataFrame(daily_totals)
        
        if len(llm_totals) == 0:
            # Fallback: create a single data point with current date and $100
            print("Warning: No valid portfolio data found. Creating baseline entry.")
            llm_totals = pd.DataFrame({
                "Date": [pd.Timestamp.now()], 
                "Total Equity": [100.0]
            })

    baseline_date = pd.Timestamp("2025-06-27")
    baseline_equity = 100.0
    baseline_row = pd.DataFrame({"Date": [baseline_date], "Total Equity": [baseline_equity]})

    out = pd.concat([baseline_row, llm_totals], ignore_index=True).sort_values("Date")
    out = out.drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
    return out


def download_sp500(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Download S&P 500 prices and normalise to a $100 baseline (at 2025-06-27 close=6173.07)."""
    sp500 = yf.download("^SPX", start=start_date, end=end_date + pd.Timedelta(days=1),
                        progress=False, auto_adjust=True)
    sp500 = sp500.reset_index()
    if isinstance(sp500.columns, pd.MultiIndex):
        sp500.columns = sp500.columns.get_level_values(0)

    spx_27_price = 6173.07  # 2025-06-27 close (baseline)
    scaling_factor = 100.0 / spx_27_price
    sp500["SPX Value ($100 Invested)"] = sp500["Close"] * scaling_factor
    return sp500[["Date", "SPX Value ($100 Invested)"]]


def find_largest_gain(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, float]:
    """
    Largest rise from a local minimum to the subsequent peak.
    Returns (start_date, end_date, gain_pct).
    """
    df = df.sort_values("Date")
    min_val = float(df["Total Equity"].iloc[0])
    min_date = pd.Timestamp(df["Date"].iloc[0])
    peak_val = min_val
    peak_date = min_date
    best_gain = 0.0
    best_start = min_date
    best_end = peak_date

    # iterate rows 1..end
    for date, val in df[["Date", "Total Equity"]].iloc[1:].itertuples(index=False):
        val = float(val)
        date = pd.Timestamp(date)

        # extend peak while rising
        if val > peak_val:
            peak_val = val
            peak_date = date
            continue

        # fall → close previous run
        if val < peak_val:
            gain = (peak_val - min_val) / min_val * 100.0
            if gain > best_gain:
                best_gain = gain
                best_start = min_date
                best_end = peak_date
            # reset min/peak at this valley
            min_val = val
            min_date = date
            peak_val = val
            peak_date = date

    # final run (if last segment ends on a rise)
    gain = (peak_val - min_val) / min_val * 100.0
    if gain > best_gain:
        best_gain = gain
        best_start = min_date
        best_end = peak_date

    return best_start, best_end, best_gain


def compute_drawdown(df: pd.DataFrame) -> tuple[pd.Timestamp, float, float]:
    """
    Compute running max and drawdown (%). Return (dd_date, dd_value, dd_pct).
    """
    df = df.sort_values("Date").copy()
    df["Running Max"] = df["Total Equity"].cummax()
    df["Drawdown %"] = (df["Total Equity"] / df["Running Max"] - 1.0) * 100.0
    row = df.loc[df["Drawdown %"].idxmin()]
    return pd.Timestamp(row["Date"]), float(row["Total Equity"]), float(row["Drawdown %"])


def main() -> dict:
    """Generate and display the comparison graph; return metrics."""
    llm_totals = load_portfolio_totals()

    start_date = pd.Timestamp("2025-06-27")
    end_date = llm_totals["Date"].max()
    sp500 = download_sp500(start_date, end_date)

    # metrics
    largest_start, largest_end, largest_gain = find_largest_gain(llm_totals)
    dd_date, dd_value, dd_pct = compute_drawdown(llm_totals)

    # plotting
    plt.figure(figsize=(10, 6))
    plt.style.use("seaborn-v0_8-whitegrid")

    plt.plot(
        llm_totals["Date"],
        llm_totals["Total Equity"],
        label="LLM ($100 Invested)",
        marker="o",
        color="blue",
        linewidth=2,
    )
    plt.plot(
        sp500["Date"],
        sp500["SPX Value ($100 Invested)"],
        label="S&P 500 ($100 Invested)",
        marker="o",
        color="orange",
        linestyle="--",
        linewidth=2,
    )

    # annotate largest gain
    largest_peak_value = float(
        llm_totals.loc[llm_totals["Date"] == largest_end, "Total Equity"].iloc[0]
    )
    plt.text(
        largest_end,
        largest_peak_value + 0.3,
        f"+{largest_gain:.1f}% largest gain",
        color="green",
        fontsize=9,
    )

    # annotate final P/Ls
    final_date = llm_totals["Date"].iloc[-1]
    final_llm = float(llm_totals["Total Equity"].iloc[-1].item())
    final_spx = float(sp500["SPX Value ($100 Invested)"].iloc[-1].item())
    plt.text(final_date, final_llm + 0.3, f"+{final_llm - 100.0:.1f}%", color="blue", fontsize=9)
    plt.text(final_date, final_spx + 0.9, f"+{final_spx - 100.0:.1f}%", color="orange", fontsize=9)

    # annotate max drawdown
    plt.text(
        dd_date + pd.Timedelta(days=0.5),
        dd_value - 0.5,
        f"{dd_pct:.1f}%",
        color="red",
        fontsize=9,
    )

    plt.title("LLM Micro Cap Portfolio vs. S&P 500")
    plt.xlabel("Date")
    plt.ylabel("Value of $100 Investment")
    plt.xticks(rotation=15)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # --- Auto-save to project root ---
    plt.savefig(RESULTS_PATH, dpi=300, bbox_inches="tight")
    print(f"Saved chart to: {RESULTS_PATH.resolve()}")

    plt.show()

    return {
        "largest_run_start": largest_start,
        "largest_run_end": largest_end,
        "largest_run_gain_pct": largest_gain,
        "max_drawdown_date": dd_date,
        "max_drawdown_equity": dd_value,
        "max_drawdown_pct": dd_pct,
    }


if __name__ == "__main__":
    print("generating graph...")

    metrics = main()
    ls = metrics["largest_run_start"].date()
    le = metrics["largest_run_end"].date()
    lg = metrics["largest_run_gain_pct"]
    dd_d = metrics["max_drawdown_date"].date()
    dd_e = metrics["max_drawdown_equity"]
    dd_p = metrics["max_drawdown_pct"]
    print(f"Largest run: {ls} → {le}, +{lg:.2f}%")
    print(f"Max drawdown: {dd_p:.2f}% on {dd_d} (equity {dd_e:.2f})")