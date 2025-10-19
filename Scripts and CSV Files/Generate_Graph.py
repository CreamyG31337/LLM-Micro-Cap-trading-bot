import matplotlib
# Use Agg backend to prevent GUI windows and threading issues
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from pathlib import Path
import sys
import argparse
import json
import os
from decimal import Decimal
from dotenv import load_dotenv
sys.path.append(str(Path(__file__).parent.parent))
from display.console_output import _safe_emoji
from data.repositories.repository_factory import RepositoryFactory

# Load environment variables
load_dotenv(Path(__file__).parent.parent / 'web_dashboard' / '.env')

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
    parser.add_argument(
        '--fund',
        type=str,
        default=None,
        help='Fund name for repository-based data loading (default: auto-detect)'
    )
    return parser.parse_args()

# Parse arguments early
args = parse_arguments()

def get_data_source_config() -> str:
    """Get the configured data source from repository config"""
    try:
        config_file = Path("repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config.get("web_dashboard", {}).get("data_source", "hybrid")
    except Exception:
        pass
    return "hybrid"  # Default fallback

def load_portfolio_from_repository(fund_name: str = None) -> pd.DataFrame:
    """Load portfolio data from repository (Supabase or CSV based on config)"""
    try:
        data_source = get_data_source_config()
        print(f"{_safe_emoji('🔧')} Using data source: {data_source}")
        
        if data_source == "csv":
            # Use CSV loading logic (existing behavior)
            return load_portfolio_from_csv()
        elif data_source == "supabase":
            # Use Supabase repository
            return load_portfolio_from_supabase(fund_name)
        else:  # hybrid
            # Try Supabase first, fallback to CSV
            try:
                return load_portfolio_from_supabase(fund_name)
            except Exception as e:
                print(f"{_safe_emoji('⚠️')} Supabase failed, falling back to CSV: {e}")
                return load_portfolio_from_csv()
    except Exception as e:
        print(f"{_safe_emoji('❌')} Repository loading failed: {e}")
        return load_portfolio_from_csv()

def load_portfolio_from_csv() -> pd.DataFrame:
    """Load portfolio data from CSV (original behavior)"""
    llm_df = pd.read_csv(PORTFOLIO_CSV)
    print(f"{_safe_emoji('📊')} Loaded portfolio data from CSV with {len(llm_df)} rows")
    return llm_df

def load_portfolio_from_supabase(fund_name: str = None) -> pd.DataFrame:
    """Load portfolio data from Supabase repository"""
    # Check Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Missing Supabase credentials")
    
    # Create repository
    repository = RepositoryFactory.create_repository(
        'supabase',
        url=supabase_url,
        key=supabase_key,
        fund=fund_name
    )
    
    # Get portfolio data
    snapshots = repository.get_portfolio_data()
    
    if not snapshots:
        raise Exception("No portfolio data found in Supabase")
    
    # Convert snapshots to DataFrame format compatible with graph generator
    all_positions = []
    for snapshot in snapshots:
        if hasattr(snapshot, 'positions') and snapshot.positions:
            for position in snapshot.positions:
                # Get current price, fallback to avg_price if not available
                current_price_raw = getattr(position, 'current_price', None) or position.avg_price
                current_price = float(current_price_raw) if current_price_raw is not None else float(position.avg_price)
                shares_float = float(position.shares)
                
                pos_dict = {
                    'Date': snapshot.timestamp,
                    'Ticker': position.ticker,
                    'Shares': shares_float,
                    'Average Price': float(position.avg_price),
                    'Cost Basis': float(position.cost_basis),
                    'PnL': float(getattr(position, 'unrealized_pnl', 0) or getattr(position, 'pnl', 0) or 0),
                    'Currency': position.currency,
                    'Company': getattr(position, 'company', ''),
                    'Total Value': shares_float * current_price,
                    'Current Price': current_price,
                    'Stop Loss': float(getattr(position, 'stop_loss', 0) or 0),
                    'Action': 'HOLD'  # Default action for historical data
                }
                all_positions.append(pos_dict)
    
    if not all_positions:
        raise Exception("No individual positions found in Supabase snapshots")
    
    df = pd.DataFrame(all_positions)
    print(f"{_safe_emoji('📊')} Loaded portfolio data from Supabase with {len(df)} rows")
    return df

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
        print("   Example: python Generate_Graph.py --data-dir 'trading_data/funds/Project Chimera'")
        sys.exit(1)

# Extract fund name from data directory path (use actual fund name, NO FALLBACKS)
import re
if 'DATA_DIR' in globals() and DATA_DIR:
    # Get just the fund name from the path (e.g., "RRSP Lance Webull" from full path)
    fund_dir_name = Path(DATA_DIR).name
    
    # Try to load fund name from the fund's own config file first
    fund_config_path = Path(DATA_DIR) / "fund_config.json"
    if fund_config_path.exists():
        try:
            import json
            with open(fund_config_path, 'r') as f:
                fund_config = json.load(f)
            fund_name_from_config = fund_config.get('fund', {}).get('name', fund_dir_name)
            print(f"{_safe_emoji('📁')} Using fund name from config: {fund_name_from_config}")
        except Exception as e:
            print(f"{_safe_emoji('⚠️')}  Could not load fund config: {e}")
            fund_name_from_config = fund_dir_name
    else:
        fund_name_from_config = fund_dir_name
    
    # Use the actual fund name from the config - no splitting or manipulation
    fund_name = fund_name_from_config
    
    sanitized_fund_dir = re.sub(r'[^\w\-_\.]', '_', fund_dir_name).strip('_')
else:
    # NO FALLBACKS - require data directory to be specified
    print("❌ No data directory specified. Use --data-dir argument.")
    print("   Example: python Generate_Graph.py --data-dir 'trading_data/funds/RRSP Lance Webull'")
    sys.exit(1)

# Create benchmark identifier for filename
benchmark_short = args.benchmark.upper() if args.benchmark != 'all' else 'ALL'

# Save path in graphs folder with fund name, benchmark, and timestamp
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_PATH = Path(f"graphs/{sanitized_fund_dir}_vs_{benchmark_short}_portfolio_performance_{timestamp}.png")


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
    # Use repository-based loading (respects config settings)
    # Priority: 1) --fund argument, 2) fund name from data directory, 3) default
    global fund_name
    if args.fund:
        fund_to_load = args.fund
    elif 'fund_name' in globals() and fund_name:
        fund_to_load = fund_name
    else:
        fund_to_load = "Project Chimera"  # Default fallback
    
    print(f"{_safe_emoji('📊')} Loading data for fund: {fund_to_load}")
    llm_df = load_portfolio_from_repository(fund_to_load)
    
    # IMPORTANT: Portfolio refresh uses the same centralized logic as the main trading system
    # The graph generation intelligently refreshes data when needed (e.g., during market hours
    # or when missing trading days) and creates continuous timeline with forward-filling
    
    print(f"{_safe_emoji('📊')} Loaded portfolio data with {len(llm_df)} rows")
    print(f"{_safe_emoji('📊')} Columns: {list(llm_df.columns)}")
    
    # --- Data Cleaning and Preparation ---
    # Handle mixed date formats (some with timezone, some without)
    def parse_mixed_dates(date_str):
        """Parse dates that may have timezone info or not using timezone-aware parsing."""
        if pd.isna(date_str):
            return pd.NaT
        
        date_str = str(date_str).strip()
        
        # Use the same timezone parsing logic as the trading system to prevent warnings
        # Convert timezone abbreviations to UTC offsets before parsing
        if " PDT" in date_str:
            clean_date = date_str.replace(" PDT", "")
            date_with_offset = f"{clean_date}-07:00"
            return pd.to_datetime(date_with_offset, errors='coerce')
        elif " PST" in date_str:
            clean_date = date_str.replace(" PST", "")
            date_with_offset = f"{clean_date}-08:00"
            return pd.to_datetime(date_with_offset, errors='coerce')
        else:
            # No timezone info - parse normally
            return pd.to_datetime(date_str, errors='coerce')
    
    llm_df["Date"] = llm_df["Date"].apply(parse_mixed_dates)
    llm_df = llm_df.dropna(subset=['Date'])
    
    # Convert all dates to timezone-naive for consistent sorting
    def make_timezone_naive(ts):
        if pd.isna(ts):
            return ts
        if hasattr(ts, 'tz') and ts.tz is not None:
            return ts.tz_localize(None)
        return ts
    
    llm_df["Date"] = llm_df["Date"].apply(make_timezone_naive)
    
    llm_df = llm_df.sort_values("Date").reset_index(drop=True)
    
    numeric_cols = ['Shares', 'Average Price', 'Cost Basis', 'Current Price', 'Total Value', 'PnL']
    for col in numeric_cols:
        llm_df[col] = pd.to_numeric(llm_df[col], errors='coerce').fillna(0)

    print(f"{_safe_emoji('📅')} Portfolio data available from: {llm_df['Date'].min().date()} to {llm_df['Date'].max().date()}")
    print(f"{_safe_emoji('ℹ️')} Graph shows continuous timeline with forward-filled values for missing days")
    
    # --- Load Exchange Rates ---
    from utils.currency_converter import load_exchange_rates, convert_usd_to_cad
    from pathlib import Path
    from decimal import Decimal
    exchange_rates = load_exchange_rates(Path(DATA_DIR))

    # --- Progressive Portfolio Calculation ---
    daily_snapshots = []
    portfolio = {}  # Holds the state of our portfolio {ticker: {data}}
    
    # Get the date range from the data
    data_dates = pd.to_datetime(llm_df['Date'].dt.date.unique())
    if len(data_dates) > 0:
        start_date = data_dates.min()
        end_date = data_dates.max()
        
        # Create continuous timeline up to the last data date
        # This ensures missing trading days are filled with forward-filled values
        # Note: We only go up to the last available data date, not today
        # The trading system should be run first to refresh data for missing days
        from datetime import datetime, timedelta
        
        # Use the last available data date as the end date for the continuous timeline
        # This prevents extending beyond available data and creating false expectations
        end_date_for_range = end_date.date()
        
        # Create a continuous date range from start to the appropriate end date
        all_dates = pd.date_range(start=start_date, end=end_date_for_range, freq='D')
        
        # Add a baseline day one day before the earliest data
        baseline_date = start_date - pd.Timedelta(days=1)
        all_dates = pd.concat([pd.Series([baseline_date]), pd.Series(all_dates)]).sort_values()
    else:
        all_dates = pd.Series([])

    for current_date in all_dates:
        # Get all records for the current day
        day_df = llm_df[llm_df['Date'].dt.date == current_date.date()]

        # Update portfolio with the latest info from the day
        for _, row in day_df.iterrows():
            ticker = row['Ticker']
            # We take the last update for any given ticker on a given day
            portfolio[ticker] = row.to_dict()

        # Remove sold positions
        portfolio = {ticker: pos for ticker, pos in portfolio.items() if pos['Total Value'] > 0}
        
        # If no data for this day, use the last known portfolio state
        # This ensures we don't lose the portfolio state between days
        if day_df.empty and not portfolio:
            # No data for this day and no portfolio state - skip this day
            continue
        
        # If no data for this day but we have portfolio state, use it
        # This handles missing trading days by using the last known state
        if day_df.empty and portfolio:
            # Use the last known portfolio state for missing trading days
            # This ensures we don't lose the portfolio state between days
            pass  # Continue with existing portfolio state

        # --- Calculate Daily Totals ---
        if portfolio:
            total_cost_basis_cad = Decimal('0')
            total_market_value_cad = Decimal('0')

            for ticker, pos in portfolio.items():
                cost_basis = Decimal(str(pos.get('Cost Basis', 0)))
                market_value = Decimal(str(pos.get('Total Value', 0)))
                currency = pos.get('Currency', 'CAD')
                if pd.isna(currency):
                    currency = 'CAD'
                currency = currency.upper()

                if currency == 'USD':
                    total_cost_basis_cad += convert_usd_to_cad(cost_basis, exchange_rates, current_date)
                    total_market_value_cad += convert_usd_to_cad(market_value, exchange_rates, current_date)
                else:
                    total_cost_basis_cad += cost_basis
                    total_market_value_cad += market_value
            
            total_pnl = float(total_market_value_cad - total_cost_basis_cad)
            total_cost_basis = float(total_cost_basis_cad)
            total_market_value = float(total_market_value_cad)
            
            performance_pct = (total_pnl / total_cost_basis) * 100 if total_cost_basis > 0 else 0.0

            daily_snapshots.append({
                "Date": current_date,
                "Cost_Basis": total_cost_basis,
                "Market_Value": total_market_value,
                "Unrealized_PnL": total_pnl,
                "Performance_Pct": performance_pct
            })
            print(f"{_safe_emoji('📊')} {current_date.date()}: Invested ${total_cost_basis:,.2f} -> Worth ${total_market_value:,.2f} ({performance_pct:+.2f}%)")
        else:
            # Handle baseline day (no portfolio data yet)
            if len(daily_snapshots) == 0:
                # Create a baseline entry with $0 for the day before first data
                daily_snapshots.append({
                    "Date": current_date,
                    "Cost_Basis": 0.0,
                    "Market_Value": 0.0,
                    "Unrealized_PnL": 0.0,
                    "Performance_Pct": 0.0
                })
                print(f"{_safe_emoji('📊')} {current_date.date()}: Baseline day (no portfolio data yet)")

    if not daily_snapshots:
        print(f"{_safe_emoji('⚠️')}  No valid portfolio data found. Creating baseline entry.")
        return pd.DataFrame({"Date": [pd.Timestamp.now()], "Performance_Pct": [0.0], "Performance_Index": [100.0]})

    llm_totals = pd.DataFrame(daily_snapshots)
    print(f"{_safe_emoji('📈')} Calculated {len(llm_totals)} daily portfolio totals")

    # Normalize fund performance to start at 100 on first trading day (same as benchmarks)
    # Find the first actual trading day (not the baseline day)
    first_trading_day_idx = llm_totals[llm_totals["Cost_Basis"] > 0].index.min() if len(llm_totals[llm_totals["Cost_Basis"] > 0]) > 0 else 0
    
    if first_trading_day_idx is not None and not pd.isna(first_trading_day_idx):
        # Get the performance percentage on the first trading day
        first_day_performance = llm_totals.loc[first_trading_day_idx, "Performance_Pct"]
        
        # Adjust all performance percentages so the first trading day starts at 0% (index 100)
        # This ensures fund and benchmarks start at the same baseline
        adjustment = -first_day_performance
        llm_totals["Performance_Pct"] = llm_totals["Performance_Pct"] + adjustment
        
        print(f"{_safe_emoji('🎯')} Normalized fund performance: first trading day adjusted from {first_day_performance:+.2f}% to 0.00% (baseline)")
    
    llm_totals["Performance_Index"] = llm_totals["Performance_Pct"] + 100
    
    start_invested = llm_totals["Cost_Basis"].iloc[0]
    end_invested = llm_totals["Cost_Basis"].iloc[-1]
    start_performance = llm_totals["Performance_Pct"].iloc[0]
    end_performance = llm_totals["Performance_Pct"].iloc[-1]
    
    print(f"{_safe_emoji('📈')} Investment Performance: {start_performance:+.2f}% -> {end_performance:+.2f}%")
    print(f"{_safe_emoji('💰')} Total Capital Deployed: ${start_invested:,.2f} -> ${end_invested:,.2f}")
    
    llm_totals = create_continuous_timeline(llm_totals)
    return llm_totals


def create_continuous_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Create a continuous timeline with proper market timing representation.
    
    - Grid lines represent midnight (00:00)
    - Trading data points represent market close time (~13:00 PST)
    - Weekend/holiday values are forward-filled from last trading day
    - Missing trading days are forward-filled to create continuous timeline
    - Excludes today if market hasn't opened yet
    """
    if df.empty:
        return df
    
    # Get the date range - ensure we have proper datetime objects
    start_date = pd.to_datetime(df['Date'].min()).date()
    end_date = pd.to_datetime(df['Date'].max()).date()
    
    # Check if we should exclude today (if market hasn't opened yet)
    from market_data.market_hours import MarketHours
    from config.settings import Settings
    from datetime import datetime
    
    settings = Settings()
    market_hours = MarketHours(settings=settings)
    today = datetime.now().date()
    
    # If today is in the data but market hasn't opened, exclude it
    if today in [start_date, end_date] and not market_hours.is_market_open():
        print(f"ℹ️ Excluding today ({today}) from graph - market hasn't opened yet")
        # Filter out today's data
        df = df[df['Date'].dt.date != today]
        if df.empty:
            return df
        # Update end_date to exclude today
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
    
    # Forward fill all numeric columns (portfolio values don't change on weekends or missing days)
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
    """Download benchmark prices with cache-first optimization, normalize to $100 baseline, and forward-fill for weekends."""
    config = get_benchmark_config(benchmark_name)
    ticker = config['ticker']
    display_name = config['display_name']
    column_name = config['column_name']
    
    try:
        # Download with a few extra days buffer to ensure we get all needed data
        download_start = start_date - pd.Timedelta(days=5)
        download_end = end_date + pd.Timedelta(days=5)
        
        # Cache-first approach: Try to use cached data first
        benchmark_data = None
        cache_hit = False
        
        # Try to get cached data if available
        try:
            from market_data.price_cache import PriceCache
            price_cache = PriceCache()
            cached_data = price_cache.get_cached_price(ticker, download_start, download_end)
            
            if cached_data is not None and not cached_data.empty:
                benchmark_data = cached_data.reset_index()
                cache_hit = True
                print(f"{_safe_emoji('💾')} Using cached {display_name} data ({len(benchmark_data)} rows)")
        except Exception as cache_error:
            print(f"{_safe_emoji('⚠️')} Cache lookup failed for {ticker}: {cache_error}")
        
        # If no cached data, fetch fresh data
        if not cache_hit:
            print(f"{_safe_emoji('📥')} Fetching fresh {display_name} data...")
            benchmark_data = yf.download(ticker, start=download_start, end=download_end,
                                       progress=False, auto_adjust=False)
            benchmark_data = benchmark_data.reset_index()
            
            # Cache the fresh data for future use
            try:
                from market_data.price_cache import PriceCache
                price_cache = PriceCache()
                price_cache.cache_price_data(ticker, benchmark_data, "yfinance")
                print(f"{_safe_emoji('💾')} Cached {display_name} data for future use")
            except Exception as cache_error:
                print(f"{_safe_emoji('⚠️')} Failed to cache {ticker} data: {cache_error}")
        
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
        
        # Use the first actual trading day (not the baseline day) for benchmark normalization
        # This ensures benchmarks start at exactly $100
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
    return pd.Timestamp(row["Date"]), float(row["Market_Value"]), float(row["Drawdown %"])



def get_historical_price_for_date(ticker, target_date, market_data_fetcher):
    """
    Get historical closing price for a ticker on a specific date.
    
    This uses the same logic as the rebuild script to fetch historical prices.
    
    Args:
        ticker: Stock ticker symbol
        target_date: datetime.date object for the target date
        market_data_fetcher: MarketDataFetcher instance
        
    Returns:
        Historical close price as float, or None if not available
    """
    try:
        from datetime import timedelta
        import pandas as pd
        
        # Try multiple date ranges to find available data
        date_ranges = [
            (target_date, target_date + timedelta(days=1)),  # Exact day
            (target_date - timedelta(days=1), target_date + timedelta(days=2)),  # 3-day window
            (target_date - timedelta(days=3), target_date + timedelta(days=4)),  # 7-day window
        ]
        
        for start_date, end_date in date_ranges:
            result = market_data_fetcher.fetch_price_data(ticker, pd.Timestamp(start_date), pd.Timestamp(end_date))
            df = result.df
            
            if df is not None and not df.empty and 'Close' in df.columns and result.source != "empty":
                # Find row matching the target date or closest available
                day_rows = df[df.index.date == target_date]
                if not day_rows.empty:
                    return float(day_rows['Close'].iloc[0])
                # If no exact match, try to find closest date within range
                available_dates = df.index.date
                closest_dates = [d for d in available_dates if d <= target_date]
                if closest_dates:
                    closest_date = max(closest_dates)
                    closest_rows = df[df.index.date == closest_date]
                    if not closest_rows.empty:
                        return float(closest_rows['Close'].iloc[0])
        
        return None
    except Exception as e:
        print(f"       Error fetching historical price for {ticker}: {e}")
        return None


def create_historical_snapshots_for_missing_days(data_dir_path, market_hours, portfolio_manager, repository, market_data_fetcher):
    """
    Create historical portfolio snapshots for ACTUAL missing trading days only.
    
    Requirements:
    1. Weekends/Holidays: Do NOT create snapshots (will be forward-filled in graph)
    2. Missing Trading Days: Create snapshots with REAL historical prices from API
    
    This uses the same historical price fetching logic as the rebuild script.
    
    Args:
        data_dir_path: Path to the data directory
        market_hours: MarketHours instance
        portfolio_manager: PortfolioManager instance
        repository: Repository instance
        market_data_fetcher: MarketDataFetcher instance
    """
    try:
        from utils.missing_trading_days import MissingTradingDayDetector
        from datetime import datetime, timedelta
        import pandas as pd
        
        detector = MissingTradingDayDetector(market_hours, portfolio_manager)
        needs_update, missing_days, most_recent = detector.check_for_missing_trading_days()
        
        if not needs_update or not missing_days:
            print(f"{_safe_emoji('ℹ️')} No missing trading days detected")
            return
        
        # Load the CSV to check which days actually have data
        csv_path = Path(data_dir_path) / "llm_portfolio_update.csv"
        if not csv_path.exists():
            print(f"{_safe_emoji('⚠️')} Portfolio CSV not found")
            return
        
        portfolio_df = pd.read_csv(csv_path)
        
        # Parse dates handling timezone info (PDT/PST)
        def parse_date_with_tz(date_str):
            if pd.isna(date_str):
                return pd.NaT
            date_str = str(date_str).strip()
            # Strip timezone abbreviations before parsing
            if " PDT" in date_str:
                date_str = date_str.replace(" PDT", "").strip()
            elif " PST" in date_str:
                date_str = date_str.replace(" PST", "").strip()
            return pd.to_datetime(date_str, errors='coerce')
        
        portfolio_df['Parsed_Date'] = portfolio_df['Date'].apply(parse_date_with_tz)
        
        # Extract date objects, handling any that didn't parse
        def extract_date(dt_value):
            if pd.isna(dt_value):
                return None
            if hasattr(dt_value, 'date'):
                return dt_value.date()
            return None
        
        existing_dates = set(filter(None, portfolio_df['Parsed_Date'].apply(extract_date).unique()))
        
        # Filter to only truly missing trading days (days with NO data in CSV) and are trading days
        truly_missing_days = [day for day in missing_days if (day not in existing_dates and market_hours.is_trading_day(day))]
        
        if not truly_missing_days:
            print(f"{_safe_emoji('✅')} No trading days need backfill - only weekends/holidays missing or already present")
            return
        
        print(f"{_safe_emoji('🔄')} Backfilling {len(truly_missing_days)} missing TRADING days with historical prices...")
        
        # Get the latest portfolio positions to work with
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if not latest_snapshot or not latest_snapshot.positions:
            print(f"{_safe_emoji('⚠️')} No portfolio positions found to create historical snapshots")
            return
        
        # Create snapshots for each truly missing trading day
        for missing_day in truly_missing_days:
            try:
                print(f"   Creating snapshot for {missing_day.strftime('%Y-%m-%d')}...")
                
                # Create a new snapshot for this historical day
                historical_positions = []
                
                for position in latest_snapshot.positions:
                    # Get historical price for this position on this day
                    # Convert missing_day to date if it's a datetime
                    target_date = missing_day.date() if hasattr(missing_day, 'date') else missing_day
                    
                    try:
                        # Use the same historical price fetching logic as the rebuild script
                        historical_price = get_historical_price_for_date(position.ticker, target_date, market_data_fetcher)
                        
                        if historical_price:
                            # Create updated position with historical price and proper calculations
                            from data.models.portfolio import Position
                            from decimal import Decimal
                            
                            hist_price_decimal = Decimal(str(historical_price))
                            market_value = position.shares * hist_price_decimal
                            unrealized_pnl = market_value - position.cost_basis
                            
                            historical_position = Position(
                                ticker=position.ticker,
                                shares=position.shares,
                                avg_price=position.avg_price,
                                cost_basis=position.cost_basis,
                                current_price=hist_price_decimal,
                                market_value=market_value,
                                unrealized_pnl=unrealized_pnl,
                                currency=position.currency,
                                company=position.company
                            )
                            historical_positions.append(historical_position)
                            print(f"     {position.ticker}: ${historical_price:.2f} (value: ${market_value:.2f}, PnL: ${unrealized_pnl:.2f})")
                        else:
                            # Keep existing position data if no historical price found
                            historical_positions.append(position)
                            print(f"     {position.ticker}: No historical price found, using last known")
                            
                    except Exception as e:
                        # Keep existing position data if there's an error
                        historical_positions.append(position)
                        print(f"     {position.ticker}: Error fetching historical price - {e}")
                
                # Create historical snapshot
                from data.models.portfolio import PortfolioSnapshot
                # Create timestamp for market close on the missing day
                if hasattr(missing_day, 'date'):
                    snapshot_date = missing_day.date()  # missing_day is datetime
                else:
                    snapshot_date = missing_day  # missing_day is already date
                    
                # Use proper timezone handling for historical snapshots
                # Market closes at 16:00 ET (Eastern Time)
                from market_config import _is_dst
                from datetime import timezone as dt_timezone
                utc_now = datetime.now(dt_timezone.utc)
                is_dst = _is_dst(utc_now)
                # 16:00 ET = 20:00 UTC during EDT, 21:00 UTC during EST
                market_close_hour_utc = 20 if is_dst else 21

                # Create timestamp for market close in Eastern timezone
                historical_timestamp = datetime.combine(
                    snapshot_date,
                    datetime.min.time().replace(hour=market_close_hour_utc, minute=0, second=0, microsecond=0)
                ).replace(tzinfo=dt_timezone.utc)
                
                historical_snapshot = PortfolioSnapshot(
                    positions=historical_positions,
                    timestamp=historical_timestamp
                )
                
                # Save historical snapshot
                repository.save_portfolio_snapshot(historical_snapshot)
                print(f"     ✅ Created snapshot for {missing_day.strftime('%Y-%m-%d')} with {len(historical_positions)} positions")
                
            except Exception as e:
                print(f"     ⚠️ Error creating snapshot for {missing_day.strftime('%Y-%m-%d')}: {e}")
        
        print(f"✅ Completed creating historical snapshots for missing trading days")
        
    except Exception as e:
        print(f"⚠️ Error creating historical snapshots: {e}")


def refresh_portfolio_data_if_needed(data_dir_path):
    """
    Refresh portfolio data using the centralized trading system logic.
    
    This function uses the same portfolio refresh logic as the main trading system
    to ensure consistency and avoid code duplication. It intelligently decides
    whether to refresh data based on market hours and existing data.
    
    Args:
        data_dir_path: Path to the data directory
    """
    try:
        print(f"{_safe_emoji('🔄')} Checking if portfolio data refresh is needed...")
        
        # Import the trading system components
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from config.settings import get_settings
        from data.repositories.repository_factory import get_repository_container, configure_repositories
        from portfolio.portfolio_manager import PortfolioManager
        from market_data.market_hours import MarketHours
        from utils.portfolio_refresh import refresh_portfolio_prices_if_needed
        from portfolio.fund_manager import Fund, RepositorySettings
        
        # Configure settings and repository
        settings = get_settings()
        if data_dir_path:
            settings._data_directory = str(data_dir_path)
            settings._config['repository']['csv']['data_directory'] = str(data_dir_path)
        else:
            if 'DATA_DIR' in globals() and DATA_DIR:
                settings._data_directory = str(DATA_DIR)
                settings._config['repository']['csv']['data_directory'] = str(DATA_DIR)
            else:
                print(f"{_safe_emoji('ℹ️')} No data directory specified - using existing data")
                return
        
        repo_config = settings.get_repository_config()
        configure_repositories({'default': repo_config})
        repository = get_repository_container().get_repository('default')
        
        # Create a basic Fund object for the PortfolioManager
        fund = Fund(
            id="graph_generator",
            name="Graph Generator Fund",
            description="Temporary fund for graph generation",
            repository=RepositorySettings(
                type="csv",
                settings={'data_directory': str(data_dir_path) if data_dir_path else str(DATA_DIR)}
            )
        )
        
        # Initialize components
        portfolio_manager = PortfolioManager(repository, fund)
        market_hours = MarketHours(settings=settings)
        
        # Initialize market data fetcher for historical data
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        price_cache = PriceCache(settings=settings)
        market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
        
        # STEP 1: Backfill missing trading days with historical prices
        # This ensures we have complete data before refreshing current prices
        create_historical_snapshots_for_missing_days(
            data_dir_path=data_dir_path if data_dir_path else DATA_DIR,
            market_hours=market_hours,
            portfolio_manager=portfolio_manager,
            repository=repository,
            market_data_fetcher=market_data_fetcher
        )
        
        # Recreate portfolio manager to reload data from disk after backfilling
        # This ensures the refresh logic sees the freshly backfilled data
        portfolio_manager = PortfolioManager(repository, fund)
        
        # Clear price cache to ensure fresh prices are fetched for today
        # This prevents reusing historical prices from the backfill step
        if hasattr(price_cache, '_price_cache'):
            price_cache._price_cache = {}
        
        # STEP 2: Refresh current prices for today's snapshot
        was_updated, reason = refresh_portfolio_prices_if_needed(
            market_hours=market_hours,
            portfolio_manager=portfolio_manager,
            repository=repository,
            market_data_fetcher=market_data_fetcher,
            price_cache=price_cache,
            verbose=True
        )
        
        if was_updated:
            print(f"{_safe_emoji('✅')} Portfolio data refreshed: {reason}")
        else:
            print(f"{_safe_emoji('ℹ️')} {reason}")
            
    except Exception as e:
        print(f"{_safe_emoji('⚠️')} Failed to refresh portfolio data: {e}")
        print(f"{_safe_emoji('📊')} Continuing with existing data...")


def main(args) -> dict:
    """Generate and display the comparison graph; return metrics."""
    
    # DISABLED: Portfolio refresh was creating duplicate/corrupted snapshots
    # The graph should use existing data, not create new snapshots
    # refresh_portfolio_data_if_needed(DATA_DIR if 'DATA_DIR' in globals() and DATA_DIR else None)
    
    llm_totals = load_portfolio_totals()

    # Use the first actual trading day (not the baseline day) for benchmark normalization
    # This ensures benchmarks start at exactly $100
    start_date = llm_totals["Date"].min()
    end_date = llm_totals["Date"].max()
    portfolio_dates = llm_totals["Date"]
    
    # Find the first actual trading day (skip baseline day with $0 portfolio)
    first_trading_day = llm_totals[llm_totals["Cost_Basis"] > 0]["Date"].min()
    if pd.notna(first_trading_day):
        benchmark_start_date = first_trading_day
    else:
        benchmark_start_date = start_date
    
    # Handle multiple benchmarks for 'all' option
    if args.benchmark == 'all':
        benchmark_names = ['qqq', 'sp500', 'russell2000', 'vti']
        benchmark_data_dict = {}
        benchmark_configs = {}
        
        for bench_name in benchmark_names:
            print(f"{_safe_emoji('📥')} Downloading {bench_name.upper()} benchmark data...")
            benchmark_configs[bench_name] = get_benchmark_config(bench_name)
            benchmark_data_dict[bench_name] = download_benchmark(bench_name, benchmark_start_date, end_date, portfolio_dates)
    else:
        # Single benchmark configuration
        benchmark_config = get_benchmark_config(args.benchmark)
        benchmark_data = download_benchmark(args.benchmark, benchmark_start_date, end_date, portfolio_dates)

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

    # Smart annotation positioning functions
    def find_optimal_text_position(x_data, y_data, x_pos, y_pos, ax, preferred_side='right'):
        """Find optimal position for text annotation to avoid overlaps and stay within bounds."""
        # Simple heuristic-based positioning without complex coordinate transforms
        # This avoids matplotlib's coordinate system complexity

        # Get the data ranges to understand where we are
        x_min, x_max = x_data.min(), x_data.max()
        y_min, y_max = y_data.min(), y_data.max()

        # Convert to numerical values for comparison
        if hasattr(x_pos, 'timestamp'):  # pandas Timestamp
            x_pos_num = x_pos.timestamp()
            x_min_num = x_min.timestamp()
            x_max_num = x_max.timestamp()
        else:
            x_pos_num = x_pos
            x_min_num = x_min
            x_max_num = x_max

        # Determine relative position in the plot
        x_relative = (x_pos_num - x_min_num) / (x_max_num - x_min_num) if x_max_num != x_min_num else 0.5
        y_relative = (y_pos - y_min) / (y_max - y_min) if y_max != y_min else 0.5

        # Smart positioning based on relative position with much increased distances
        if preferred_side == 'right':
            # For points in left half, prefer right positioning
            if x_relative < 0.6:
                return ('right', 100, 0)
            # For points in right half, prefer left positioning
            elif x_relative > 0.4:
                return ('left', -100, 0)
            # For middle, try above or below
            else:
                if y_relative > 0.5:
                    return ('below', 0, -100)
                else:
                    return ('above', 0, 100)
        else:
            # For end labels, prefer left side with much extra distance
            if x_relative > 0.3:
                return ('left', -100, 0)
            else:
                return ('right', 100, 0)

    def create_smart_annotation(text, x_pos, y_pos, color, facecolor, ax, preferred_side='right', fontsize=10):
        """Create an annotation with smart positioning."""
        _, x_offset, y_offset = find_optimal_text_position(x_data=llm_totals["Date"],
                                                         y_data=llm_totals["Performance_Index"],
                                                         x_pos=x_pos, y_pos=y_pos, ax=ax,
                                                         preferred_side=preferred_side)

        plt.annotate(
            text,
            xy=(x_pos, y_pos),
            xytext=(x_offset, y_offset),
            textcoords='offset points',
            color=color,
            fontsize=fontsize,
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.4", facecolor=facecolor, alpha=0.85,
                     edgecolor=color, linewidth=1),
            arrowprops=dict(arrowstyle="->", color=color, alpha=0.8, linewidth=1.5,
                          shrinkA=5, shrinkB=5),
            zorder=20  # High z-order to ensure annotations appear on top
        )

    # Get current axis for positioning calculations
    ax = plt.gca()

    # annotate peak performance - always position above
    peak_value = float(
        llm_totals.loc[llm_totals["Date"] == peak_date, "Performance_Index"].iloc[0]
    )
    
    plt.annotate(
        f"[+] +{peak_gain:.1f}% Peak",
        xy=(peak_date, peak_value),
        xytext=(0, 80),  # Always above the peak
        textcoords='offset points',
        color="darkgreen",
        fontsize=11,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightgreen", alpha=0.85,
                 edgecolor="darkgreen", linewidth=1),
        arrowprops=dict(arrowstyle="->", color="darkgreen", alpha=0.8, linewidth=1.5,
                      shrinkA=5, shrinkB=5),
        zorder=20
    )

    # annotate final P/Ls - position within plot area
    final_date = llm_totals["Date"].iloc[-1]
    final_llm = float(llm_totals["Performance_Index"].iloc[-1])
    portfolio_return = final_llm - 100.0

    # Portfolio performance annotation (always show) - position down
    plt.annotate(
        f"[*] {portfolio_return:+.1f}% Total Return",
        xy=(final_date, final_llm),
        xytext=(0, -80),  # Always below the final point
        textcoords='offset points',
        color="darkblue",
        fontsize=12,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightblue", alpha=0.85,
                 edgecolor="darkblue", linewidth=1),
        arrowprops=dict(arrowstyle="->", color="darkblue", alpha=0.8, linewidth=1.5,
                      shrinkA=5, shrinkB=5),
        zorder=20
    )

    if args.benchmark == 'all':
        # For multiple benchmarks, show performance in legend instead of individual annotations
        # This keeps the chart clean and readable
        pass  # Performance is shown in the legend
    else:
        # Single benchmark performance annotation - prefer left side
        final_benchmark = float(benchmark_data[benchmark_config['column_name']].iloc[-1].item())
        benchmark_return = final_benchmark - 100.0

        plt.annotate(
            f"[=] {benchmark_return:+.1f}% Benchmark",
            xy=(final_date, final_benchmark),
            xytext=(0, -100),  # Straight down from the benchmark point
            textcoords='offset points',
            color="darkorange",
            fontsize=11,
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.85,
                     edgecolor="darkorange", linewidth=1),
            arrowprops=dict(arrowstyle="->", color="darkorange", alpha=0.8, linewidth=1.5,
                          shrinkA=5, shrinkB=5),
            zorder=20
        )

    # annotate max drawdown - position to the right
    dd_normalized = llm_totals.loc[llm_totals["Date"] == dd_date, "Performance_Index"].iloc[0] if len(llm_totals.loc[llm_totals["Date"] == dd_date]) > 0 else 100
    
    plt.annotate(
        f"[-] {dd_pct:.1f}% Max Drawdown",
        xy=(dd_date, dd_normalized),
        xytext=(100, 0),  # Right from the drawdown point
        textcoords='offset points',
        color="darkred",
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightcoral", alpha=0.85,
                 edgecolor="darkred", linewidth=1),
        arrowprops=dict(arrowstyle="->", color="darkred", alpha=0.8, linewidth=1.5,
                      shrinkA=5, shrinkB=5),
        zorder=20
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
    
    # Enhanced date axis with more labels and grid lines
    import matplotlib.dates as mdates

    # Calculate the date range to determine optimal tick frequency
    date_range = (llm_totals["Date"].max() - llm_totals["Date"].min()).days

    # Set up date formatting and locator based on date range
    if date_range <= 7:  # Very short range - show every day
        locator = mdates.DayLocator()
        date_format = '%m/%d'
        minor_locator = mdates.HourLocator(byhour=[9, 12, 15])  # Show market hours
    elif date_range <= 30:  # Short range - show every 2-3 days
        locator = mdates.DayLocator(interval=2)
        date_format = '%m/%d'
        minor_locator = mdates.DayLocator()
    elif date_range <= 90:  # Medium range - show weekly
        locator = mdates.WeekdayLocator(byweekday=mdates.MO)
        date_format = '%m/%d'
        minor_locator = mdates.DayLocator(interval=1)
    elif date_range <= 365:  # Long range - show monthly
        locator = mdates.MonthLocator()
        date_format = '%Y-%m'
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MO)
    else:  # Very long range - show quarterly
        locator = mdates.MonthLocator(interval=3)
        date_format = '%Y-%m'
        minor_locator = mdates.MonthLocator()

    # Apply the date formatting
    plt.gca().xaxis.set_major_locator(locator)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    plt.gca().xaxis.set_minor_locator(minor_locator)

    # Add more detailed grid lines
    plt.grid(True, which='major', axis='x', alpha=0.4, linewidth=1)  # Major vertical grid lines
    plt.grid(True, which='minor', axis='x', alpha=0.2, linewidth=0.5)  # Minor vertical grid lines
    plt.grid(True, which='major', axis='y', alpha=0.3, linewidth=0.8)  # Horizontal grid lines

    plt.xlabel("Date (Times shown in EST - market timezone)")
    plt.ylabel("Performance Index (100 = Break-even)")
    plt.xticks(rotation=45)  # Keep rotation for better readability
    plt.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)
    
    # Better layout management
    plt.subplots_adjust(left=0.08, bottom=0.12, right=0.95, top=0.88, hspace=0.2, wspace=0.2)

    # --- Auto-save to project root with optimized settings ---
    # Ensure the directory exists before saving
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
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
