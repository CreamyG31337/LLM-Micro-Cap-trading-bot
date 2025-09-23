"""Dynamic Fund Management System.

This module provides functionality for creating, managing, and switching between
multiple independent investment funds (like RRSP, TFSA, etc.) through a user-friendly
interface.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from config.settings import Settings
from display.console_output import print_success, print_error, print_warning, print_info

logger = logging.getLogger(__name__)


class FundManager:
    """Manages multiple investment funds with dynamic creation and switching."""
    
    def __init__(self, base_data_dir: str = "trading_data"):
        """Initialize the fund manager.
        
        Args:
            base_data_dir: Base directory for all trading data
        """
        self.base_data_dir = Path(base_data_dir)
        self.funds_dir = self.base_data_dir / "funds"
        self.shared_dir = self.base_data_dir / "shared"
        self.active_fund_file = self.base_data_dir / "active_fund.json"
        
        # Ensure directories exist
        self.funds_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        
        # Create templates directory
        self.templates_dir = self.shared_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self) -> None:
        """Create default configuration and thesis templates."""
        # Fund config template
        config_template_path = self.templates_dir / "fund_config_template.json"
        if not config_template_path.exists():
            template_config = {
                "fund": {
                    "name": "{fund_name}",
                    "description": "{fund_description}",
                    "display_currency": "CAD",
                    "fund_type": "investment",
                    "created_date": "{created_date}",
                    "tax_status": "taxable"
                },
                "repository": {
                    "type": "csv",
                    "csv": {
                        "data_directory": "trading_data/funds/{fund_directory}"
                    }
                },
                "market_data": {
                    "primary_source": "yahoo",
                    "fallback_source": "stooq",
                    "cache_enabled": True
                },
                "backup": {
                    "enabled": True,
                    "directory": "backups",
                    "max_backups": 10
                }
            }
            
            with open(config_template_path, 'w') as f:
                json.dump(template_config, f, indent=2)
        
        # Thesis template (create in prompts directory)
        prompts_dir = Path("prompts")
        prompts_dir.mkdir(exist_ok=True)
        thesis_template_path = prompts_dir / "thesis_template.yaml"
        if not thesis_template_path.exists():
            template_thesis = """guiding_thesis:
  title: "{fund_name} Investment Thesis"
  overview: "The {fund_name} portfolio is designed to achieve specific investment objectives through a structured approach."
  pillars:
    - name: "Core Holdings"
      allocation: "~70%"
      thesis: "Stable, dividend-paying investments that form the foundation of the portfolio."
    - name: "Growth Opportunities"
      allocation: "~20%"
      thesis: "Higher-growth investments with potential for capital appreciation."
    - name: "Diversification & Risk Management"
      allocation: "~10%"
      thesis: "Defensive positions and alternative investments to reduce overall portfolio risk."
"""
            
            with open(thesis_template_path, 'w') as f:
                f.write(template_thesis)
    
    def get_available_funds(self) -> List[str]:
        """Get list of all available funds.
        
        Returns:
            List of fund names
        """
        if not self.funds_dir.exists():
            return []
        
        funds = []
        for fund_dir in self.funds_dir.iterdir():
            if fund_dir.is_dir() and (fund_dir / "fund_config.json").exists():
                funds.append(fund_dir.name)
        
        return sorted(funds)
    
    def get_active_fund(self) -> Optional[str]:
        """Get the currently active fund.
        
        Returns:
            Name of active fund or None if not set
        """
        if not self.active_fund_file.exists():
            # Try to set a default active fund
            funds = self.get_available_funds()
            if funds:
                # Use first available fund alphabetically
                preferred_fund = funds[0]
                self.set_active_fund(preferred_fund)
                return preferred_fund
            return None
        
        try:
            with open(self.active_fund_file, 'r') as f:
                data = json.load(f)
                active_fund = data.get('active_fund')
                
                # Verify the fund still exists
                if active_fund and active_fund in self.get_available_funds():
                    return active_fund
                else:
                    # Active fund no longer exists, reset
                    funds = self.get_available_funds()
                    if funds:
                        # Use first available fund alphabetically
                        preferred_fund = funds[0]
                        self.set_active_fund(preferred_fund)
                        return preferred_fund
                    return None
                    
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def set_active_fund(self, fund_name: str) -> bool:
        """Set the active fund.
        
        Args:
            fund_name: Name of the fund to set as active
            
        Returns:
            True if successful, False otherwise
        """
        if fund_name not in self.get_available_funds():
            print_error(f"Fund '{fund_name}' does not exist")
            return False
        
        try:
            active_fund_data = {
                "active_fund": fund_name,
                "last_switched": datetime.now().isoformat(),
                "switch_count": self._get_switch_count() + 1
            }
            
            with open(self.active_fund_file, 'w') as f:
                json.dump(active_fund_data, f, indent=2)
            
            # Invalidate global settings cache to force refresh
            self._invalidate_global_settings_cache()
            
            print_success(f"Switched to fund: {fund_name}")
            return True
            
        except Exception as e:
            print_error(f"Failed to set active fund: {e}")
            logger.error(f"Failed to set active fund {fund_name}: {e}")
            return False
    
    def _get_switch_count(self) -> int:
        """Get the current switch count for tracking."""
        if not self.active_fund_file.exists():
            return 0
        
        try:
            with open(self.active_fund_file, 'r') as f:
                data = json.load(f)
                return data.get('switch_count', 0)
        except:
            return 0
    
    def _invalidate_global_settings_cache(self) -> None:
        """Invalidate the global settings cache to force refresh after fund switch."""
        try:
            # Import here to avoid circular imports
            import config.settings
            # Reset the global settings instance to None so it gets recreated
            config.settings._settings = None
        except ImportError:
            # Settings module not available, nothing to invalidate
            pass
        except Exception:
            # Any other error, ignore silently
            pass
        
        # Also invalidate the global fund manager cache to ensure fresh instance
        # This prevents UI from showing stale fund names after switching
        invalidate_fund_manager_cache()
    
    def create_fund(self, fund_name: str, fund_type: str = "investment", 
                   display_currency: str = "CAD", description: str = "", 
                   copy_from_fund: Optional[str] = None) -> bool:
        """Create a new fund with the specified configuration.
        
        Args:
            fund_name: Name of the new fund
            fund_type: Type of fund (investment, RRSP, TFSA, etc.)
            display_currency: Display currency for the fund
            description: Optional description
            copy_from_fund: Optional fund to copy data from
            
        Returns:
            True if successful, False otherwise
        """
        if fund_name in self.get_available_funds():
            print_error(f"Fund '{fund_name}' already exists")
            return False
        
        # Validate fund name (no special characters that would cause filesystem issues)
        if not fund_name.replace(" ", "").replace("-", "").replace("_", "").isalnum():
            print_error("Fund name can only contain letters, numbers, spaces, hyphens, and underscores")
            return False
        
        try:
            # Create fund directory
            fund_dir = self.funds_dir / fund_name
            fund_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backups directory
            (fund_dir / "backups").mkdir(exist_ok=True)
            
            # Create fund configuration
            self._create_fund_config(fund_dir, fund_name, fund_type, display_currency, description)
            
            # Create thesis file
            self._create_fund_thesis(fund_dir, fund_name, fund_type)
            
            # Create empty data files or copy from existing fund
            if copy_from_fund and copy_from_fund in self.get_available_funds():
                self._copy_fund_data(copy_from_fund, fund_name)
            else:
                self._create_empty_data_files(fund_dir)
            
            print_success(f"Created fund '{fund_name}' successfully")
            
            # Set as active fund if it's the first one
            if len(self.get_available_funds()) == 1:
                self.set_active_fund(fund_name)
            
            return True
            
        except Exception as e:
            print_error(f"Failed to create fund '{fund_name}': {e}")
            logger.error(f"Failed to create fund {fund_name}: {e}")
            
            # Cleanup on failure
            fund_dir = self.funds_dir / fund_name
            if fund_dir.exists():
                shutil.rmtree(fund_dir, ignore_errors=True)
            
            return False
    
    def _create_fund_config(self, fund_dir: Path, fund_name: str, fund_type: str, 
                           display_currency: str, description: str) -> None:
        """Create the fund configuration file."""
        # Load template
        template_path = self.templates_dir / "fund_config_template.json"
        with open(template_path, 'r') as f:
            config = json.load(f)
        
        # Customize for this fund
        config["fund"]["name"] = fund_name
        config["fund"]["description"] = description or f"{fund_type.upper()} Investment Portfolio"
        config["fund"]["display_currency"] = display_currency
        config["fund"]["fund_type"] = fund_type
        config["fund"]["created_date"] = datetime.now().isoformat()
        
        # Set tax status based on fund type
        if fund_type.upper() == "TFSA":
            config["fund"]["tax_status"] = "tax_free"
        elif fund_type.upper() == "RRSP":
            config["fund"]["tax_status"] = "tax_deferred"
        else:
            config["fund"]["tax_status"] = "taxable"
        
        # Add Webull-specific configuration
        if fund_type.lower() == "webull":
            config["fund"]["webull_fx_fee"] = {
                "enabled": True,
                "liquidation_fee": 2.99,  # $2.99 per USD holding
                "fx_fee_rate": 0.015,  # 1.5% FX fee
                "description": "Webull liquidation fee ($2.99/holding) + FX fee (1.5%)"
            }
        
        # Add Wealthsimple-specific configuration
        if fund_type.lower() == "wealthsimple":
            config["fund"]["wealthsimple_fees"] = {
                "enabled": True,
                "fx_fee_rate": 0.015,  # 1.5% FX fee on USD holdings (same as Webull)
                "liquidation_fee": 0.0,  # No liquidation fees (unlike Webull's $2.99)
                "description": "Wealthsimple FX fees only (1.5% of USD holdings, no liquidation fees)"
            }
        
        # Update data directory path
        config["repository"]["csv"]["data_directory"] = f"trading_data/funds/{fund_name}"
        
        # Save configuration
        config_path = fund_dir / "fund_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_fund_thesis(self, fund_dir: Path, fund_name: str, fund_type: str = "investment") -> None:
        """Create the investment thesis file for the fund."""
        # Choose appropriate thesis template based on fund type
        thesis_template_name = self._get_thesis_template_name(fund_type)
        template_path = self._get_thesis_template_path(thesis_template_name)
        
        with open(template_path, 'r') as f:
            thesis_content = f.read()
        
        # Customize for this fund
        thesis_content = thesis_content.replace("{fund_name}", fund_name)
        
        # Save thesis
        thesis_path = fund_dir / "thesis.yaml"
        with open(thesis_path, 'w') as f:
            f.write(thesis_content)
    
    def _get_thesis_template_name(self, fund_type: str) -> str:
        """Get the appropriate thesis template name based on fund type."""
        fund_type_lower = fund_type.lower()
        
        if fund_type_lower == "rrsp":
            return "thesis_rrsp.yaml.example"
        elif fund_type_lower == "tfsa":
            return "thesis_tfsa.yaml.example"
        else:
            return "thesis_template.yaml"
    
    def _get_thesis_template_path(self, template_name: str) -> Path:
        """Get the full path to a thesis template, checking multiple locations."""
        # Check in config directory for .example files first
        config_template_path = Path("config") / template_name
        if config_template_path.exists():
            return config_template_path
        
        # Check in prompts directory for templates
        prompts_template_path = Path("prompts") / template_name
        if prompts_template_path.exists():
            return prompts_template_path
        
        # Check in shared templates directory
        template_path = self.templates_dir / template_name
        if template_path.exists():
            return template_path
        
        # Fallback to default template in prompts
        default_template = Path("prompts") / "thesis_template.yaml"
        if default_template.exists():
            return default_template
        
        # If nothing exists, create a basic template
        self._create_default_templates()
        return Path("prompts") / "thesis_template.yaml"
    
    def _create_empty_data_files(self, fund_dir: Path) -> None:
        """Create empty data files for a new fund."""
        # Portfolio CSV
        portfolio_path = fund_dir / "llm_portfolio_update.csv"
        with open(portfolio_path, 'w') as f:
            f.write("Date,Ticker,Shares,Average Price,Cost Basis,Stop Loss,Current Price,Total Value,PnL,Action,Company,Currency\n")
        
        # Trade log CSV
        trade_log_path = fund_dir / "llm_trade_log.csv"
        with open(trade_log_path, 'w') as f:
            f.write("Date,Ticker,Action,Shares,Price,Total,Currency,Notes\n")
        
        # Cash balances JSON
        cash_path = fund_dir / "cash_balances.json"
        with open(cash_path, 'w') as f:
            json.dump({"cad": 0.0, "usd": 0.0}, f, indent=2)
        
        # Fund contributions CSV
        contributions_path = fund_dir / "fund_contributions.csv"
        with open(contributions_path, 'w') as f:
            f.write("Date,Amount,Currency,Type,Notes\n")
        
        # Exchange rates CSV
        exchange_rates_path = fund_dir / "exchange_rates.csv"
        with open(exchange_rates_path, 'w') as f:
            f.write("Date,USD_CAD,Source\n")
    
    def _copy_fund_data(self, source_fund: str, target_fund: str) -> None:
        """Copy data files from source fund to target fund."""
        source_dir = self.funds_dir / source_fund
        target_dir = self.funds_dir / target_fund
        
        # Files to copy
        data_files = [
            "llm_portfolio_update.csv",
            "llm_trade_log.csv", 
            "cash_balances.json",
            "fund_contributions.csv",
            "exchange_rates.csv"
        ]
        
        for file_name in data_files:
            source_file = source_dir / file_name
            target_file = target_dir / file_name
            
            if source_file.exists():
                shutil.copy2(source_file, target_file)
                print_info(f"Copied {file_name} from {source_fund}")
            else:
                # Create empty file if source doesn't exist
                if file_name.endswith('.csv'):
                    if file_name == "llm_portfolio_update.csv":
                        with open(target_file, 'w') as f:
                            f.write("Date,Ticker,Shares,Average Price,Cost Basis,Stop Loss,Current Price,Total Value,PnL,Action,Company,Currency\n")
                    elif file_name == "llm_trade_log.csv":
                        with open(target_file, 'w') as f:
                            f.write("Date,Ticker,Action,Shares,Price,Total,Currency,Notes\n")
                    elif file_name == "fund_contributions.csv":
                        with open(target_file, 'w') as f:
                            f.write("Date,Amount,Currency,Type,Notes\n")
                    elif file_name == "exchange_rates.csv":
                        with open(target_file, 'w') as f:
                            f.write("Date,USD_CAD,Source\n")
                elif file_name.endswith('.json'):
                    with open(target_file, 'w') as f:
                        json.dump({"cad": 0.0, "usd": 0.0}, f, indent=2)
    
    def get_fund_config(self, fund_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific fund.
        
        Args:
            fund_name: Name of the fund
            
        Returns:
            Fund configuration dictionary or None if not found
        """
        if fund_name not in self.get_available_funds():
            return None
        
        config_path = self.funds_dir / fund_name / "fund_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config for fund {fund_name}: {e}")
            return None
    
    def get_fund_data_directory(self, fund_name: Optional[str] = None) -> Optional[str]:
        """Get the data directory path for a fund.
        
        Args:
            fund_name: Name of the fund (uses active fund if None)
            
        Returns:
            Data directory path or None if fund not found
        """
        if fund_name is None:
            fund_name = self.get_active_fund()
        
        if fund_name is None or fund_name not in self.get_available_funds():
            return None
        
        return str(self.funds_dir / fund_name)
    
    def get_fund_by_data_directory(self, data_directory: str) -> Optional[str]:
        """Find fund name by data directory path.
        
        Args:
            data_directory: Data directory path to search for
            
        Returns:
            Fund name if found, None otherwise
        """
        data_path = Path(data_directory).resolve()
        
        # Check if it's a direct fund directory
        for fund_name in self.get_available_funds():
            fund_dir = (self.funds_dir / fund_name).resolve()
            if data_path == fund_dir:
                return fund_name
        
        # Check if it's a subdirectory of a fund
        for fund_name in self.get_available_funds():
            fund_dir = (self.funds_dir / fund_name).resolve()
            try:
                data_path.relative_to(fund_dir)
                return fund_name
            except ValueError:
                # Not a subdirectory of this fund
                continue
        
        # Check if the data directory is actually a fund directory by looking at the folder name
        # This handles cases where the path doesn't match exactly but the folder name does
        if data_path.parent == self.funds_dir:
            folder_name = data_path.name
            if folder_name in self.get_available_funds():
                return folder_name
        
        return None
    
    def delete_fund(self, fund_name: str, confirm: bool = False) -> bool:
        """Delete a fund and all its data.
        
        Args:
            fund_name: Name of the fund to delete
            confirm: Confirmation flag to prevent accidental deletion
            
        Returns:
            True if successful, False otherwise
        """
        if not confirm:
            print_error("Fund deletion requires confirmation flag")
            return False
        
        if fund_name not in self.get_available_funds():
            print_error(f"Fund '{fund_name}' does not exist")
            return False
        
        # Don't allow deletion of the last fund
        if len(self.get_available_funds()) <= 1:
            print_error("Cannot delete the last remaining fund")
            return False
        
        try:
            fund_dir = self.funds_dir / fund_name
            shutil.rmtree(fund_dir)
            
            # If this was the active fund, switch to another one
            if self.get_active_fund() == fund_name:
                remaining_funds = self.get_available_funds()
                if remaining_funds:
                    self.set_active_fund(remaining_funds[0])
            
            print_success(f"Deleted fund '{fund_name}' successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to delete fund '{fund_name}': {e}")
            logger.error(f"Failed to delete fund {fund_name}: {e}")
            return False
    
    def get_fund_info(self, fund_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a fund.
        
        Args:
            fund_name: Name of the fund
            
        Returns:
            Dictionary with fund information or None if not found
        """
        config = self.get_fund_config(fund_name)
        if not config:
            return None
        
        fund_dir = self.funds_dir / fund_name
        
        # Get file information
        files_info = {}
        data_files = [
            "llm_portfolio_update.csv",
            "llm_trade_log.csv",
            "cash_balances.json",
            "fund_contributions.csv",
            "exchange_rates.csv"
        ]
        
        for file_name in data_files:
            file_path = fund_dir / file_name
            if file_path.exists():
                stat = file_path.stat()
                files_info[file_name] = {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                files_info[file_name] = {"exists": False}
        
        return {
            "name": fund_name,
            "config": config.get("fund", {}),
            "files": files_info,
            "directory": str(fund_dir),
            "is_active": fund_name == self.get_active_fund()
        }


# Global fund manager instance
_fund_manager: Optional[FundManager] = None


def get_fund_manager() -> FundManager:
    """Get the global fund manager instance.
    
    Returns:
        Global fund manager instance
    """
    global _fund_manager
    if _fund_manager is None:
        _fund_manager = FundManager()
    return _fund_manager


def invalidate_fund_manager_cache() -> None:
    """Invalidate the global fund manager cache to force refresh.
    
    This should be called after fund switches to ensure all instances
    pick up the new active fund immediately.
    """
    global _fund_manager
    _fund_manager = None
