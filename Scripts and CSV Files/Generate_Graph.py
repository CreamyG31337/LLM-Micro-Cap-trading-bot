import matplotlib
# Use Agg backend to prevent GUI windows and threading issues
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from pathlib import Path
import sys
import argparse
from decimal import Decimal
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
    parser.add_argument(
        '--show-graph',
        action='store_true',
        default=True,
        help='Automatically open the generated graph (default: True, useful for development)'
    )
    parser.add_argument(
        '--no-show-graph',
        action='store_true',
        default=False,
        help='Disable automatic graph opening (useful for server/headless environments)'
    )
    parser.add_argument(
        '--benchmark',
        type=str,
        default='qqq',
        choices=['sp500', 'qqq', 'russell2000', 'vti', 'all'],
        help='Benchmark to compare against (default: qqq - Nasdaq-100, all: show all benchmarks)'
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
    # Search logic - check multiple locations including fund directories
    search_locations = [
        # 1. Active fund directory (if fund management is available)
        None,  # Will be populated dynamically
        # 2. trading_data/funds/* (all fund directories)
        None,  # Will be populated dynamically
        # 3. Scripts and CSV Files (current directory)
        SCRIPT_DIR,
        # 5. Legacy locations (for backward compatibility)
        SCRIPT_DIR.parent / "my trading",
        SCRIPT_DIR.parent / "trading_data" / "prod"
    ]
    
    # Try to get active fund directory first
    try:
        from utils.fund_manager import get_fund_manager
        fm = get_fund_manager()
        active_fund = fm.get_active_fund()
        if active_fund:
            active_fund_dir = fm.get_fund_data_directory()
            if active_fund_dir:
                search_locations[0] = Path(active_fund_dir)
                print(f"{_safe_emoji('📁')} Using active fund directory: {active_fund_dir}")
    except ImportError:
        pass  # Fund management not available
    
    # Add all fund directories
    try:
        funds_dir = SCRIPT_DIR.parent / "trading_data" / "funds"
        if funds_dir.exists():
            for fund_dir in funds_dir.iterdir():
                if fund_dir.is_dir():
                    search_locations[1] = fund_dir
                    break  # Use first fund found
    except Exception:
        pass
    
    PORTFOLIO_CSV = None
    DATA_DIR = None
    
    for search_dir in search_locations:
        if search_dir is None or not search_dir.exists():
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
                print(f"{_safe_emoji('📁')} Found portfolio data at: {PORTFOLIO_CSV}")
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

# Save path in graphs folder with timestamp
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_PATH = Path(f"graphs/portfolio_performance_{timestamp}.png")


def should_open_graph(args) -> bool:
    """Determine if we should automatically open the graph based on arguments and environment."""
    # Explicit command line arguments take precedence
    if args.no_show_graph:
        return False
    if args.show_graph:
        return True
    
    # Environment detection as fallback
    import os
    
    # Check for headless/server environment indicators
    headless_indicators = [
        'DISPLAY' not in os.environ,  # No X11 display (Linux)
        os.environ.get('SSH_CONNECTION') is not None,  # SSH connection
        os.environ.get('VERCEL') is not None,  # Vercel deployment
        os.environ.get('HEROKU') is not None,  # Heroku deployment
        os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None,  # AWS Lambda
        os.environ.get('GITHUB_ACTIONS') is not None,  # GitHub Actions
        os.environ.get('CI') is not None,  # General CI environment
    ]
    
    # If any headless indicator is present, don't open graph
    if any(headless_indicators):
        return False
    
    # Default to opening graph for local development
    return True


def open_graph_file(file_path: Path) -> None:
    """Open the graph file using the system's default image viewer."""
    import os
    import platform
    import subprocess
    
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(file_path))
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(file_path)], check=True)
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", str(file_path)], check=True)
        
        print(f"{_safe_emoji('📖')} Opened graph in default viewer")
        
    except Exception as e:
        print(f"⚠️  Could not open graph automatically: {e}")
        print(f"{_safe_emoji('📁')} Graph saved at: {file_path.resolve()}")


def load_portfolio_totals() -> pd.DataFrame:
    """Load portfolio equity history and calculate daily totals from individual positions."""
    llm_df = pd.read_csv(PORTFOLIO_CSV)
    
    print(f"{_safe_emoji('📊')} Loaded portfolio data with {len(llm_df)} rows")
    print(f"{_safe_emoji('📊')} Columns: {list(llm_df.columns)}")
    
    # Convert date and clean data for modern format
    llm_df["Date"] = pd.to_datetime(llm_df["Date"], errors="coerce")
    llm_df["Total Value"] = pd.to_numeric(llm_df["Total Value"], errors="coerce")
    
    # Convert dates to date-only (remove time component) for proper daily aggregation
    # Filter out NaN dates first to avoid mixed type issues
    llm_df = llm_df.dropna(subset=['Date'])
    llm_df['Date_Only'] = llm_df['Date'].dt.date
    
    print(f"{_safe_emoji('📅')} Date range: {llm_df['Date_Only'].min()} to {llm_df['Date_Only'].max()}")
    
    # Load exchange rates for currency conversion
    from utils.currency_converter import load_exchange_rates, convert_usd_to_cad, is_us_ticker
    from pathlib import Path
    from decimal import Decimal
    
    # Use the data directory from the portfolio file for exchange rates
    exchange_rates = load_exchange_rates(Path(DATA_DIR) if 'DATA_DIR' in globals() else Path("trading_data/funds/Project Chimera"))
    
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
            
            print(f"{_safe_emoji('📊')} {date_only}: Invested ${total_cost_basis:,.2f} -> Worth ${total_market_value:,.2f} ({performance_pct:+.2f}%)")
    
    if len(daily_totals) == 0:
        print(f"{_safe_emoji('⚠️')}  No valid portfolio data found. Creating baseline entry.")
        llm_totals = pd.DataFrame({
            "Date": [pd.Timestamp.now()], 
            "Total Equity": [100.0]
        })
    else:
        llm_totals = pd.DataFrame(daily_totals)
        print(f"{_safe_emoji('📈')} Calculated {len(llm_totals)} daily portfolio totals")

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
        
        print(f"{_safe_emoji('📈')} Investment Performance: {start_performance:+.2f}% -> {end_performance:+.2f}%")
        print(f"{_safe_emoji('💰')} Total Capital Deployed: ${start_invested:,.2f} -> ${end_invested:,.2f}")
        
        # Create continuous timeline including weekends
        llm_totals = create_continuous_timeline(llm_totals)
        return llm_totals
    else:
        # Fallback if no data
        return pd.DataFrame({"Date": [pd.Timestamp.now()], "Performance_Pct": [0.0], "Performance_Index": [100.0]})
    
    print(f"{_safe_emoji('📊')} Final dataset: {len(out)} data points from {out['Date'].min().date()} to {out['Date'].max().date()}")
    return out


def create_continuous_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Create a continuous timeline with proper market timing representation.
    
    - Grid lines represent midnight (00:00)
    - Trading data points represent market close time (~13:00 PST)
    - Weekend/holiday values are forward-filled from last trading day
    """
    if df.empty:
        return df
    
    # Get the date range - ensure we have proper datetime objects
    start_date = pd.to_datetime(df['Date'].min()).date()
    end_date = pd.to_datetime(df['Date'].max()).date()
    
    # Create complete date range (every single day at midnight for grid reference)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create DataFrame with complete date range
    continuous_df = pd.DataFrame({'Date': date_range})
    continuous_df['Date_Only'] = continuous_df['Date'].dt.date
    
    # Convert original df date for merging
    df_for_merge = df.copy()
    df_for_merge['Date_Only'] = df_for_merge['Date'].dt.date
    
    # Merge and forward-fill missing values (weekends/holidays keep previous trading day values)
    merged = continuous_df.merge(df_for_merge.drop('Date', axis=1), on='Date_Only', how='left')
    
    # Forward fill all numeric columns (portfolio values don't change on weekends)
    numeric_cols = ['Cost_Basis', 'Market_Value', 'Unrealized_PnL', 'Performance_Pct', 'Performance_Index', 'Total Equity']
    for col in numeric_cols:
        if col in merged.columns:
            merged[col] = merged[col].ffill()
    
    
    # Adjust timestamps to represent market close time for trading days
    # For weekends, use market close time of the weekend day to keep lines flat
    from datetime import timedelta
    
    for idx, row in merged.iterrows():
        date_only = row['Date'].date()
        weekday = pd.to_datetime(date_only).weekday()
        
        if weekday < 5:  # Trading day (Mon-Fri = 0-4)
            # Set to market close time: 1:00 PM PST (13:00)
            market_close_time = pd.to_datetime(date_only) + timedelta(hours=13)
            merged.at[idx, 'Date'] = market_close_time
        else:  # Weekend (Sat-Sun = 5-6)
            # Also use market close time for weekend days to keep lines flat
            # This prevents diagonal lines from weekend midnight to Monday market close
            weekend_market_close = pd.to_datetime(date_only) + timedelta(hours=13)
            merged.at[idx, 'Date'] = weekend_market_close
    
    # Drop the helper column
    merged = merged.drop('Date_Only', axis=1)
    
    print(f"{_safe_emoji('📅')} Created continuous timeline: {len(df)} trading days -> {len(merged)} total days (with market timing)")
    return merged


def get_benchmark_config(benchmark_name: str) -> dict:
    """Get benchmark configuration including ticker, display name, and column name."""
    configs = {
        'sp500': {
            'ticker': '^GSPC',
            'display_name': 'S&P 500',
            'column_name': 'SPX Value ($100 Invested)',
            'short_name': 'SPX'
        },
        'russell2000': {
            'ticker': '^RUT',
            'display_name': 'Russell 2000',
            'column_name': 'RUT Value ($100 Invested)',
            'short_name': 'RUT'
        },
        'qqq': {
            'ticker': 'QQQ',
            'display_name': 'Nasdaq-100 (QQQ)',
            'column_name': 'QQQ Value ($100 Invested)',
            'short_name': 'QQQ'
        },
        'vti': {
            'ticker': 'VTI',
            'display_name': 'Total Stock Market (VTI)',
            'column_name': 'VTI Value ($100 Invested)',
            'short_name': 'VTI'
        }
    }
    return configs.get(benchmark_name, configs['sp500'])


def download_benchmark(benchmark_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp, portfolio_dates: pd.Series) -> pd.DataFrame:
    """Download benchmark prices, normalize to $100 baseline, and forward-fill for weekends."""
    config = get_benchmark_config(benchmark_name)
    ticker = config['ticker']
    display_name = config['display_name']
    column_name = config['column_name']
    
    try:
        # Download with a few extra days buffer to ensure we get all needed data
        download_start = start_date - pd.Timedelta(days=5)
        download_end = end_date + pd.Timedelta(days=5)
        
        benchmark_data = yf.download(ticker, start=download_start, end=download_end,
                                   progress=False, auto_adjust=False)
        benchmark_data = benchmark_data.reset_index()
        if isinstance(benchmark_data.columns, pd.MultiIndex):
            benchmark_data.columns = benchmark_data.columns.get_level_values(0)
        
        if benchmark_data.empty:
            print(f"{_safe_emoji('⚠️')}  No {display_name} data available, creating flat baseline")
            return pd.DataFrame({
                'Date': portfolio_dates,
                column_name: [100.0] * len(portfolio_dates)
            })
        
        # Find the benchmark price on the portfolio start date for fair comparison
        benchmark_temp = benchmark_data.copy()
        benchmark_temp['Date_Only'] = pd.to_datetime(benchmark_temp['Date']).dt.date
        
        portfolio_start_date = pd.to_datetime(start_date).date()
        # Ensure both sides of comparison are datetime.date objects
        benchmark_temp['Date_Only'] = pd.to_datetime(benchmark_temp['Date_Only']).dt.date
        baseline_data = benchmark_temp[benchmark_temp['Date_Only'] == portfolio_start_date]
        
        if len(baseline_data) > 0:
            # Use benchmark price on portfolio start date
            baseline_close = baseline_data["Close"].iloc[0]
            print(f"{_safe_emoji('🎯')} Using {display_name} close on {portfolio_start_date}: ${baseline_close:.2f} as baseline")
        else:
            # If no exact date match (weekend/holiday), use the closest previous trading day
            available_dates = benchmark_temp[benchmark_temp['Date_Only'] <= portfolio_start_date]
            if len(available_dates) > 0:
                baseline_close = available_dates["Close"].iloc[-1]
                baseline_date = available_dates['Date_Only'].iloc[-1]
                print(f"{_safe_emoji('🎯')} Using {display_name} close on {baseline_date} (closest to {portfolio_start_date}): ${baseline_close:.2f} as baseline")
            else:
                # Fallback to first available price
                baseline_close = benchmark_data["Close"].iloc[0]
                print(f"{_safe_emoji('⚠️')}  Fallback: Using first available {display_name} price: ${baseline_close:.2f} as baseline")
        
        scaling_factor = 100.0 / baseline_close
        benchmark_data[column_name] = benchmark_data["Close"] * scaling_factor
        
        # Create a complete date range matching portfolio dates
        benchmark_clean = benchmark_data[["Date", column_name]].copy()
        benchmark_clean['Date'] = pd.to_datetime(benchmark_clean['Date']).dt.date
        
        # Create a DataFrame with all portfolio dates and merge with benchmark data
        portfolio_date_range = pd.DataFrame({
            'Date': [pd.to_datetime(d).date() for d in portfolio_dates]
        })
        
        # Merge and forward-fill missing values (weekends, holidays)
        merged = portfolio_date_range.merge(benchmark_clean, on='Date', how='left')
        merged[column_name] = merged[column_name].ffill()
        
        # If we still have NaN values at the beginning, backfill
        merged[column_name] = merged[column_name].bfill()
        
        # Convert dates back to datetime and apply same market timing as portfolio
        merged['Date'] = pd.to_datetime(merged['Date'])
        
        # Apply market timing: trading days at market close (13:00 PST), weekends at midnight
        from datetime import timedelta
        for idx, row in merged.iterrows():
            date_only = row['Date'].date()
            weekday = pd.to_datetime(date_only).weekday()
            
            if weekday < 5:  # Trading day (Mon-Fri = 0-4)
                # Set to market close time: 1:00 PM PST (13:00) to match portfolio timing
                market_close_time = pd.to_datetime(date_only) + timedelta(hours=13)
                merged.at[idx, 'Date'] = market_close_time
            else:  # Weekend (Sat-Sun = 5-6)
                # Also use market close time for weekend days to match portfolio timing
                # This prevents misaligned dots and keeps both series consistent
                weekend_market_close = pd.to_datetime(date_only) + timedelta(hours=13)
                merged.at[idx, 'Date'] = weekend_market_close
        
        print(f"{_safe_emoji('📈')} {display_name} data: {len(benchmark_clean)} trading days -> {len(merged)} total days (with weekends)")
        return merged[["Date", column_name]]
        
    except Exception as e:
        print(f"{_safe_emoji('⚠️')}  Error downloading {display_name} data: {e}")
        print(f"{_safe_emoji('📊')} Creating flat {display_name} baseline for comparison")
        return pd.DataFrame({
            'Date': portfolio_dates,
            column_name: [100.0] * len(portfolio_dates)
        })


def download_sp500(start_date: pd.Timestamp, end_date: pd.Timestamp, portfolio_dates: pd.Series) -> pd.DataFrame:
    """Legacy function for backward compatibility - downloads S&P 500 benchmark."""
    return download_benchmark('sp500', start_date, end_date, portfolio_dates)


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
        print(f"{_safe_emoji('🔄')} Refreshing portfolio data to ensure current prices...")
        
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
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if latest_snapshot and latest_snapshot.positions:
            print(f"{_safe_emoji('💰')} Refreshing prices for {len(latest_snapshot.positions)} positions...")
            
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
                        print(f"{_safe_emoji('✅')} {position.ticker}: ${current_price:.2f}")
                    else:
                        print(f"{_safe_emoji('⚠️')}  {position.ticker}: Could not fetch current price")
                        updated_positions.append(position)  # Keep existing data
                except Exception as e:
                    print(f"{_safe_emoji('⚠️')}  {position.ticker}: Error fetching price - {e}")
                    updated_positions.append(position)  # Keep existing data
            
            # Save updated snapshot
            if updated_positions:
                from datetime import datetime
                updated_snapshot = latest_snapshot
                updated_snapshot.positions = updated_positions
                updated_snapshot.timestamp = datetime.now()
                
                portfolio_manager.save_snapshot(updated_snapshot)
                print(f"{_safe_emoji('✅')} Portfolio data refreshed successfully")
        else:
            print(f"{_safe_emoji('⚠️')}  No portfolio positions found to refresh")
            
    except Exception as e:
        print(f"{_safe_emoji('⚠️')}  Failed to refresh portfolio data: {e}")
        print(f"{_safe_emoji('📊')} Continuing with existing data...")

def main(args) -> dict:
    """Generate and display the comparison graph; return metrics."""
    # Get fund name from config
    try:
        sys.path.append(str(Path(__file__).parent.parent))
        from config.settings import get_settings
        settings = get_settings()
        fund_name = settings.get_fund_name()
    except Exception as e:
        print(f"{_safe_emoji('⚠️')}  Could not load fund name from config: {e}")
        fund_name = "Your Investments"  # Fallback
    
    # First, try to refresh portfolio data to get current prices
    refresh_portfolio_data(DATA_DIR if 'DATA_DIR' in globals() else None)
    
    llm_totals = load_portfolio_totals()

    start_date = llm_totals["Date"].min()
    end_date = llm_totals["Date"].max()
    portfolio_dates = llm_totals["Date"]
    
    # Handle multiple benchmarks for 'all' option
    if args.benchmark == 'all':
        benchmark_names = ['qqq', 'sp500', 'russell2000', 'vti']
        benchmark_data_dict = {}
        benchmark_configs = {}
        
        for bench_name in benchmark_names:
            print(f"{_safe_emoji('📥')} Downloading {bench_name.upper()} benchmark data...")
            benchmark_configs[bench_name] = get_benchmark_config(bench_name)
            benchmark_data_dict[bench_name] = download_benchmark(bench_name, start_date, end_date, portfolio_dates)
    else:
        # Single benchmark configuration
        benchmark_config = get_benchmark_config(args.benchmark)
        benchmark_data = download_benchmark(args.benchmark, start_date, end_date, portfolio_dates)

    # metrics
    peak_date, peak_gain = find_peak_performance(llm_totals)
    dd_date, dd_value, dd_pct = compute_drawdown(llm_totals)

    # plotting - optimized for financial time series (wide landscape)
    plt.figure(figsize=(16, 9))  # 16:9 aspect ratio, perfect for time series
    plt.style.use("seaborn-v0_8-whitegrid")

    # Show ACTUAL investment performance vs benchmark(s)
    current_performance = llm_totals["Performance_Pct"].iloc[-1]
    plt.plot(
        llm_totals["Date"],
        llm_totals["Performance_Index"],
        label=f"{fund_name} ({current_performance:+.2f}%)",
        marker="o",
        color="blue",
        linewidth=3,  # Slightly thicker for your portfolio
        zorder=10  # Ensure portfolio line is on top
    )
    
    if args.benchmark == 'all':
        # Plot all benchmarks with different colors and styles
        benchmark_colors = ['orange', 'green', 'red', 'purple']
        benchmark_styles = ['--', '-.', ':', (0, (3, 1, 1, 1))]  # Different line styles
        benchmark_markers = ['s', '^', 'v', 'D']
        
        for i, (bench_name, bench_data) in enumerate(benchmark_data_dict.items()):
            bench_config = benchmark_configs[bench_name]
            plt.plot(
                bench_data["Date"],
                bench_data[bench_config['column_name']],
                label=f"{bench_config['display_name']}",
                marker=benchmark_markers[i],
                color=benchmark_colors[i],
                linestyle=benchmark_styles[i],
                linewidth=2,
                alpha=0.8,
                markersize=4
            )
    else:
        # Single benchmark plot
        plt.plot(
            benchmark_data["Date"],
            benchmark_data[benchmark_config['column_name']],
            label=f"{benchmark_config['display_name']} Benchmark",
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
    portfolio_return = final_llm - 100.0
    
    # Portfolio performance annotation (always show)
    plt.annotate(
        f"{portfolio_return:+.1f}%",
        xy=(final_date, final_llm),
        xytext=(-40, 20),  # Left and up offset
        textcoords='offset points',
        color="blue",
        fontsize=11,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8),
        arrowprops=dict(arrowstyle="->", color="blue", alpha=0.7)
    )
    
    if args.benchmark == 'all':
        # For multiple benchmarks, show performance in legend instead of individual annotations
        # This keeps the chart clean and readable
        pass  # Performance is shown in the legend
    else:
        # Single benchmark performance annotation
        final_benchmark = float(benchmark_data[benchmark_config['column_name']].iloc[-1].item())
        benchmark_return = final_benchmark - 100.0
        
        plt.annotate(
            f"{benchmark_return:+.1f}%",
            xy=(final_date, final_benchmark),
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
    
    if args.benchmark == 'all':
        chart_title = f"Investment Performance Analysis\n${total_invested:,.0f} Invested -> {actual_return:+.2f}% Return (vs All Major Benchmarks)"
    else:
        chart_title = f"Investment Performance Analysis\n${total_invested:,.0f} Invested -> {actual_return:+.2f}% Return (vs {benchmark_config['display_name']})"
    
    plt.title(chart_title)
    # Add weekend/holiday shading for market closure clarity
    def add_market_closure_shading(start_date, end_date):
        """Add light gray shading for weekends when markets are closed.
        
        Shades Saturday 00:00 through Sunday 23:59 to clearly show when markets are closed.
        """
        import matplotlib.dates as mdates
        from datetime import timedelta
        
        current_date = start_date.date()
        end_date_only = end_date.date()
        weekend_labeled = False  # Track if we've added the legend label
        
        while current_date <= end_date_only:
            # Check if it's Saturday (start of weekend)
            weekday = pd.to_datetime(current_date).weekday()
            
            if weekday == 5:  # Saturday (start of weekend)
                # Shade from Saturday 00:00 to Monday 00:00 (covers entire weekend)
                weekend_start = pd.to_datetime(current_date)  # Saturday midnight
                weekend_end = weekend_start + pd.Timedelta(days=2)  # Monday midnight
                
                # Add shading for entire weekend period
                label = 'Weekend (Market Closed)' if not weekend_labeled else ""
                plt.axvspan(weekend_start, weekend_end, 
                           color='lightgray', alpha=0.2, zorder=0,
                           label=label)
                
                if not weekend_labeled:
                    weekend_labeled = True
                
                # Skip Sunday since we already covered the full weekend
                current_date += timedelta(days=2)
            else:
                current_date += timedelta(days=1)
            
            # TODO: Add major market holidays (New Year's, July 4th, Christmas, etc.)
            # For now, just handle weekends which are the most common
    
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
    print(f"{_safe_emoji('📊')} Saved chart to: {RESULTS_PATH.resolve()}")
    
    # Close the figure to free memory and prevent threading issues
    plt.close()
    
    # Open graph if requested and environment supports it
    # NOTE: Change default behavior for server/headless deployments
    if should_open_graph(args):
        open_graph_file(RESULTS_PATH)
    else:
        print(f"{_safe_emoji('📁')} Graph ready at: {RESULTS_PATH.resolve()}")

    return {
        "peak_performance_date": peak_date,
        "peak_performance_pct": peak_gain,
        "max_drawdown_date": dd_date,
        "max_drawdown_equity": dd_value,
        "max_drawdown_pct": dd_pct,
    }


if __name__ == "__main__":
    print("generating graph...")

    metrics = main(args)
    peak_d = metrics["peak_performance_date"].date()
    peak_p = metrics["peak_performance_pct"]
    dd_d = metrics["max_drawdown_date"].date()
    dd_e = metrics["max_drawdown_equity"]
    dd_p = metrics["max_drawdown_pct"]
    print(f"Peak performance: +{peak_p:.2f}% on {peak_d}")
    print(f"Max drawdown: {dd_p:.2f}% on {dd_d} (equity ${dd_e:.2f})")
