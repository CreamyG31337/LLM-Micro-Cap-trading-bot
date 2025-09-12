"""Integration between configuration system and repository factory."""

from __future__ import annotations

import logging
from typing import Optional

from .repository_factory import configure_repositories, get_repository
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


def initialize_repositories_from_config(config_dict: Optional[dict] = None) -> BaseRepository:
    """Initialize repositories from configuration.
    
    This function integrates the configuration system with the repository factory
    to automatically configure repositories based on settings.
    
    Args:
        config_dict: Optional configuration dictionary. If None, will try to import
                    from config.settings module
        
    Returns:
        Default repository instance
    """
    if config_dict is None:
        try:
            # Try to import configuration system
            from config.settings import get_settings
            settings = get_settings()
            repo_config = settings.get_repository_config()
        except ImportError:
            # Fallback to default CSV configuration
            logger.warning("Configuration system not available, using default CSV repository")
            repo_config = {
                'type': 'csv',
                'data_directory': 'my trading'
            }
    else:
        repo_config = config_dict
    
    # Configure the repository container
    repository_config = {
        'default': repo_config
    }
    
    configure_repositories(repository_config)
    
    # Get the default repository instance
    repository = get_repository('default')
    
    logger.info(f"Initialized repository: {type(repository).__name__}")
    return repository


def get_configured_repository() -> BaseRepository:
    """Get a repository instance configured from system settings.
    
    This is a convenience function that handles the configuration loading
    and repository creation in one step.
    
    Returns:
        Configured repository instance
    """
    return initialize_repositories_from_config()