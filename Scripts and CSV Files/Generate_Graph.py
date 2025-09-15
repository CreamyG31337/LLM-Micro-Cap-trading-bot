import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from pathlib import Path
import sys
import argparse
sys.path.append(str(Path(__file__).parent.parent))
from display.console_output import _safe_emoji

# Command line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate portfolio performance graph")
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='Data directory path (overrides default search logic)'
    )
    return parser.parse_args()

# Parse arguments early
args = parse_arguments()

# Data directory resolution logic
SCRIPT_DIR = Path(__file__).resolve().parent

if args.data_dir:
    # Use specified data directory
    DATA_DIR = Path(args.data_dir)
    # Try multiple possible filenames
    portfolio_files = [
        DATA_DIR / "llm_portfolio_update.csv",
        DATA_DIR / "chatgpt_portfolio_update.csv",
        DATA_DIR / "portfolio_update.csv"
    ]
    PORTFOLIO_CSV = None
    for pf in portfolio_files:
        if pf.exists():
            PORTFOLIO_CSV = str(pf)
            break
    
    if PORTFOLIO_CSV is None:
        print(f"❌ No portfolio CSV file found in specified directory: {DATA_DIR}")
        print(f"   Looked for: {[pf.name for pf in portfolio_files]}")
        sys.exit(1)
else:
    # Legacy search logic - check multiple locations
    search_locations = [
        # 1. trading_data/prod (main production directory)
        SCRIPT_DIR.parent / "trading_data" / "prod",
        # 2. my trading (legacy location)
        SCRIPT_DIR.parent / "my trading", 
        # 3. Scripts and CSV Files (current directory)
        SCRIPT_DIR,
        # 4. Start Your Own directory
        SCRIPT_DIR.parent / "Start Your Own"
    ]
    
    PORTFOLIO_CSV = None
    DATA_DIR = None
    
    for search_dir in search_locations:
        if not search_dir.exists():
            continue
            
        # Try different file names in each location
        possible_files = [
            search_dir / "llm_portfolio_update.csv",
            search_dir / "chatgpt_portfolio_update.csv",
            search_dir / "portfolio_update.csv"
        ]
        
        for pf in possible_files:
            if pf.exists():
                PORTFOLIO_CSV = str(pf)
                DATA_DIR = search_dir
                print(f"📁 Found portfolio data at: {PORTFOLIO_CSV}")
                break
        
        if PORTFOLIO_CSV:
            break
    
    if PORTFOLIO_CSV is None:
        print("❌ No portfolio CSV file found in any of the expected locations:")
        for i, loc in enumerate(search_locations, 1):
            print(f"   {i}. {loc}")
        print("\n💡 Try specifying the data directory with --data-dir argument")
        print("   Example: python Generate_Graph.py --data-dir 'trading_data/prod'")
        sys.exit(1)

# Save path in project root
RESULTS_PATH = Path("Results.png")  # NEW


def load_portfolio_totals() -> pd.DataFrame:
    """Load portfolio equity history and calculate daily totals from individual positions."""
    llm_df = pd.read_csv(PORTFOLIO_CSV)
    
    print(f"📊 Loaded portfolio data with {len(llm_df)} rows")
    print(f"📊 Columns: {list(llm_df.columns)}")
    
    # Convert date and clean data for modern format
    llm_df["Date"] = pd.to_datetime(llm_df["Date"], errors="coerce")
    llm_df["Total Value"] = pd.to_numeric(llm_df["Total Value"], errors="coerce")
    
    # Convert dates to date-only (remove time component) for proper daily aggregation
    llm_df['Date_Only'] = llm_df['Date'].dt.date
    
    print(f"📅 Date range: {llm_df['Date_Only'].min()} to {llm_df['Date_Only'].max()}")
    
    # Group by date and calculate portfolio totals
    # For each date, we want the FINAL state (latest timestamp) for each ticker
    daily_totals = []
    for date_only, date_group in llm_df.groupby('Date_Only'):
        if pd.isna(date_only):
            continue
        
        # For each ticker on this date, get the LATEST entry (last timestamp)
        latest_positions = []
        for ticker, ticker_group in date_group.groupby('Ticker'):
            # Get the row with the latest timestamp for this ticker on this date
            latest_entry = ticker_group.loc[ticker_group['Date'].idxmax()]
            
            # Only include positions that still have value (not sold)
            if latest_entry['Total Value'] > 0:
                latest_positions.append(latest_entry)
        
        if latest_positions:
            # Calculate TRUE performance metrics
            total_cost_basis = sum(pos['Cost Basis'] for pos in latest_positions)
            total_market_value = sum(pos['Total Value'] for pos in latest_positions)
            total_pnl = sum(pos['PnL'] for pos in latest_positions)
            
            # Performance percentage (how much your investments have grown/declined)
            performance_pct = (total_pnl / total_cost_basis) * 100 if total_cost_basis > 0 else 0.0
            
            # Use the latest timestamp from this date as the representative date
            latest_timestamp = pd.to_datetime(date_only)
            
            daily_totals.append({
                "Date": latest_timestamp, 
                "Total Equity": total_market_value,  # Keep for compatibility
                "Cost_Basis": total_cost_basis,      # Money actually invested
                "Market_Value": total_market_value,   # Current value of investments
                "Unrealized_PnL": total_pnl,         # Actual gains/losses
                "Performance_Pct": performance_pct     # True percentage return
            })
            
            print(f"📊 {date_only}: Invested ${total_cost_basis:,.2f} → Worth ${total_market_value:,.2f} ({performance_pct:+.2f}%)")
    
    if len(daily_totals) == 0:
        print("⚠️  No valid portfolio data found. Creating baseline entry.")
        llm_totals = pd.DataFrame({
            "Date": [pd.Timestamp.now()], 
            "Total Equity": [100.0]
        })
    else:
        llm_totals = pd.DataFrame(daily_totals)
        print(f"📈 Calculated {len(llm_totals)} daily portfolio totals")

    # Convert to DataFrame and sort by date
    if daily_totals:
        llm_totals = pd.DataFrame(daily_totals)
        llm_totals = llm_totals.sort_values("Date").reset_index(drop=True)
        
        # Use actual investment performance for meaningful comparison
        # This shows how your investments are performing, not cash injections
        llm_totals["Performance_Index"] = llm_totals["Performance_Pct"] + 100  # Base 100 index
        
        start_invested = llm_totals["Cost_Basis"].iloc[0]
        end_invested = llm_totals["Cost_Basis"].iloc[-1]
        start_performance = llm_totals["Performance_Pct"].iloc[0]
        end_performance = llm_totals["Performance_Pct"].iloc[-1]
        
        print(f"📈 Investment Performance: {start_performance:+.2f}% → {end_performance:+.2f}%")
        print(f"💰 Total Capital Deployed: ${start_invested:,.2f} → ${end_invested:,.2f}")
        return llm_totals
    else:
        # Fallback if no data
        return pd.DataFrame({"Date": [pd.Timestamp.now()], "Performance_Pct": [0.0], "Performance_Index": [100.0]})
    
    print(f"📊 Final dataset: {len(out)} data points from {out['Date'].min().date()} to {out['Date'].max().date()}")
    return out


def download_sp500(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Download S&P 500 prices and normalise to a $100 baseline."""
    try:
        sp500 = yf.download("^GSPC", start=start_date, end=end_date + pd.Timedelta(days=1),
                            progress=False, auto_adjust=False)
        sp500 = sp500.reset_index()
        if isinstance(sp500.columns, pd.MultiIndex):
            sp500.columns = sp500.columns.get_level_values(0)
        
        if sp500.empty:
            print("⚠️  No S&P 500 data available, creating flat baseline")
            return pd.DataFrame({
                'Date': [start_date, end_date],
                'SPX Value ($100 Invested)': [100.0, 100.0]
            })
        
        # Use the first available price as baseline for $100 investment
        first_close = sp500["Close"].iloc[0]
        scaling_factor = 100.0 / first_close
        sp500["SPX Value ($100 Invested)"] = sp500["Close"] * scaling_factor
        
        print(f"📈 Downloaded S&P 500 data: {len(sp500)} data points")
        return sp500[["Date", "SPX Value ($100 Invested)"]]
        
    except Exception as e:
        print(f"⚠️  Error downloading S&P 500 data: {e}")
        print("📊 Creating flat S&P 500 baseline for comparison")
        return pd.DataFrame({
            'Date': [start_date, end_date],
            'SPX Value ($100 Invested)': [100.0, 100.0]
        })


def find_largest_gain(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, float]:
    """
    Largest rise from a local minimum to the subsequent peak.
    Returns (start_date, end_date, gain_pct).
    """
    df = df.sort_values("Date")
    min_val = float(df["Performance_Index"].iloc[0])
    min_date = pd.Timestamp(df["Date"].iloc[0])
    peak_val = min_val
    peak_date = min_date
    best_gain = 0.0
    best_start = min_date
    best_end = peak_date

    # iterate rows 1..end
    for date, val in df[["Date", "Performance_Index"]].iloc[1:].itertuples(index=False):
        val = float(val)
        date = pd.Timestamp(date)

        # extend peak while rising
        if val > peak_val:
            peak_val = val
            peak_date = date
            continue

        # fall → close previous run
        if val < peak_val:
            gain = (peak_val - min_val) / 100.0 * 100.0  # Convert to percentage from base 100
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
    gain = (peak_val - min_val) / 100.0 * 100.0  # Convert to percentage from base 100
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
    df["Running Max"] = df["Performance_Index"].cummax()
    df["Drawdown %"] = (df["Performance_Index"] / df["Running Max"] - 1.0) * 100.0
    row = df.loc[df["Drawdown %"].idxmin()]
    return pd.Timestamp(row["Date"]), float(row["Total Equity"]), float(row["Drawdown %"])


def main() -> dict:
    """Generate and display the comparison graph; return metrics."""
    llm_totals = load_portfolio_totals()

    start_date = llm_totals["Date"].min()
    end_date = llm_totals["Date"].max()
    sp500 = download_sp500(start_date, end_date)

    # metrics
    largest_start, largest_end, largest_gain = find_largest_gain(llm_totals)
    dd_date, dd_value, dd_pct = compute_drawdown(llm_totals)

    # plotting
    plt.figure(figsize=(10, 6))
    plt.style.use("seaborn-v0_8-whitegrid")

    # Show ACTUAL investment performance vs S&P 500 performance
    current_performance = llm_totals["Performance_Pct"].iloc[-1]
    plt.plot(
        llm_totals["Date"],
        llm_totals["Performance_Index"],
        label=f"Your Investments ({current_performance:+.2f}%)",
        marker="o",
        color="blue",
        linewidth=2.5,
    )
    plt.plot(
        sp500["Date"],
        sp500["SPX Value ($100 Invested)"],
        label="S&P 500 Benchmark",
        marker="s",
        color="orange",
        linestyle="--",
        linewidth=2,
        alpha=0.8,
    )

    # annotate largest gain
    largest_peak_value = float(
        llm_totals.loc[llm_totals["Date"] == largest_end, "Performance_Index"].iloc[0]
    )
    plt.text(
        largest_end,
        largest_peak_value + 5,
        f"+{largest_gain:.1f}% largest gain",
        color="green",
        fontsize=9,
    )

    # annotate final P/Ls
    final_date = llm_totals["Date"].iloc[-1]
    final_llm = float(llm_totals["Performance_Index"].iloc[-1])
    final_spx = float(sp500["SPX Value ($100 Invested)"].iloc[-1].item())
    
    portfolio_return = final_llm - 100.0
    sp500_return = final_spx - 100.0
    
    plt.text(final_date, final_llm + 5, f"{portfolio_return:+.1f}%", color="blue", fontsize=10, weight="bold")
    plt.text(final_date, final_spx + 5, f"{sp500_return:+.1f}%", color="orange", fontsize=10, weight="bold")

    # annotate max drawdown (use normalized values)
    dd_normalized = llm_totals.loc[llm_totals["Date"] == dd_date, "Performance_Index"].iloc[0] if len(llm_totals.loc[llm_totals["Date"] == dd_date]) > 0 else 100
    plt.text(
        dd_date + pd.Timedelta(days=0.2),
        dd_normalized - 5,
        f"{dd_pct:.1f}% max drawdown",
        color="red",
        fontsize=9,
    )

    # Chart formatting - show TRUE performance, not misleading portfolio value growth
    total_invested = llm_totals['Cost_Basis'].iloc[-1]
    current_value = llm_totals['Market_Value'].iloc[-1] 
    actual_return = current_performance
    
    plt.title(f"Investment Performance Analysis\n${total_invested:,.0f} Invested → {actual_return:+.2f}% Return (vs S&P 500)")
    plt.xlabel("Date")
    plt.ylabel("Performance Index (100 = Break-even)")
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