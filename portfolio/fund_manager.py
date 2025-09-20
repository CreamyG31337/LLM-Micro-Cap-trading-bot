"""Fund management module.

This module provides the FundManager class for loading and managing fund 
configurations from a YAML file. It defines the data models for funds and 
their repository settings, ensuring a structured approach to multi-fund support.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class FundManagerError(Exception):
    """Base exception for fund manager operations."""
    pass


@dataclass
class RepositorySettings:
    """Settings for a fund's data repository."""
    type: str
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fund:
    """Represents a single investment fund."""
    id: str
    name: str
    description: str
    repository: RepositorySettings


class FundManager:
    """Manages loading and accessing fund configurations."""

    def __init__(self, config_path: Path):
        """Initialize fund manager.
        
        Args:
            config_path: Path to the funds YAML configuration file
        """
        self.config_path = config_path
        self.funds: List[Fund] = []
        self._load_funds()

    def _load_funds(self) -> None:
        """Load fund configurations from the YAML file."""
        try:
            logger.info(f"Loading funds from {self.config_path}")
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict) or 'funds' not in config:
                raise FundManagerError("Invalid YAML format: 'funds' key not found")

            for fund_data in config['funds']:
                repo_settings = RepositorySettings(**fund_data['repository'])
                fund = Fund(
                    id=fund_data['id'],
                    name=fund_data['name'],
                    description=fund_data['description'],
                    repository=repo_settings
                )
                self.funds.append(fund)
            
            logger.info(f"Loaded {len(self.funds)} funds")

        except FileNotFoundError:
            logger.error(f"Fund configuration file not found: {self.config_path}")
            raise FundManagerError(f"Fund configuration file not found: {self.config_path}")
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise FundManagerError(f"Error parsing YAML file: {e}")
        
        except (KeyError, TypeError) as e:
            logger.error(f"Invalid fund configuration format: {e}")
            raise FundManagerError(f"Invalid fund configuration format: {e}")

    def get_all_funds(self) -> List[Fund]:
        """Get a list of all loaded funds."""
        return self.funds

    def get_fund_by_id(self, fund_id: str) -> Fund | None:
        """Get a fund by its ID.
        
        Args:
            fund_id: The ID of the fund to retrieve
            
        Returns:
            The Fund object or None if not found
        """
        for fund in self.funds:
            if fund.id == fund_id:
                return fund
        return None
