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
from datetime import datetime
from pathlib import Path
from typing import Optional

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
from display.console_output import print_success, print_error, print_warning, print_info, print_header
from display.table_formatter import TableFormatter
from display.terminal_utils import detect_terminal_width, check_table_display_issues

from utils.timezone_utils import get_trading_timezone, format_timestamp_for_csv
from utils.validation import validate_portfolio_data, validate_trade_data
from utils.backup_manager import BackupManager
from utils.system_utils import setup_error_handlers, validate_system_requirements, log_system_info, InitializationError

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
  python trading_script.py --data-dir "test_data"   # Use test data directory
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
        total_portfolio_value = sum(pos.market_value or 0 for pos in updated_positions)
        
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
            try:
                daily_pnl_calculated = False
                # Try to find daily P&L from multiple previous snapshots
                for i in range(1, min(len(portfolio_snapshots), 4)):  # Check up to 3 previous snapshots
                    if len(portfolio_snapshots) > i:
                        previous_snapshot = portfolio_snapshots[-(i+1)]
                        # Find the same ticker in previous snapshot
                        prev_position = None
                        for prev_pos in previous_snapshot.positions:
                            if prev_pos.ticker == position.ticker:
                                prev_position = prev_pos
                                break
                        
                        if prev_position and prev_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
                            daily_pnl_change = position.unrealized_pnl - prev_position.unrealized_pnl
                            pos_dict['daily_pnl'] = f"${daily_pnl_change:.2f}"
                            daily_pnl_calculated = True
                            break
                
                if not daily_pnl_calculated:
                    # If no historical data, show current P&L as daily change for new positions
                    if position.unrealized_pnl is not None and abs(position.unrealized_pnl) > 0.01:
                        pos_dict['daily_pnl'] = f"${position.unrealized_pnl:.2f}*"  # * indicates new position
                    else:
                        pos_dict['daily_pnl'] = "$0.00"
            except Exception as e:
                logger.debug(f"Could not calculate daily P&L for {position.ticker}: {e}")
                pos_dict['daily_pnl'] = "$0.00"
            
            # 5-day P&L would require more historical data
            pos_dict['five_day_pnl'] = "N/A"
            
            enhanced_positions.append(pos_dict)
        
        # Clear screen before displaying portfolio
        import os
        import json
        import pandas as pd
        from pathlib import Path
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Display portfolio table
        print_header("Portfolio Summary", "📊")
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
                for contribution in fund_contributions:
                    amount = float(contribution.get('Amount', contribution.get('amount', 0)))
                    contrib_type = contribution.get('Type', contribution.get('type', 'CONTRIBUTION'))
                    if contrib_type.upper() == 'CONTRIBUTION':
                        total_contributions += amount
                    elif contrib_type.upper() == 'WITHDRAWAL':
                        total_contributions -= amount
            
            # Get realized P&L from FIFO processor
            realized_summary = trade_processor.get_realized_pnl_summary()
            total_realized_pnl = float(realized_summary.get('total_realized_pnl', 0))
            
            stats_data = {
                'total_contributions': total_contributions,
                'total_cost_basis': float(portfolio_metrics.get('total_cost_basis', 0)),
                'total_current_value': float(total_portfolio_value),
                'total_pnl': float(pnl_metrics.get('total_absolute_pnl', 0)),
                'total_realized_pnl': total_realized_pnl,
                'total_portfolio_pnl': float(pnl_metrics.get('total_absolute_pnl', 0)) + total_realized_pnl
            }
            table_formatter.create_statistics_table(stats_data)
            print()  # Add spacing
        except Exception as e:
            logger.debug(f"Could not calculate portfolio statistics: {e}")
            print_warning(f"Could not display portfolio statistics: {e}")
        
        # Calculate and display ownership information
        try:
            
            if fund_contributions:
                ownership_raw = position_calculator.calculate_ownership_percentages(
                    fund_contributions, Decimal(str(total_portfolio_value))
                )
                # Map field names for table formatter
                ownership_data = {}

                # Calculate total shares in portfolio for proportional ownership
                try:
                    total_shares = sum(float(pos.shares) for pos in updated_positions) if updated_positions else 0
                    logger.debug(f"Calculated total shares: {total_shares}")
                except Exception as calc_error:
                    logger.warning(f"Could not calculate total shares: {calc_error}")
                    total_shares = 0

                for contributor, data in ownership_raw.items():
                    ownership_pct = float(data.get('ownership_percentage', 0))
                    # Calculate proportional shares owned by this contributor
                    # Since this is a pooled fund, shares are owned collectively, but we show
                    # proportional ownership based on each contributor's percentage of the fund
                    contributor_shares = (ownership_pct / 100) * total_shares if total_shares > 0 else 0

                    ownership_data[contributor] = {
                        'shares': contributor_shares,  # Proportional share ownership
                        'contributed': float(data.get('net_contribution', 0)),
                        'ownership_pct': ownership_pct,
                        'current_value': float(data.get('current_value', 0))
                    }

                    logger.debug(f"Contributor {contributor}: {contributor_shares:.4f} shares ({ownership_pct:.1f}% ownership)")

                # Create the ownership table
                logger.debug(f"Creating ownership table with {len(ownership_data)} contributors")
                table_formatter.create_ownership_table(ownership_data)
                print()  # Add spacing
        except Exception as e:
            logger.error(f"Could not calculate ownership data: {e}")
            # Try to show a basic ownership table as fallback
            try:
                if fund_contributions and ownership_raw:
                    logger.debug("Attempting fallback ownership table...")
                    fallback_ownership_data = {}
                    for contributor, data in ownership_raw.items():
                        fallback_ownership_data[contributor] = {
                            'shares': 0.0,  # Fallback to 0 shares
                            'contributed': float(data.get('net_contribution', 0)),
                            'ownership_pct': float(data.get('ownership_percentage', 0)),
                            'current_value': float(data.get('current_value', 0))
                        }
                    table_formatter.create_ownership_table(fallback_ownership_data)
                    print()  # Add spacing
                    logger.info("Displayed fallback ownership table")
            except Exception as fallback_e:
                logger.error(f"Fallback ownership table also failed: {fallback_e}")
                print_warning("Could not display ownership information")
        
        # Display financial summary
        try:
            # Load cash balance
            cash_balance = 0
            try:
                cash_file = Path(repository.data_dir) / "cash_balances.json"
                if cash_file.exists():
                    with open(cash_file, 'r') as f:
                        cash_data = json.load(f)
                        cash_balance = cash_data.get('cad', 0) + cash_data.get('usd', 0)
            except Exception as e:
                logger.debug(f"Could not load cash balance: {e}")
            
            summary_data = {
                'portfolio_value': float(total_portfolio_value),
                'total_pnl': float(pnl_metrics.get('total_absolute_pnl', 0)),
                'cash_balance': float(cash_balance),
                'fund_contributions': float(stats_data.get('total_contributions', 0))
            }
            table_formatter.create_summary_table(summary_data)
        except Exception as e:
            logger.debug(f"Could not create financial summary: {e}")
        
        # Display market timing information
        try:
            market_time_header = market_hours.display_market_time_header()
            print_info(market_time_header, emoji="⏰")
        except Exception as e:
            logger.debug(f"Could not display market time header: {e}")
            # Fallback to simple market time display
            tz = market_hours.get_trading_timezone()
            now = datetime.now(tz)
            simple_time = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"Current time: {simple_time}")
        
        # Display trading menu
        print()  # Add spacing
        print_header("Trading Actions", "💰")
        # Use fancy Unicode borders if supported, otherwise ASCII fallback
        from display.console_output import _can_handle_unicode, _safe_emoji
        
        # Use safe emoji function for consistent Unicode handling
        from display.console_output import _safe_emoji

        if _can_handle_unicode():
            print("┌─────────────────────────────────────────────────────────────────┐")
            print(f"│ 'b' {_safe_emoji('🛒')} Buy (Limit Order or Market Open Order)                  │")
            print(f"│ 's' {_safe_emoji('📤')} Sell (Limit Order)                                      │")
            print(f"│ 'c' {_safe_emoji('💵')} Log Contribution                                        │")
            print(f"│ 'w' {_safe_emoji('💸')} Log Withdrawal                                          │")
            print(f"│ 'u' {_safe_emoji('🔄')} Update Cash Balances                                    │")
            print(f"│ 'sync' {_safe_emoji('🔗')} Sync Fund Contributions                              │")
            print(f"│ 'backup' {_safe_emoji('💾')} Create Backup                                      │")
            print(f"│ 'restore' {_safe_emoji('🔄')} Restore from Backup                               │")
            print(f"│ 'r' {_safe_emoji('🔄')} Refresh Portfolio                                       │")
            print(f"│ Enter {_safe_emoji('➤')}  Continue to Portfolio Processing                       │")
            print(f"│ 'q' {_safe_emoji('❌')} Quit                                                     │")
            print("└─────────────────────────────────────────────────────────────────┘")
        else:
            print("+---------------------------------------------------------------+")
            print("| 'b' [B] Buy (Limit Order or Market Open Order)              |")
            print("| 's' [S] Sell (Limit Order)                                  |")
            print("| 'c' $ Log Contribution                                      |")
            print("| 'w' -$ Log Withdrawal                                       |")
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
                print_info("Refreshing portfolio...")
                # Recursive call to refresh (could be improved with a loop)
                run_portfolio_workflow(args, settings, repository, trading_interface)
                return
            elif action == 'backup':
                print_info("Creating backup...")
                backup_name = backup_manager.create_backup()
                print_success(f"Backup created: {backup_name}")
            elif action == 'c':
                trading_interface.log_contribution()
            elif action == 'w':
                trading_interface.log_withdrawal()
            elif action == 'u':
                trading_interface.update_cash_balances()
            elif action == 'b':
                trading_interface.buy_stock()
            elif action == 's':
                trading_interface.sell_stock()
            elif action == 'sync':
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
                total_value=sum(pos.market_value or 0 for pos in updated_positions)
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