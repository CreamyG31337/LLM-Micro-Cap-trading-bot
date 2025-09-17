"""Configuration management system."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Configuration management class for the trading system.
    
    This class handles loading and managing configuration settings,
    including repository type selection and database configuration.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize settings.
        
        Args:
            config_file: Optional path to configuration file
        """
        self._config: Dict[str, Any] = {}
        self._config_file = config_file
        self._load_default_config()
        
        if config_file:
            self.load_from_file(config_file)
        
        # Load from environment variables
        self._load_from_environment()
    
    def _load_default_config(self) -> None:
        """Load default configuration values."""
        # Try to get active fund data directory, fallback to legacy
        active_fund_data_dir = self._get_active_fund_data_directory()
        
        self._config = {
            'repository': {
                'type': 'csv',
                'csv': {
                    'data_directory': active_fund_data_dir
                },
                'database': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'trading_system',
                    'username': 'trading_user',
                    'password': '',
                    'ssl_mode': 'prefer'
                }
            },
            'market_data': {
                'primary_source': 'yahoo',
                'fallback_source': 'stooq',
                'cache_enabled': True,
                'cache_duration_hours': 24,
                'fundamentals_cache_persist': True,
                'fundamentals_cache_ttl_hours': 12
            },
            'timezone': {
                'name': 'PST',
                'offset_hours': -8,
                'utc_offset': '-08:00'
            },
            'logging': {
                'level': 'INFO',
                'file': 'trading_bot_dev.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'backup': {
                'enabled': True,
                'directory': 'backups',
                'max_backups': 10,
                'auto_backup_on_save': True
            },
            'fund': self._get_active_fund_config()
        }
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Repository configuration
        if os.getenv('TRADING_REPOSITORY_TYPE'):
            self._config['repository']['type'] = os.getenv('TRADING_REPOSITORY_TYPE')
        
        if os.getenv('TRADING_DATA_DIR'):
            self._config['repository']['csv']['data_directory'] = os.getenv('TRADING_DATA_DIR')
        
        # Database configuration
        if os.getenv('TRADING_DB_HOST'):
            self._config['repository']['database']['host'] = os.getenv('TRADING_DB_HOST')
        
        if os.getenv('TRADING_DB_PORT'):
            self._config['repository']['database']['port'] = int(os.getenv('TRADING_DB_PORT'))
        
        if os.getenv('TRADING_DB_NAME'):
            self._config['repository']['database']['database'] = os.getenv('TRADING_DB_NAME')
        
        if os.getenv('TRADING_DB_USER'):
            self._config['repository']['database']['username'] = os.getenv('TRADING_DB_USER')
        
        if os.getenv('TRADING_DB_PASSWORD'):
            self._config['repository']['database']['password'] = os.getenv('TRADING_DB_PASSWORD')
        
        # Fund configuration
        if os.getenv('FUND_NAME'):
            if 'fund' not in self._config:
                self._config['fund'] = {}
            self._config['fund']['name'] = os.getenv('FUND_NAME')
        
        if os.getenv('FUND_DESCRIPTION'):
            if 'fund' not in self._config:
                self._config['fund'] = {}
            self._config['fund']['description'] = os.getenv('FUND_DESCRIPTION')
        
        # Development mode
        if os.getenv('TRADING_BOT_DEV', 'false').lower() == 'true':
            self._config['logging']['level'] = 'DEBUG'
    
    def load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file.
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return
        
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            # Merge with existing configuration
            self._merge_config(self._config, file_config)
            logger.info(f"Loaded configuration from: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration file {config_file}: {e}")
    
    def save_to_file(self, config_file: str) -> None:
        """Save configuration to JSON file.
        
        Args:
            config_file: Path to save configuration file
        """
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            
            logger.info(f"Saved configuration to: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration file {config_file}: {e}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'repository.type')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def get_repository_config(self) -> Dict[str, Any]:
        """Get repository configuration.
        
        Returns:
            Repository configuration dictionary
        """
        repo_type = self.get('repository.type', 'csv')
        repo_config = self.get(f'repository.{repo_type}', {})
        
        return {
            'type': repo_type,
            **repo_config
        }
    
    def get_data_directory(self) -> str:
        """Get data directory path.
        
        Returns:
            Data directory path
        """
        # Always get the current active fund data directory
        return self._get_active_fund_data_directory()
    
    def get_repository_type(self) -> str:
        """Get repository type.
        
        Returns:
            Repository type ('csv', 'database', etc.)
        """
        return self.get('repository.type', 'csv')
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration.
        
        Returns:
            Database configuration dictionary
        """
        return self.get('repository.database', {})
    
    def is_development_mode(self) -> bool:
        """Check if development mode is enabled.
        
        Returns:
            True if development mode is enabled
        """
        return os.getenv('TRADING_BOT_DEV', 'false').lower() == 'true'
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration.
        
        Returns:
            Logging configuration dictionary
        """
        return self.get('logging', {})
    
    def get_backup_config(self) -> Dict[str, Any]:
        """Get backup configuration.
        
        Returns:
            Backup configuration dictionary
        """
        return self.get('backup', {})
    
    def get_fund_name(self) -> str:
        """Get fund name.
        
        Returns:
            Fund name for display purposes
        """
        # Always get the current active fund name
        active_fund_config = self._get_active_fund_config()
        return active_fund_config.get('name', 'Your Investments')
    
    def get_fund_config(self) -> Dict[str, Any]:
        """Get fund configuration.
        
        Returns:
            Fund configuration dictionary
        """
        # Always get the current active fund configuration
        return self._get_active_fund_config()
    
    def _get_active_fund_data_directory(self) -> str:
        """Get the data directory for the currently active fund.
        
        Returns:
            Data directory path for active fund or legacy fallback
        """
        try:
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info["data_directory"]:
                return fund_info["data_directory"]
        
        except ImportError:
            # Fund management not available, use legacy
            pass
        except Exception:
            # Any other error, fall back to legacy
            pass
        
        # Fallback to legacy structure
        return 'trading_data/prod'
    
    def _get_active_fund_config(self) -> Dict[str, Any]:
        """Get the configuration for the currently active fund.
        
        Returns:
            Fund configuration dictionary
        """
        try:
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            
            if fund_info["exists"] and fund_info.get("config"):
                return fund_info["config"].get("fund", {})
        
        except ImportError:
            # Fund management not available, use default
            pass
        except Exception:
            # Any other error, fall back to default
            pass
        
        # Fallback to default fund configuration
        return {
            'name': 'Project Chimera',
            'description': 'AI-Powered Micro-Cap Investment Fund',
            'display_currency': 'CAD'
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Global settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def configure_system(config_file: Optional[str] = None) -> Settings:
    """Configure the system with settings.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Configured settings instance
    """
    global _settings
    _settings = Settings(config_file)
    return _settings