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
    
    # Load exchange rates for currency conversion
    from utils.currency_converter import load_exchange_rates, convert_usd_to_cad, is_us_ticker
    from pathlib import Path
    from decimal import Decimal
    
    exchange_rates = load_exchange_rates(Path("trading_data/prod"))
    
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
            # Calculate TRUE performance metrics with proper currency conversion
            total_cost_basis_cad = Decimal('0')
            total_market_value_cad = Decimal('0')
            total_pnl_cad = Decimal('0')
            
            for pos in latest_positions:
                ticker = pos['Ticker']
                cost_basis = Decimal(str(pos['Cost Basis']))
                market_value = Decimal(str(pos['Total Value']))
                pnl = Decimal(str(pos['PnL']))
                
                # Convert USD to CAD if needed
                if is_us_ticker(ticker):
                    cost_basis_cad = convert_usd_to_cad(cost_basis, exchange_rates)
                    market_value_cad = convert_usd_to_cad(market_value, exchange_rates)
                    pnl_cad = convert_usd_to_cad(pnl, exchange_rates)
                else:
                    cost_basis_cad = cost_basis
                    market_value_cad = market_value
                    pnl_cad = pnl
                
                total_cost_basis_cad += cost_basis_cad
                total_market_value_cad += market_value_cad
                total_pnl_cad += pnl_cad
            
            # Convert back to float for compatibility
            total_cost_basis = float(total_cost_basis_cad)
            total_market_value = float(total_market_value_cad)
            total_pnl = float(total_pnl_cad)
            
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


def download_sp500(start_date: pd.Timestamp, end_date: pd.Timestamp, portfolio_dates: pd.Series) -> pd.DataFrame:
    """Download S&P 500 prices, normalize to $100 baseline, and forward-fill for weekends."""
    try:
        # Download with a few extra days buffer to ensure we get all needed data
        download_start = start_date - pd.Timedelta(days=5)
        download_end = end_date + pd.Timedelta(days=5)
        
        sp500 = yf.download("^GSPC", start=download_start, end=download_end,
                            progress=False, auto_adjust=False)
        sp500 = sp500.reset_index()
        if isinstance(sp500.columns, pd.MultiIndex):
            sp500.columns = sp500.columns.get_level_values(0)
        
        if sp500.empty:
            print("⚠️  No S&P 500 data available, creating flat baseline")
            return pd.DataFrame({
                'Date': portfolio_dates,
                'SPX Value ($100 Invested)': [100.0] * len(portfolio_dates)
            })
        
        # Find the S&P 500 price on the portfolio start date for fair comparison
        sp500_temp = sp500.copy()
        sp500_temp['Date_Only'] = pd.to_datetime(sp500_temp['Date']).dt.date
        
        portfolio_start_date = start_date.date()
        baseline_data = sp500_temp[sp500_temp['Date_Only'] == portfolio_start_date]
        
        if len(baseline_data) > 0:
            # Use S&P 500 price on portfolio start date
            baseline_close = baseline_data["Close"].iloc[0]
            print(f"🎯 Using S&P 500 close on {portfolio_start_date}: ${baseline_close:.2f} as baseline")
        else:
            # If no exact date match (weekend/holiday), use the closest previous trading day
            available_dates = sp500_temp[sp500_temp['Date_Only'] <= portfolio_start_date]
            if len(available_dates) > 0:
                baseline_close = available_dates["Close"].iloc[-1]
                baseline_date = available_dates['Date_Only'].iloc[-1]
                print(f"🎯 Using S&P 500 close on {baseline_date} (closest to {portfolio_start_date}): ${baseline_close:.2f} as baseline")
            else:
                # Fallback to first available price
                baseline_close = sp500["Close"].iloc[0]
                print(f"⚠️  Fallback: Using first available S&P 500 price: ${baseline_close:.2f} as baseline")
        
        scaling_factor = 100.0 / baseline_close
        sp500["SPX Value ($100 Invested)"] = sp500["Close"] * scaling_factor
        
        # Create a complete date range matching portfolio dates
        sp500_clean = sp500[["Date", "SPX Value ($100 Invested)"]].copy()
        sp500_clean['Date'] = pd.to_datetime(sp500_clean['Date']).dt.date
        
        # Create a DataFrame with all portfolio dates and merge with S&P 500 data
        portfolio_date_range = pd.DataFrame({
            'Date': [pd.to_datetime(d).date() for d in portfolio_dates]
        })
        
        # Merge and forward-fill missing values (weekends, holidays)
        merged = portfolio_date_range.merge(sp500_clean, on='Date', how='left')
        merged['SPX Value ($100 Invested)'] = merged['SPX Value ($100 Invested)'].ffill()
        
        # If we still have NaN values at the beginning, backfill
        merged['SPX Value ($100 Invested)'] = merged['SPX Value ($100 Invested)'].bfill()
        
        # Convert dates back to datetime for plotting
        merged['Date'] = pd.to_datetime(merged['Date'])
        
        print(f"📈 S&P 500 data: {len(sp500_clean)} trading days → {len(merged)} total days (with weekends)")
        return merged[["Date", "SPX Value ($100 Invested)"]]
        
    except Exception as e:
        print(f"⚠️  Error downloading S&P 500 data: {e}")
        print("📊 Creating flat S&P 500 baseline for comparison")
        return pd.DataFrame({
            'Date': portfolio_dates,
            'SPX Value ($100 Invested)': [100.0] * len(portfolio_dates)
        })


def find_peak_performance(df: pd.DataFrame) -> tuple[pd.Timestamp, float]:
    """
    Find the highest performance point (peak gain from baseline 100).
    Returns (peak_date, peak_gain_pct).
    """
    df = df.sort_values("Date")
    
    # Find the maximum performance index value
    max_idx = df["Performance_Index"].idxmax()
    peak_date = pd.Timestamp(df.loc[max_idx, "Date"])
    peak_value = float(df.loc[max_idx, "Performance_Index"])
    
    # Calculate gain percentage from baseline (100)
    peak_gain_pct = peak_value - 100.0
    
    return peak_date, peak_gain_pct


def compute_drawdown(df: pd.DataFrame) -> tuple[pd.Timestamp, float, float]:
    """
    Compute running max and drawdown (%). Return (dd_date, dd_value, dd_pct).
    """
    df = df.sort_values("Date").copy()
    df["Running Max"] = df["Performance_Index"].cummax()
    df["Drawdown %"] = (df["Performance_Index"] / df["Running Max"] - 1.0) * 100.0
    row = df.loc[df["Drawdown %"].idxmin()]
    return pd.Timestamp(row["Date"]), float(row["Total Equity"]), float(row["Drawdown %"])


def refresh_portfolio_data(data_dir_path):
    """Refresh portfolio data to ensure we have current prices before graphing."""
    try:
        print(f"🔄 Refreshing portfolio data to ensure current prices...")
        
        # Import the trading system components
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from config.settings import get_settings
        from data.repositories.repository_factory import get_repository_container, configure_repositories
        from portfolio.portfolio_manager import PortfolioManager
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        
        # Configure settings and repository
        settings = get_settings()
        if data_dir_path:
            settings._data_directory = str(data_dir_path)
        
        repo_config = settings.get_repository_config()
        configure_repositories({'default': repo_config})
        repository = get_repository_container().get_repository('default')
        
        # Initialize components
        portfolio_manager = PortfolioManager(repository)
        price_cache = PriceCache()
        market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
        
        # Get current portfolio and refresh prices
        latest_snapshot = portfolio_manager.get_latest_snapshot()
        if latest_snapshot and latest_snapshot.positions:
            print(f"💰 Refreshing prices for {len(latest_snapshot.positions)} positions...")
            
            # Update prices for all positions
            updated_positions = []
            for position in latest_snapshot.positions:
                try:
                    current_price = market_data_fetcher.get_current_price(position.ticker)
                    if current_price:
                        # Update position with current market data
                        position.current_price = current_price
                        position.market_value = current_price * position.shares
                        position.unrealized_pnl = position.market_value - position.cost_basis
                        updated_positions.append(position)
                        print(f"✅ {position.ticker}: ${current_price:.2f}")
                    else:
                        print(f"⚠️  {position.ticker}: Could not fetch current price")
                        updated_positions.append(position)  # Keep existing data
                except Exception as e:
                    print(f"⚠️  {position.ticker}: Error fetching price - {e}")
                    updated_positions.append(position)  # Keep existing data
            
            # Save updated snapshot
            if updated_positions:
                from datetime import datetime
                updated_snapshot = latest_snapshot
                updated_snapshot.positions = updated_positions
                updated_snapshot.timestamp = datetime.now()
                
                portfolio_manager.save_snapshot(updated_snapshot)
                print(f"✅ Portfolio data refreshed successfully")
        else:
            print(f"⚠️  No portfolio positions found to refresh")
            
    except Exception as e:
        print(f"⚠️  Failed to refresh portfolio data: {e}")
        print(f"📊 Continuing with existing data...")

def main() -> dict:
    """Generate and display the comparison graph; return metrics."""
    # First, try to refresh portfolio data to get current prices
    refresh_portfolio_data(DATA_DIR if 'DATA_DIR' in globals() else None)
    
    llm_totals = load_portfolio_totals()

    start_date = llm_totals["Date"].min()
    end_date = llm_totals["Date"].max()
    portfolio_dates = llm_totals["Date"]
    sp500 = download_sp500(start_date, end_date, portfolio_dates)

    # metrics
    peak_date, peak_gain = find_peak_performance(llm_totals)
    dd_date, dd_value, dd_pct = compute_drawdown(llm_totals)

    # plotting - optimized for financial time series (wide landscape)
    plt.figure(figsize=(16, 9))  # 16:9 aspect ratio, perfect for time series
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

    # annotate peak performance - position text within plot area
    peak_value = float(
        llm_totals.loc[llm_totals["Date"] == peak_date, "Performance_Index"].iloc[0]
    )
    plt.annotate(
        f"+{peak_gain:.2f}% peak",
        xy=(peak_date, peak_value),
        xytext=(10, 10),  # Offset from the point
        textcoords='offset points',
        color="green",
        fontsize=9,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.7),
        arrowprops=dict(arrowstyle="->", color="green", alpha=0.7)
    )

    # annotate final P/Ls - position within plot area
    final_date = llm_totals["Date"].iloc[-1]
    final_llm = float(llm_totals["Performance_Index"].iloc[-1])
    final_spx = float(sp500["SPX Value ($100 Invested)"].iloc[-1].item())
    
    portfolio_return = final_llm - 100.0
    sp500_return = final_spx - 100.0
    
    # Portfolio performance annotation
    plt.annotate(
        f"{portfolio_return:+.1f}%",
        xy=(final_date, final_llm),
        xytext=(-40, 10),  # Left offset to avoid edge
        textcoords='offset points',
        color="blue",
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7),
        arrowprops=dict(arrowstyle="->", color="blue", alpha=0.7)
    )
    
    # S&P 500 performance annotation  
    plt.annotate(
        f"{sp500_return:+.1f}%",
        xy=(final_date, final_spx),
        xytext=(-40, -15),  # Left and down offset
        textcoords='offset points',
        color="orange",
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.7),
        arrowprops=dict(arrowstyle="->", color="orange", alpha=0.7)
    )

    # annotate max drawdown - position within plot area
    dd_normalized = llm_totals.loc[llm_totals["Date"] == dd_date, "Performance_Index"].iloc[0] if len(llm_totals.loc[llm_totals["Date"] == dd_date]) > 0 else 100
    plt.annotate(
        f"{dd_pct:.1f}% max drawdown",
        xy=(dd_date, dd_normalized),
        xytext=(15, -20),  # Right and down offset
        textcoords='offset points',
        color="red",
        fontsize=9,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.7),
        arrowprops=dict(arrowstyle="->", color="red", alpha=0.7)
    )

    # Chart formatting - show TRUE performance, not misleading portfolio value growth
    total_invested = llm_totals['Cost_Basis'].iloc[-1]
    current_value = llm_totals['Market_Value'].iloc[-1] 
    actual_return = current_performance
    
    plt.title(f"Investment Performance Analysis\n${total_invested:,.0f} Invested → {actual_return:+.2f}% Return (vs S&P 500)")
    # Add weekend/holiday shading for market closure clarity
    def add_market_closure_shading(start_date, end_date):
        """Add light gray shading for weekends and holidays when markets are closed."""
        import matplotlib.dates as mdates
        from datetime import timedelta
        
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            # Check if it's a weekend (Saturday=5, Sunday=6)
            weekday = pd.to_datetime(current_date).weekday()
            
            if weekday >= 5:  # Weekend (Sat/Sun)
                shade_start = pd.to_datetime(current_date)
                shade_end = shade_start + pd.Timedelta(days=1)
                
                plt.axvspan(shade_start, shade_end, 
                           color='lightgray', alpha=0.15, zorder=0,
                           label='Weekend' if current_date == start_date.date() or weekday == 5 else "")
            
            # TODO: Add major market holidays (New Year's, July 4th, Christmas, etc.)
            # For now, just handle weekends which are the most common
            
            current_date += timedelta(days=1)
    
    add_market_closure_shading(llm_totals["Date"].min(), llm_totals["Date"].max())
    
    # Add break-even reference line
    plt.axhline(y=100, color='gray', linestyle=':', alpha=0.7, linewidth=1.5, label='Break-even')
    
    plt.xlabel("Date")
    plt.ylabel("Performance Index (100 = Break-even)")
    plt.xticks(rotation=45)  # Better rotation for dates
    plt.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)
    plt.grid(True, alpha=0.3)
    
    # Better layout management
    plt.subplots_adjust(left=0.08, bottom=0.12, right=0.95, top=0.88, hspace=0.2, wspace=0.2)

    # --- Auto-save to project root with optimized settings ---
    plt.savefig(RESULTS_PATH, 
                dpi=300, 
                bbox_inches="tight",
                facecolor='white',
                edgecolor='none',
                format='png',
                pad_inches=0.1)  # Minimal padding
    print(f"📊 Saved chart to: {RESULTS_PATH.resolve()}")

    plt.show()

    return {
        "peak_performance_date": peak_date,
        "peak_performance_pct": peak_gain,
        "max_drawdown_date": dd_date,
        "max_drawdown_equity": dd_value,
        "max_drawdown_pct": dd_pct,
    }


if __name__ == "__main__":
    print("generating graph...")

    metrics = main()
    peak_d = metrics["peak_performance_date"].date()
    peak_p = metrics["peak_performance_pct"]
    dd_d = metrics["max_drawdown_date"].date()
    dd_e = metrics["max_drawdown_equity"]
    dd_p = metrics["max_drawdown_pct"]
    print(f"Peak performance: +{peak_p:.2f}% on {peak_d}")
    print(f"Max drawdown: {dd_p:.2f}% on {dd_d} (equity ${dd_e:.2f})")
