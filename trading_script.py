"""Refactored trading script with modular architecture.

This is the main orchestrator for the trading system, now using a modular architecture
with proper separation of concerns. The script coordinates between different modules
while maintaining backward compatibility with existing CSV files and workflows.

Key improvements:
- Modular architecture with clear separation of concerns
- Repository pattern for data access abstraction
- Dependency injection for component management
- Comprehensive error handling and logging
- Future-ready for database migration and web dashboard
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Modular startup check - handles path setup and dependency checking
try:
    from utils.script_startup import startup_check
    startup_check("trading_script.py")
except ImportError:
    # Fallback for minimal dependency checking if script_startup isn't available
    try:
        import pandas
    except ImportError:
        print("\n❌ Missing Dependencies (trading_script.py)")
        print("Required packages not found. Please activate virtual environment:")
        if os.name == 'nt':  # Windows
            print("  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print("  source venv/bin/activate")
        print("  python trading_script.py")
        print("\n💡 TIP: Use 'python run.py' to avoid dependency issues")
        sys.exit(1)

# Force fallback mode to avoid Windows console encoding issues
# os.environ["FORCE_FALLBACK"] = "true"

import pandas as pd

# Core system imports
from config.settings import Settings, get_settings, configure_system
from config.constants import DEFAULT_DATA_DIR, LOG_FILE, VERSION

# Repository and data access
from data.repositories.repository_factory import RepositoryFactory, get_repository_container, configure_repositories
from data.repositories.base_repository import BaseRepository, RepositoryError
from data.models.portfolio import PortfolioSnapshot

# Business logic modules
from portfolio.portfolio_manager import PortfolioManager
from portfolio.fifo_trade_processor import FIFOTradeProcessor
from portfolio.position_calculator import PositionCalculator
from portfolio.trading_interface import TradingInterface

from market_data.data_fetcher import MarketDataFetcher
from market_data.market_hours import MarketHours
from market_data.price_cache import PriceCache

from financial.calculations import money_to_decimal, calculate_cost_basis, calculate_position_value
from financial.currency_handler import CurrencyHandler
from financial.pnl_calculator import PnLCalculator

# Display and utilities
from display.console_output import print_success, print_error, print_warning, print_info, print_header, print_environment_banner
from display.table_formatter import TableFormatter
from display.terminal_utils import detect_terminal_width, check_table_display_issues

from utils.timezone_utils import get_trading_timezone, format_timestamp_for_csv
from utils.validation import validate_portfolio_data, validate_trade_data
from utils.backup_manager import BackupManager
from utils.system_utils import setup_error_handlers, validate_system_requirements, log_system_info, InitializationError
from utils.hash_verification import require_script_integrity, initialize_launch_time, ScriptIntegrityError

# Global logger
logger = logging.getLogger(__name__)


class TradingSystemError(Exception):
    """Base exception for trading system errors."""
    pass


def setup_logging(settings: Settings) -> None:
    """Setup logging configuration.
    
    Args:
        settings: System settings containing logging configuration
    """
    log_config = settings.get_logging_config()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_config.get('file', LOG_FILE)),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info(f"Logging configured - Level: {log_config.get('level', 'INFO')}")


def check_dependencies() -> dict[str, bool]:
    """Check for optional dependencies and return availability status.
    
    Returns:
        Dictionary mapping dependency names to availability status
    """
    dependencies = {}
    
    # Check for market configuration
    try:
        from market_config import get_timezone_config, get_timezone_offset, get_timezone_name
        dependencies['market_config'] = True
        logger.info("Market configuration module available")
    except ImportError:
        dependencies['market_config'] = False
        logger.warning("Market configuration module not found - using defaults")
    
    # Check for dual currency support
    try:
        from dual_currency import CashBalances, get_ticker_currency
        dependencies['dual_currency'] = True
        logger.info("Dual currency module available")
    except ImportError:
        dependencies['dual_currency'] = False
        logger.warning("Dual currency module not found - single currency mode")
    
    # Check for pandas-datareader (Stooq fallback)
    try:
        import pandas_datareader.data as pdr
        dependencies['pandas_datareader'] = True
        logger.info("Pandas-datareader available for Stooq fallback")
    except ImportError:
        dependencies['pandas_datareader'] = False
        logger.warning("Pandas-datareader not available - limited fallback options")
    
    # Check for Rich/colorama display libraries
    try:
        from rich.console import Console
        from colorama import init
        dependencies['rich_display'] = True
        logger.info("Rich display libraries available")
    except ImportError:
        dependencies['rich_display'] = False
        logger.warning("Rich display libraries not available - using plain text")
    
    return dependencies


def initialize_repository(settings: Settings) -> BaseRepository:
    """Initialize repository based on configuration.
    
    Args:
        settings: System settings containing repository configuration
        
    Returns:
        Initialized repository instance
        
    Raises:
        InitializationError: If repository initialization fails
    """
    try:
        repo_config = settings.get_repository_config()
        repository_type = repo_config.get('type', 'csv')
        
        logger.info(f"Initializing {repository_type} repository")
        
        # Configure repository container
        configure_repositories({'default': repo_config})
        
        # Get repository instance
        repository = get_repository_container().get_repository('default')
        
        logger.info(f"Repository initialized: {type(repository).__name__}")
        return repository
        
    except Exception as e:
        error_msg = f"Failed to initialize repository: {e}"
        logger.error(error_msg)
        raise InitializationError(error_msg) from e


def initialize_components(settings: Settings, repository: BaseRepository, dependencies: dict[str, bool]) -> None:
    """Initialize all system components with dependency injection.
    
    Args:
        settings: System settings
        repository: Initialized repository instance
        dependencies: Dictionary of available dependencies
        
    Raises:
        InitializationError: If component initialization fails
    """
    global portfolio_manager, trade_processor, position_calculator, trading_interface
    global market_data_fetcher, market_hours, price_cache
    global currency_handler, pnl_calculator, table_formatter, backup_manager
    
    try:
        logger.info("Initializing system components...")
        
        # Initialize portfolio components
        portfolio_manager = PortfolioManager(repository)
        trade_processor = FIFOTradeProcessor(repository)
        position_calculator = PositionCalculator(repository)
        trading_interface = TradingInterface(repository, trade_processor)
        
        # Initialize market data components
        price_cache = PriceCache()
        market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
        market_hours = MarketHours(settings=settings)
        
        # Initialize financial components
        data_dir = Path(settings.get_data_directory())
        currency_handler = CurrencyHandler(data_dir=data_dir)
        pnl_calculator = PnLCalculator()
        
        # Initialize display components
        table_formatter = TableFormatter(
            data_dir=settings.get_data_directory(),
            web_mode=False
        )
        
        # Initialize utility components
        backup_config = settings.get_backup_config()
        backup_manager = BackupManager(
            data_dir=data_dir,
            backup_dir=Path(backup_config.get('directory', 'backups'))
        )
        
        logger.info("All system components initialized successfully")
        
    except Exception as e:
        error_msg = f"Failed to initialize system components: {e}"
        logger.error(error_msg)
        raise InitializationError(error_msg) from e


def handle_graceful_degradation(dependencies: dict[str, bool]) -> None:
    """Handle graceful degradation for missing optional dependencies.
    
    Args:
        dependencies: Dictionary of available dependencies
    """
    if not dependencies.get('market_config', True):
        print_warning("Market configuration not available - using default timezone settings")
    
    if not dependencies.get('dual_currency', True):
        print_warning("Dual currency support not available - using single currency mode")
    
    if not dependencies.get('pandas_datareader', True):
        print_warning("Pandas-datareader not available - Stooq fallback disabled")
    
    if not dependencies.get('rich_display', True):
        print_warning("Rich display libraries not available - using plain text output")
    
    # Check for critical missing dependencies
    critical_missing = []
    
    if critical_missing:
        error_msg = f"Critical dependencies missing: {', '.join(critical_missing)}"
        print_error(error_msg)
        print_error("Please install missing dependencies and try again")
        sys.exit(1)


def parse_command_line_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Trading System - Portfolio Management and Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_script.py                           # Use default data directory
  python trading_script.py --data-dir "trading_data/dev"   # Use test data directory
  python trading_script.py --config config.json     # Use custom configuration
  python trading_script.py --debug                  # Enable debug logging
  python trading_script.py --validate-only          # Only validate data integrity
        """
    )
    
    parser.add_argument(
        'file_path',
        nargs='?',
        default=None,
        help='Path to portfolio CSV file (optional, uses default from config)'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='Data directory path (overrides config setting)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate data integrity and exit'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before processing'
    )
    
    parser.add_argument(
        '--force-fallback',
        action='store_true',
        help='Force fallback mode for testing'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'Trading System {VERSION}'
    )
    
    return parser.parse_args()


def initialize_system(args: argparse.Namespace) -> tuple[Settings, BaseRepository, dict[str, bool]]:
    """Initialize the trading system with configuration and dependencies.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Tuple of (settings, repository, dependencies)
        
    Raises:
        InitializationError: If system initialization fails
    """
    try:
        print_header("Trading System Initialization", "🚀")
        
        # Configure system settings
        settings = configure_system(args.config)
        
        # Override settings from command-line arguments
        if args.data_dir:
            settings.set('repository.csv.data_directory', args.data_dir)
        
        # Show environment banner (after command-line overrides)
        data_dir = settings.get_data_directory()
        print_environment_banner(data_dir)
        
        if args.debug:
            settings.set('logging.level', 'DEBUG')
        
        # Setup logging
        setup_logging(settings)
        
        # Check dependencies
        dependencies = check_dependencies()
        
        # Handle graceful degradation
        handle_graceful_degradation(dependencies)
        
        # Initialize repository
        repository = initialize_repository(settings)
        
        # Initialize components
        initialize_components(settings, repository, dependencies)
        
        print_success("System initialization completed successfully")
        
        return settings, repository, dependencies
        
    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        print_error(error_msg)
        logger.error(error_msg, exc_info=True)
        raise InitializationError(error_msg) from e


def verify_script_before_action() -> None:
    """Verify script integrity before allowing sensitive operations.
    
    Raises:
        ScriptIntegrityError: If script integrity cannot be verified
    """
    try:
        project_root = Path(__file__).parent.absolute()
        require_script_integrity(project_root)
    except ScriptIntegrityError as e:
        print_error(f"Script integrity verification failed: {e}")
        print_error("Trading operations are disabled for security reasons")
        raise
    except Exception as e:
        print_error(f"Script integrity check failed: {e}")
        print_error("Trading operations are disabled for security reasons")
        raise ScriptIntegrityError(f"Script integrity check failed: {e}") from e


def run_portfolio_workflow(args: argparse.Namespace, settings: Settings, repository: BaseRepository, trading_interface: TradingInterface) -> None:
    """Run the main portfolio management workflow.
    
    Args:
        args: Parsed command-line arguments
        settings: System settings
        repository: Initialized repository
        trading_interface: Trading interface for user actions
    """
    try:
        print_header("Portfolio Management Workflow", "📊")
        
        # Validate data integrity if requested
        if args.validate_only:
            print_info("Running data integrity validation...")
            validation_errors = repository.validate_data_integrity()
            
            if validation_errors:
                print_error(f"Data validation failed with {len(validation_errors)} errors:")
                for error in validation_errors:
                    print_error(f"  • {error}")
                sys.exit(1)
            else:
                print_success("Data validation passed - no issues found")
                return
        
        # Create backup if requested
        if args.backup or settings.get('backup.auto_backup_on_save', True):
            print_info("Creating data backup...")
            backup_path = backup_manager.create_backup()
            print_success(f"Backup created: {backup_path}")
        
        # Check terminal display capabilities
        check_table_display_issues()
        
        # Load portfolio data
        print_info("Loading portfolio data...")
        portfolio_snapshots = portfolio_manager.load_portfolio()
        
        if not portfolio_snapshots:
            print_warning("No portfolio data found")
            return
        
        latest_snapshot = portfolio_snapshots[-1]
        print_success(f"Loaded portfolio with {len(latest_snapshot.positions)} positions")
        
        # Update exchange rates CSV with current rates
        print_info("Updating exchange rates...")
        currency_handler.update_exchange_rates_csv()
        
        # Fetch current market data
        print_info("Fetching current market data...")
        tickers = [pos.ticker for pos in latest_snapshot.positions]
        
        if tickers:
            # Get trading day window
            start_date, end_date = market_hours.trading_day_window()
            
            # Fetch market data for each ticker
            market_data = {}
            for ticker in tickers:
                try:
                    result = market_data_fetcher.fetch_price_data(ticker, start_date, end_date)
                    if not result.df.empty:
                        market_data[ticker] = result.df
                        # Update price cache
                        price_cache.cache_price_data(ticker, result.df, result.source)
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {ticker}: {e}")
                    market_data[ticker] = pd.DataFrame()
            
            print_success(f"Updated market data for {len(market_data)} tickers")
        
        # Calculate portfolio metrics
        print_info("Calculating portfolio metrics...")
        
        # Update positions with current prices
        updated_positions = []
        for position in latest_snapshot.positions:
            cached_data = price_cache.get_cached_price(position.ticker)
            if cached_data is not None and not cached_data.empty:
                # Get the latest close price from the cached data and convert to Decimal
                from decimal import Decimal
                current_price = Decimal(str(cached_data['Close'].iloc[-1]))
                updated_position = position_calculator.update_position_with_price(
                    position, current_price
                )
                updated_positions.append(updated_position)
            else:
                updated_positions.append(position)
        
        # Calculate P&L metrics
        pnl_metrics = pnl_calculator.calculate_portfolio_pnl(updated_positions)
        
        # Calculate additional display metrics
        enhanced_positions = []
        from decimal import Decimal
        total_portfolio_value = sum(((pos.market_value or Decimal('0')) for pos in updated_positions), Decimal('0'))
        
        for position in updated_positions:
            pos_dict = position.to_dict()
            
            # Calculate position weight
            if total_portfolio_value > 0 and position.market_value:
                weight_percentage = (position.market_value / total_portfolio_value) * 100
                pos_dict['position_weight'] = f"{weight_percentage:.1f}%"
            else:
                pos_dict['position_weight'] = "N/A"
            
            # Get open date from trade log
            try:
                trades = repository.get_trade_history(position.ticker)
                if trades:
                    # Find first BUY trade for this ticker
                    buy_trades = [t for t in trades if t.action.upper() == 'BUY']
                    if buy_trades:
                        first_buy = min(buy_trades, key=lambda t: t.timestamp)
                        pos_dict['opened_date'] = first_buy.timestamp.strftime('%m-%d-%y')
                        logger.debug(f"Found open date for {position.ticker}: {pos_dict['opened_date']}")
                    else:
                        pos_dict['opened_date'] = "N/A"
                        logger.debug(f"No BUY trades found for {position.ticker}")
                else:
                    pos_dict['opened_date'] = "N/A"
                    logger.debug(f"No trades found for {position.ticker}")
            except Exception as e:
                logger.warning(f"Could not get open date for {position.ticker}: {e}")
                pos_dict['opened_date'] = "N/A"
            
            # Calculate daily P&L using historical portfolio data
            # SHARED LOGIC: Same function used by prompt_generator.py when user hits 'd' in menu
            from financial.pnl_calculator import calculate_daily_pnl_from_snapshots
            pos_dict['daily_pnl'] = calculate_daily_pnl_from_snapshots(position, portfolio_snapshots)
            
            # 5-day P&L would require more historical data
            pos_dict['five_day_pnl'] = "N/A"
            
            enhanced_positions.append(pos_dict)
        
        # Sort positions by weight percentage (highest first)
        def get_weight_value(pos_dict):
            """Extract numeric weight value for sorting."""
            weight_str = pos_dict.get('position_weight', '0.0%')
            if weight_str == 'N/A':
                return -1  # Put N/A values at the end
            try:
                return float(weight_str.replace('%', ''))
            except (ValueError, AttributeError):
                return -1
        
        enhanced_positions.sort(key=get_weight_value, reverse=True)
        
        # Clear screen before displaying portfolio
        import os
        import json
        import pandas as pd
        from pathlib import Path
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Get market time info and environment for header
        market_time_info = ""
        try:
            market_time_info = market_hours.display_market_time_header()
        except Exception as e:
            logger.debug(f"Could not get market time header: {e}")
            # Fallback to simple time display
            try:
                tz = market_hours.get_trading_timezone()
                now = datetime.now(tz)
                market_time_info = f"{now.strftime('%Y-%m-%d %H:%M:%S')} PDT | 🔴 MARKET CLOSED"
            except Exception:
                market_time_info = ""
        
        # Determine environment based on data directory
        env_indicator = ""
        try:
            data_path = str(repository.data_dir).lower()
            if 'dev' in data_path or 'test' in data_path:
                env_indicator = "🟡 DEV"
            elif 'prod' in data_path or 'production' in data_path:
                env_indicator = "🟢 PROD"
            else:
                # Check if it's a common dev pattern like ending in _dev, -dev, etc.
                from pathlib import Path
                data_dir_name = Path(data_path).name
                if any(pattern in data_dir_name for pattern in ['dev', 'test', 'debug']):
                    env_indicator = "🟡 DEV"
                else:
                    env_indicator = "🟢 PROD"  # Default to PROD if unclear
        except Exception:
            env_indicator = ""
        
        # Display portfolio table with market time and environment in header
        time_part = f"⏰ {market_time_info}" if market_time_info else ""
        env_part = f"{env_indicator}" if env_indicator else ""
        
        if time_part and env_part:
            header_title = f"Portfolio Summary | {time_part} | {env_part}"
        elif time_part:
            header_title = f"Portfolio Summary | {time_part}"
        elif env_part:
            header_title = f"Portfolio Summary | {env_part}"
        else:
            header_title = "Portfolio Summary"
            
        print_header(header_title, "📊")
        table_formatter.create_portfolio_table(enhanced_positions)
        
        # Display additional tables
        print()  # Add spacing
        
        # Load fund contributions data first
        fund_contributions = []
        try:
            fund_file = Path(repository.data_dir) / "fund_contributions.csv"
            if fund_file.exists():
                df = pd.read_csv(fund_file)
                fund_contributions = df.to_dict('records')
        except Exception as e:
            logger.debug(f"Could not load fund contributions: {e}")
        
        # Calculate and display portfolio statistics
        try:
            portfolio_metrics = position_calculator.calculate_portfolio_metrics(latest_snapshot)
            
            # Calculate total contributions from fund data
            total_contributions = 0
            if fund_contributions:
                from decimal import Decimal
                for contribution in fund_contributions:
                    raw_amount = contribution.get('Amount', contribution.get('amount', 0))
                    try:
                        amount = Decimal(str(raw_amount))
                    except Exception:
                        amount = Decimal('0')
                    contrib_type = contribution.get('Type', contribution.get('type', 'CONTRIBUTION'))
                    ctype = str(contrib_type).upper()
                    if ctype in ('CONTRIBUTION', 'ADJUSTMENT'):
                        total_contributions += amount
                    elif ctype in ('WITHDRAWAL', 'FEE', 'FX_FEE', 'MAINTENANCE_FEE', 'BANK_FEE'):
                        total_contributions -= amount
            
            # Get realized P&L from FIFO processor
            realized_summary = trade_processor.get_realized_pnl_summary()
            from decimal import Decimal
            total_realized_pnl = realized_summary.get('total_realized_pnl', Decimal('0'))
            
            stats_data = {
                'total_contributions': total_contributions,
                'total_cost_basis': portfolio_metrics.get('total_cost_basis', Decimal('0')),
                'total_current_value': total_portfolio_value,
                'total_pnl': pnl_metrics.get('total_absolute_pnl', Decimal('0')),
                'total_realized_pnl': total_realized_pnl,
                'total_portfolio_pnl': pnl_metrics.get('total_absolute_pnl', Decimal('0')) + total_realized_pnl
            }
            
            # Load cash balances and compute CAD-equivalent summary
            from financial.currency_handler import CurrencyHandler
            from decimal import Decimal
            cash_balance = Decimal('0')
            cad_cash = Decimal('0')
            usd_cash = Decimal('0')
            usd_to_cad_rate = Decimal('0')
            estimated_fx_fee_total_usd = Decimal('0')
            estimated_fx_fee_total_cad = Decimal('0')
            try:
                handler = CurrencyHandler(Path(repository.data_dir))
                balances = handler.load_cash_balances()
                # Raw balances as Decimal
                cad_cash = balances.cad
                usd_cash = balances.usd
                # Rate and CAD equivalent
                usd_to_cad_rate = handler.get_exchange_rate('USD','CAD')
                total_cash_cad_equiv_dec = balances.total_cad_equivalent(usd_to_cad_rate)
                cash_balance = total_cash_cad_equiv_dec
                # Compute per-currency holdings
                usd_positions_value_usd = Decimal('0')
                cad_positions_value_cad = Decimal('0')
                try:
                    for pos in updated_positions:
                        try:
                            if pos.market_value is None:
                                continue
                            ticker_currency = handler.get_ticker_currency(pos.ticker)
                            if ticker_currency == 'USD':
                                usd_positions_value_usd += (pos.market_value or Decimal('0'))
                            elif ticker_currency == 'CAD':
                                cad_positions_value_cad += (pos.market_value or Decimal('0'))
                        except Exception:
                            continue
                except Exception:
                    usd_positions_value_usd = Decimal('0')
                    cad_positions_value_cad = Decimal('0')
                total_usd_holdings = usd_cash + usd_positions_value_usd
                total_cad_holdings = cad_cash + cad_positions_value_cad
                # Estimated simple FX fee at 1.5% on USD holdings
                if total_usd_holdings > 0:
                    estimated_fx_fee_total_usd = (total_usd_holdings * Decimal('0.015')).quantize(Decimal('0.01'))
                    estimated_fx_fee_total_cad = (estimated_fx_fee_total_usd * usd_to_cad_rate).quantize(Decimal('0.01'))
            except Exception as e:
                logger.debug(f"Could not load or compute cash balances: {e}")
                total_cash_cad_equiv_dec = Decimal('0')
                usd_to_cad_rate = Decimal('0')
                estimated_fx_fee_total_usd = Decimal('0')
                estimated_fx_fee_total_cad = Decimal('0')
            
            # Prepare summary data (all Decimal)
            summary_data = {
                'portfolio_value': total_portfolio_value,
                'total_pnl': pnl_metrics.get('total_absolute_pnl', Decimal('0')),
                'cash_balance': cash_balance,
                'cad_cash': cad_cash,
                'usd_cash': usd_cash,
'usd_to_cad_rate': usd_to_cad_rate,
                'estimated_fx_fee_total_usd': estimated_fx_fee_total_usd,
                'estimated_fx_fee_total_cad': estimated_fx_fee_total_cad,
                'usd_positions_value_usd': usd_positions_value_usd,
                'cad_positions_value_cad': cad_positions_value_cad,
                'usd_holdings_total_usd': total_usd_holdings,
                'cad_holdings_total_cad': total_cad_holdings,
                'total_equity_cad': total_portfolio_value + cash_balance,
                'fund_contributions': stats_data.get('total_contributions', Decimal('0'))
            }

            # Enrich stats with audit metrics (Decimal)
            try:
                equity = summary_data.get('portfolio_value', Decimal('0')) + summary_data.get('cash_balance', Decimal('0'))
                stats_data['unallocated_vs_cost'] = stats_data.get('total_contributions', Decimal('0')) - stats_data.get('total_cost_basis', Decimal('0')) - summary_data.get('cash_balance', Decimal('0'))
                stats_data['net_pnl_vs_contrib'] = equity - stats_data.get('total_contributions', Decimal('0'))
            except Exception as audit_e:
                logger.debug(f"Could not compute audit metrics: {audit_e}")
            
            # Calculate ownership information to display alongside financial overview
            ownership_data = {}
            try:
                if fund_contributions:
                    # Toggle whether cash is included in ownership allocations via env var
                    include_cash_in_ownership = True
                    try:
                        include_env = os.environ.get('OWNERSHIP_INCLUDE_CASH', '1').strip().lower()
                        include_cash_in_ownership = include_env not in ('0', 'false', 'no')
                    except Exception:
                        include_cash_in_ownership = True

                    base_value_dec = Decimal(str(total_portfolio_value))
                    fund_total_value_dec = base_value_dec + total_cash_cad_equiv_dec if include_cash_in_ownership else base_value_dec

                    ownership_raw = position_calculator.calculate_ownership_percentages(
                        fund_contributions, fund_total_value_dec
                    )
                    
                    # Calculate total shares in portfolio for proportional ownership
                    from decimal import Decimal
                    try:
                        total_shares = sum((pos.shares for pos in updated_positions), start=Decimal('0')) if updated_positions else Decimal('0')
                        logger.debug(f"Calculated total shares: {total_shares}")
                    except Exception as calc_error:
                        logger.warning(f"Could not calculate total shares: {calc_error}")
                        total_shares = Decimal('0')

                    for contributor, data in ownership_raw.items():
                        ownership_pct = data.get('ownership_percentage', Decimal('0'))
                        # Calculate proportional shares owned by this contributor
                        # Since this is a pooled fund, shares are owned collectively, but we show
                        # proportional ownership based on each contributor's percentage of the fund
                        contributor_shares = (ownership_pct / Decimal('100')) * total_shares if total_shares > 0 else Decimal('0')

                        ownership_data[contributor] = {
                            'shares': contributor_shares,  # Proportional share ownership
                            'contributed': data.get('net_contribution', Decimal('0')),
'ownership_pct': ownership_pct,
                            'current_value': data.get('current_value', Decimal('0'))
                        }

                        logger.debug(f"Contributor {contributor}: {contributor_shares:.4f} shares ({ownership_pct:.1f}% ownership)")
            except Exception as e:
                logger.error(f"Could not calculate ownership data: {e}")
            
            # Display financial overview and ownership tables side by side
            if ownership_data:
                table_formatter.create_financial_and_ownership_tables(stats_data, summary_data, ownership_data)
            else:
                # Fallback to just financial table if no ownership data
                table_formatter.create_unified_financial_table(stats_data, summary_data)
            
            print()  # Add spacing
        except Exception as e:
            logger.debug(f"Could not calculate portfolio statistics or financial summary: {e}")
            print_warning(f"Could not display portfolio metrics: {e}")
        
        # Display trading menu
        print()  # Add spacing
        # Add environment indicator to Trading Actions header too
        if env_indicator:
            trading_header_title = f"Trading Actions | {env_indicator}"
        else:
            trading_header_title = "Trading Actions"
        print_header(trading_header_title, "💰")
        # Use fancy Unicode borders if supported, otherwise ASCII fallback
        from display.console_output import _can_handle_unicode, _safe_emoji
        from colorama import Fore, Style
        
        # Use safe emoji function for consistent Unicode handling
        from display.console_output import _safe_emoji

        if _can_handle_unicode():
            # Define box width and create properly aligned menu
            box_width = 67
            border_line = "┌" + "─" * (box_width - 2) + "┐"
            end_line = "└" + "─" * (box_width - 2) + "┘"
            
            def create_menu_line(content):
                """Create a menu line with proper spacing accounting for emoji width."""
                # Calculate actual visual width - emojis appear to take 1 extra space
                visual_len = len(content)
                emoji_count = 0
                for char in content:
                    if ord(char) > 127:  # Likely emoji or Unicode
                        emoji_count += 1
                        visual_len += 1  # Each emoji takes 1 extra visual space
                
                # Calculate padding to align right border
                content_space = 1  # Leading space after │
                border_space = 1   # Trailing space before │
                padding_needed = box_width - content_space - visual_len - border_space - 1  # -1 for trailing │
                
                return f"{Fore.GREEN}{Style.BRIGHT}│{Style.RESET_ALL} {content}{' ' * max(0, padding_needed)}{Fore.GREEN}{Style.BRIGHT}│{Style.RESET_ALL}"
            
            # Print lime-colored box
            print(f"{Fore.GREEN}{Style.BRIGHT}{border_line}{Style.RESET_ALL}")
            # Create aligned menu with consistent spacing
            print(create_menu_line(f"{_safe_emoji('🛒')} 'b'       Buy (Limit Order or Market Open Order)"))
            print(create_menu_line(f"{_safe_emoji('📤')} 's'       Sell (Limit Order)"))
            print(create_menu_line(f"{_safe_emoji('💵')} 'c'       Log Contribution"))
            print(create_menu_line(f"{_safe_emoji('💸')} 'w'       Log Withdrawal"))
            print(create_menu_line(f"{_safe_emoji('👥')} 'm'       Manage Contributors"))
            print(create_menu_line(f"{_safe_emoji('🔄')} 'u'       Update Cash Balances"))
            print(create_menu_line(f"{_safe_emoji('🔗')} 'sync'    Sync Fund Contributions"))
            print(create_menu_line(f"{_safe_emoji('💾')} 'backup'  Create Backup"))
            print(create_menu_line(f"{_safe_emoji('💾')} 'restore' Restore from Backup"))
            print(create_menu_line(f"{_safe_emoji('🔄')} 'r'       Refresh Portfolio"))
            print(create_menu_line(f"{_safe_emoji('🚀')} Enter     Continue to Portfolio Processing"))
            print(create_menu_line(f"{_safe_emoji('❌')} 'q'       Quit"))
            print(f"{Fore.GREEN}{Style.BRIGHT}{end_line}{Style.RESET_ALL}")
        else:
            print("+---------------------------------------------------------------+")
            print("| 'b' [B] Buy (Limit Order or Market Open Order)              |")
            print("| 's' [S] Sell (Limit Order)                                  |")
            print("| 'c' $ Log Contribution                                      |")
            print("| 'w' -$ Log Withdrawal                                       |")
            print("| 'm' [M] Manage Contributors                                 |")
            print("| 'u' ~ Update Cash Balances                                  |")
            print("| 'sync' & Sync Fund Contributions                            |")
            print("| 'backup' [B] Create Backup                                  |")
            print("| 'restore' ~ Restore from Backup                             |")
            print("| 'r' ~ Refresh Portfolio                                     |")
            print("| Enter -> Continue to Portfolio Processing                   |")
            print("| 'q' X Quit                                                  |")
            print("+---------------------------------------------------------------+")
        print()
        
        # Get user input for trading action
        try:
            action = input("Select an action: ").strip().lower()
            
            if action == 'q':
                print_info("Exiting trading system...")
                return
            elif action == '' or action == 'enter':
                print_info("Continuing to portfolio processing...")
                return
            elif action == 'r':
                verify_script_before_action()
                print_info("Refreshing portfolio...")
                # Recursive call to refresh (could be improved with a loop)
                run_portfolio_workflow(args, settings, repository, trading_interface)
                return
            elif action == 'backup':
                print_info("Creating backup...")
                backup_name = backup_manager.create_backup()
                print_success(f"Backup created: {backup_name}")
            elif action == 'c':
                verify_script_before_action()
                trading_interface.log_contribution()
            elif action == 'w':
                verify_script_before_action()
                trading_interface.log_withdrawal()
            elif action == 'm':
                verify_script_before_action()
                trading_interface.manage_contributors()
            elif action == 'u':
                verify_script_before_action()
                trading_interface.update_cash_balances()
            elif action == 'b':
                verify_script_before_action()
                trading_interface.buy_stock()
            elif action == 's':
                verify_script_before_action()
                trading_interface.sell_stock()
            elif action == 'sync':
                verify_script_before_action()
                trading_interface.sync_fund_contributions()
            elif action == 'restore':
                print_warning("Restore functionality not yet implemented")
                print_info("This feature will be added in future updates")
            else:
                print_warning("Invalid action selected")
                
        except KeyboardInterrupt:
            print_info("\nExiting trading system...")
            return
        except Exception as e:
            logger.debug(f"Error in trading menu: {e}")
            print_warning("Error in trading menu")
        
        # Save updated portfolio snapshot (following daily update rules)
        try:
            # Create updated snapshot with current prices
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=datetime.now(),
                total_value=sum(((pos.market_value or Decimal('0')) for pos in updated_positions), Decimal('0'))
            )
            
            # Check if we should update prices (market hours or no update today)
            should_update_prices = False
            
            # Check if market is open
            if market_hours.is_market_open():
                should_update_prices = True
                logger.info("Market is open - updating portfolio prices")
            else:
                # Check if portfolio was updated today
                latest_snapshot = portfolio_manager.get_latest_portfolio()
                if latest_snapshot:
                    latest_date = latest_snapshot.timestamp.date()
                    today = datetime.now().date()
                    if latest_date < today:
                        should_update_prices = True
                        logger.info("Portfolio not updated today - updating prices outside market hours")
                    else:
                        logger.info("Portfolio already updated today and market is closed - skipping price update")
                else:
                    should_update_prices = True
                    logger.info("No existing portfolio data - creating initial snapshot")
            
            if should_update_prices:
                # Use the new daily update method
                repository.update_daily_portfolio_snapshot(updated_snapshot)
                print_success("Portfolio snapshot updated successfully")
            else:
                print_info("Portfolio prices not updated (market closed and already updated today)")
                
        except Exception as e:
            logger.warning(f"Could not save portfolio snapshot: {e}")
            print_warning(f"Could not save portfolio snapshot: {e}")
        
        print_success("Portfolio workflow completed successfully")
        
    except Exception as e:
        error_msg = f"Portfolio workflow failed: {e}"
        print_error(error_msg)
        logger.error(error_msg, exc_info=True)
        raise


def main() -> None:
    """Main entry point for the trading system.
    
    This function orchestrates the entire trading system workflow:
    1. Parse command-line arguments
    2. Initialize system components with dependency injection
    3. Run the portfolio management workflow
    4. Handle errors gracefully with proper cleanup
    """
    try:
        # Initialize launch time for integrity checking
        initialize_launch_time()
        
        # Parse command-line arguments
        args = parse_command_line_arguments()
        
        # Initialize system
        system_settings, system_repository, dependencies = initialize_system(args)
        
        # Store global references for cleanup
        global settings, repository
        settings = system_settings
        repository = system_repository
        
        # Run main workflow
        run_portfolio_workflow(args, system_settings, system_repository, trading_interface)
        
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user")
        sys.exit(0)
        
    except InitializationError as e:
        print_error(f"System initialization failed: {e}")
        sys.exit(1)
        
    except RepositoryError as e:
        print_error(f"Data access error: {e}")
        sys.exit(1)
        
    except TradingSystemError as e:
        print_error(f"Trading system error: {e}")
        sys.exit(1)
        
    except ScriptIntegrityError as e:
        print_error(f"Script integrity error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.error("Unexpected error in main", exc_info=True)
        sys.exit(1)
        
    finally:
        # Cleanup resources
        cleanup_system()


def cleanup_system() -> None:
    """Cleanup system resources and connections."""
    try:
        if repository:
            # Close any open connections or resources
            if hasattr(repository, 'close'):
                repository.close()
        
        logger.info("System cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")





if __name__ == "__main__":
    # Setup error handlers before anything else
    setup_error_handlers()
    
    # Validate system requirements
    validate_system_requirements()
    
    # Log system information
    log_system_info(VERSION)
    
    # Run main function
    main()