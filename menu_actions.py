"""Menu Actions Module.

This module provides a unified interface for all menu actions with shared
initialization logic. This eliminates code duplication and provides a clean
separation between UI and business logic.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any

# Modular startup check - handles path setup and dependency checking
try:
    from utils.script_startup import startup_check
    startup_check("menu_actions.py")
except ImportError:
    # Fallback for minimal dependency checking if script_startup isn't available
    try:
        import pandas
    except ImportError:
        print("\n❌ Missing Dependencies (menu_actions.py)")
        print("Required packages not found. Please activate virtual environment:")
        import os
        if os.name == 'nt':  # Windows
            print("  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print("  source venv/bin/activate")
        print("  python menu_actions.py")
        print("\n💡 TIP: Use 'python run.py' to avoid dependency issues")
        sys.exit(1)

# Core system imports
from config.settings import Settings, configure_system

# Repository and data access
from data.repositories.repository_factory import get_repository_container, configure_repositories
from data.repositories.base_repository import BaseRepository

# Business logic modules
from portfolio.fifo_trade_processor import FIFOTradeProcessor
from portfolio.trading_interface import TradingInterface
from portfolio.contributor_manager import ContributorManager, ContributorUI

# Display utilities
from display.console_output import print_success, print_error, print_warning, print_info, print_header

# Global logger
logger = logging.getLogger(__name__)


class MenuActionSystem:
    """System for executing menu actions with shared initialization."""
    
    def __init__(self):
        """Initialize the menu action system."""
        self.settings: Optional[Settings] = None
        self.repository: Optional[BaseRepository] = None
        self.trade_processor: Optional[FIFOTradeProcessor] = None
        self.trading_interface: Optional[TradingInterface] = None
        self.contributor_manager: Optional[ContributorManager] = None
        self.contributor_ui: Optional[ContributorUI] = None
        self._initialized = False
    
    def initialize_system(self, data_dir: Optional[str] = None, debug: bool = False) -> bool:
        """Initialize all system components.
        
        Args:
            data_dir: Optional data directory override
            debug: Enable debug logging
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if self._initialized:
                return True
                
            # Configure system settings
            self.settings = configure_system()
            
            # Override settings if provided
            if data_dir:
                self.settings.set('repository.csv.data_directory', data_dir)
            
            if debug:
                self.settings.set('logging.level', 'DEBUG')
                logging.basicConfig(level=logging.DEBUG)
            else:
                logging.basicConfig(level=logging.INFO)
            
            # Initialize repository with dual-write support
            repo_config = self.settings.get_repository_config()
            repository_type = repo_config.get('type', 'csv')
            
            # Check if we should use dual-write mode based on repository type
            use_dual_write = False
            use_supabase_dual_write = False
            
            if repository_type == 'csv':
                # CSV mode: Check if Supabase is available for dual-write
                try:
                    from data.repositories.supabase_repository import SupabaseRepository
                    # Test if Supabase credentials are available
                    import os
                    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
                        # Get fund name for testing
                        fund_name = repo_config.get('fund', 'Project Chimera')
                        # Test connection
                        test_repo = SupabaseRepository(fund_name)
                        if test_repo.test_connection():
                            use_dual_write = True
                            logger.info("CSV mode with Supabase available - enabling CSV dual-write mode")
                        else:
                            logger.warning("Supabase credentials available but connection failed - using CSV-only mode")
                except Exception as e:
                    logger.debug(f"Supabase not available for dual-write: {e}")
                    
            elif repository_type == 'supabase':
                # Supabase mode: Check if Supabase is available for dual-write
                try:
                    from data.repositories.supabase_repository import SupabaseRepository
                    # Test if Supabase credentials are available
                    import os
                    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
                        # Get fund name for testing
                        fund_name = repo_config.get('fund', 'Project Chimera')
                        # Test connection
                        test_repo = SupabaseRepository(fund_name)
                        if test_repo.test_connection():
                            use_supabase_dual_write = True
                            logger.info("Supabase mode with Supabase available - enabling Supabase dual-write mode")
                        else:
                            logger.warning("Supabase credentials available but connection failed - falling back to CSV-only mode")
                            repository_type = 'csv'  # Fall back to CSV
                except Exception as e:
                    logger.debug(f"Supabase not available - falling back to CSV mode: {e}")
                    repository_type = 'csv'  # Fall back to CSV
            
            if use_dual_write:
                logger.info(f"Initializing CSV dual-write repository (CSV read, CSV+Supabase write) for fund: {repo_config.get('fund', 'N/A')}")
                # Clear any existing repositories to avoid stale cache
                get_repository_container().clear()
                
                # Create CSV dual-write repository
                from data.repositories.repository_factory import RepositoryFactory
                self.repository = RepositoryFactory.create_dual_write_repository(
                    fund_name=repo_config.get('fund', 'Project Chimera'),
                    data_directory=self.settings.get_data_directory()
                )
            elif use_supabase_dual_write:
                logger.info(f"Initializing Supabase dual-write repository (Supabase read, CSV+Supabase write) for fund: {repo_config.get('fund', 'N/A')}")
                # Clear any existing repositories to avoid stale cache
                get_repository_container().clear()
                
                # Create Supabase dual-write repository
                from data.repositories.repository_factory import RepositoryFactory
                self.repository = RepositoryFactory.create_repository(
                    repository_type='supabase-dual-write',
                    fund_name=repo_config.get('fund', 'Project Chimera'),
                    data_directory=self.settings.get_data_directory()
                )
            else:
                configure_repositories({'default': repo_config})
                self.repository = get_repository_container().get_repository('default')
            
            # Initialize business logic components
            self.trade_processor = FIFOTradeProcessor(self.repository)
            self.trading_interface = TradingInterface(self.repository, self.trade_processor)
            self.contributor_manager = ContributorManager(self.repository)
            self.contributor_ui = ContributorUI(self.contributor_manager)
            
            self._initialized = True
            logger.info("Menu action system initialized successfully")
            return True
            
        except Exception as e:
            error_msg = f"System initialization failed: {e}"
            print_error(error_msg)
            logger.error(error_msg, exc_info=True)
            return False
    
    def execute_action(self, action_name: str, **kwargs) -> bool:
        """Execute a menu action.
        
        Args:
            action_name: Name of the action to execute
            **kwargs: Additional arguments for the action
            
        Returns:
            bool: True if action executed successfully
        """
        if not self._initialized:
            print_error("System not initialized")
            return False
        
        action_map = {
            'manage_contributors': self._manage_contributors,
            'get_contributor_emails': self._get_contributor_emails,
            'log_contribution': self._log_contribution,
            'log_withdrawal': self._log_withdrawal,
            'update_cash_balances': self._update_cash_balances,
            'buy_stock': self._buy_stock,
            'sell_stock': self._sell_stock,
            'sync_fund_contributions': self._sync_fund_contributions,
            'view_trade_log': self._view_trade_log,
        }
        
        if action_name not in action_map:
            print_error(f"Unknown action: {action_name}")
            return False
        
        try:
            return action_map[action_name](**kwargs)
        except Exception as e:
            print_error(f"Error executing action '{action_name}': {e}")
            logger.error(f"Error executing action '{action_name}': {e}", exc_info=True)
            return False
    
    def _manage_contributors(self, **kwargs) -> bool:
        """Execute contributor management action."""
        return self.contributor_ui.manage_contributors_interactive()
    
    def _get_contributor_emails(self, **kwargs) -> bool:
        """Execute get contributor emails action."""
        try:
            emails = self.contributor_manager.get_emails_as_string()
            if emails:
                print_info("Contributor Email Addresses (ready to copy):", "📧")
                print()
                print(f"📋 {emails}")
                print()
                print_success("Email addresses displayed above - you can copy and paste them into your mail program")
            else:
                print_warning("No email addresses found or all emails are empty")
            return True
        except Exception as e:
            print_error(f"Failed to get contributor emails: {e}")
            return False
    
    def _log_contribution(self, **kwargs) -> bool:
        """Execute contribution logging action."""
        return self.trading_interface.log_contribution()
    
    def _log_withdrawal(self, **kwargs) -> bool:
        """Execute withdrawal logging action."""
        return self.trading_interface.log_withdrawal()
    
    def _update_cash_balances(self, **kwargs) -> bool:
        """Execute cash balance update action."""
        return self.trading_interface.update_cash_balances()
    
    def _buy_stock(self, **kwargs) -> bool:
        """Execute stock purchase action."""
        return self.trading_interface.buy_stock()
    
    def _sell_stock(self, **kwargs) -> bool:
        """Execute stock sale action."""
        return self.trading_interface.sell_stock()
    
    def _sync_fund_contributions(self, **kwargs) -> bool:
        """Execute fund contribution sync action."""
        return self.trading_interface.sync_fund_contributions()
    
    def _view_trade_log(self, **kwargs) -> bool:
        """Execute view trade log action."""
        try:
            from display.table_formatter import TableFormatter
            
            # Get all trades from repository
            trades = self.repository.get_trade_history()
            
            if not trades:
                print_info("No trades found in trade log")
                return True
            
            # Create and display trade log table
            formatter = TableFormatter()
            formatter.create_trade_log_table(trades, "Complete Trade History")
            
            return True
            
        except Exception as e:
            print_error(f"Error viewing trade log: {e}")
            logger.error(f"Error viewing trade log: {e}", exc_info=True)
            return False


def create_standalone_action_script(action_name: str, title: str, emoji: str = "⚙️") -> Callable:
    """Create a standalone script function for a menu action.
    
    Args:
        action_name: Name of the action to execute
        title: Display title for the action
        emoji: Emoji icon for the action
        
    Returns:
        Function that can be used as a standalone script
    """
    def standalone_script():
        """Standalone script function."""
        # Parse command-line arguments
        parser = argparse.ArgumentParser(
            description=f"{title} - Standalone Script",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            '--data-dir',
            type=str,
            default=None,
            help='Data directory path (uses default from config if not specified)'
        )
        
        parser.add_argument(
            '--action',
            type=str,
            help='Specific action to run'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )
        
        args = parser.parse_args()
        
        # Show header
        print_header(title, emoji)
        
        # Initialize system
        print_info("Initializing system...")
        action_system = MenuActionSystem()
        
        if not action_system.initialize_system(data_dir=args.data_dir, debug=args.debug):
            print_error("Failed to initialize system")
            sys.exit(1)
        
        print_success("System initialized successfully")
        print()  # Add spacing
        
        # Execute the action
        try:
            success = action_system.execute_action(action_name)
            
            if success:
                print()  # Add spacing
                print_success(f"{title} completed successfully")
            else:
                print()  # Add spacing
                print_warning(f"{title} was cancelled or failed")
                
        except KeyboardInterrupt:
            print_warning(f"\n{title} cancelled by user")
            sys.exit(0)
            
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            logger.error(f"Unexpected error in {action_name}", exc_info=True)
            sys.exit(1)
    
    return standalone_script


# Pre-defined standalone script functions
def manage_contributors_main():
    """Standalone script for managing contributors."""
    script_func = create_standalone_action_script(
        action_name="manage_contributors",
        title="Manage Contributors",
        emoji="👥"
    )
    script_func()


def log_contribution_main():
    """Standalone script for logging contributions."""
    script_func = create_standalone_action_script(
        action_name="log_contribution", 
        title="Log Contribution",
        emoji="💵"
    )
    script_func()


def log_withdrawal_main():
    """Standalone script for logging withdrawals."""
    script_func = create_standalone_action_script(
        action_name="log_withdrawal",
        title="Log Withdrawal", 
        emoji="💸"
    )
    script_func()


def get_contributor_emails_main():
    """Standalone script for getting contributor emails."""
    script_func = create_standalone_action_script(
        action_name="get_contributor_emails",
        title="Get Contributor Emails",
        emoji="📧"
    )
    script_func()


def view_trade_log_main():
    """Standalone script for viewing trade log."""
    script_func = create_standalone_action_script(
        action_name="view_trade_log",
        title="View Trade Log",
        emoji="📜"
    )
    script_func()


if __name__ == "__main__":
    # Parse command line arguments for specific actions
    import argparse
    parser = argparse.ArgumentParser(description="Menu Actions")
    parser.add_argument("--action", help="Specific action to run")
    args = parser.parse_args()
    
    if args.action == "view_trade_log":
        view_trade_log_main()
    else:
        # Default to contributor management if run directly
        manage_contributors_main()
