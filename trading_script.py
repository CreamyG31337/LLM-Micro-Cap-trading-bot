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

import pandas as pd

# Core system imports
from config.settings import Settings, get_settings, configure_system
from config.constants import DEFAULT_DATA_DIR, LOG_FILE, VERSION

# Repository and data access
from data.repositories.repository_factory import RepositoryFactory, get_repository_container, configure_repositories
from data.repositories.base_repository import BaseRepository, RepositoryError

# Business logic modules
from portfolio.portfolio_manager import PortfolioManager
from portfolio.trade_processor import TradeProcessor
from portfolio.position_calculator import PositionCalculator

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
    global portfolio_manager, trade_processor, position_calculator
    global market_data_fetcher, market_hours, price_cache
    global currency_handler, pnl_calculator, table_formatter, backup_manager
    
    try:
        logger.info("Initializing system components...")
        
        # Initialize portfolio components
        portfolio_manager = PortfolioManager(repository)
        trade_processor = TradeProcessor(repository)
        position_calculator = PositionCalculator(repository)
        
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


def run_portfolio_workflow(args: argparse.Namespace, settings: Settings, repository: BaseRepository) -> None:
    """Run the main portfolio management workflow.
    
    Args:
        args: Parsed command-line arguments
        settings: System settings
        repository: Initialized repository
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
                        pos_dict['opened_date'] = first_buy.timestamp.strftime('%Y-%m-%d')
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
                # Get historical snapshots to calculate daily change
                if len(portfolio_snapshots) >= 2:
                    # Get previous snapshot (second to last)
                    previous_snapshot = portfolio_snapshots[-2]
                    # Find the same ticker in previous snapshot
                    prev_position = None
                    for prev_pos in previous_snapshot.positions:
                        if prev_pos.ticker == position.ticker:
                            prev_position = prev_pos
                            break
                    
                    if prev_position and prev_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
                        daily_pnl_change = position.unrealized_pnl - prev_position.unrealized_pnl
                        pos_dict['daily_pnl'] = f"${daily_pnl_change:.2f}"
                    else:
                        pos_dict['daily_pnl'] = "N/A"
                else:
                    pos_dict['daily_pnl'] = "N/A"
            except Exception as e:
                logger.debug(f"Could not calculate daily P&L for {position.ticker}: {e}")
                pos_dict['daily_pnl'] = "N/A"
            
            # 5-day P&L would require more historical data
            pos_dict['five_day_pnl'] = "N/A"
            
            enhanced_positions.append(pos_dict)
        
        # Display portfolio table
        print_header("Portfolio Summary", "💼")
        table_formatter.create_portfolio_table(enhanced_positions)
        
        # Display market timing information
        market_time_header = market_hours.display_market_time_header()
        print_info(market_time_header)
        
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
        run_portfolio_workflow(args, system_settings, system_repository)
        
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