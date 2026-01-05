#!/usr/bin/env python3
"""
Research Report Processing Service
==================================

Handles scanning, parsing, and processing of PDF research reports
stored in organized folders (Research/{TICKER}/, Research/_MARKET/, Research/_CHIMERA/, Research/_WEBULL/).
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)

# Base research directory (relative to project root)
RESEARCH_BASE_DIR = Path(__file__).parent.parent / "Research"

# Config file path
CONFIG_FILE = Path(__file__).parent / "research_funds_config.json"


def load_fund_config() -> Dict:
    """
    Load fund configuration from JSON file.
    
    Returns:
        Dictionary with fund mappings and market folder name
    """
    default_config = {
        "funds": {
            "CHIMERA": {
                "folder": "_CHIMERA",
                "display_name": "Project Chimera"
            },
            "WEBULL": {
                "folder": "_WEBULL",
                "display_name": "Webull Fund"
            }
        },
        "market_folder": "_MARKET"
    }
    
    if not CONFIG_FILE.exists():
        logger.warning(f"Config file not found: {CONFIG_FILE}, using defaults")
        # Create default config file
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config file: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to create config file: {e}")
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Validate structure
        if "funds" not in config or "market_folder" not in config:
            logger.warning("Invalid config structure, using defaults")
            return default_config
        return config
    except Exception as e:
        logger.error(f"Failed to load config file {CONFIG_FILE}: {e}, using defaults")
        return default_config


def get_fund_folder(fund_abbrev: str) -> Optional[str]:
    """
    Get folder name for a fund abbreviation.
    
    Args:
        fund_abbrev: Fund abbreviation (e.g., "CHIMERA", "WEBULL")
        
    Returns:
        Folder name (e.g., "_CHIMERA") or None if not found
    """
    config = load_fund_config()
    fund_info = config.get("funds", {}).get(fund_abbrev.upper())
    if fund_info:
        return fund_info.get("folder")
    return None


def get_fund_display_name(fund_abbrev: str) -> Optional[str]:
    """
    Get display name for a fund abbreviation.
    
    Args:
        fund_abbrev: Fund abbreviation (e.g., "CHIMERA", "WEBULL")
        
    Returns:
        Display name (e.g., "Project Chimera") or None if not found
    """
    config = load_fund_config()
    fund_info = config.get("funds", {}).get(fund_abbrev.upper())
    if fund_info:
        return fund_info.get("display_name")
    return None


def get_available_funds() -> List[str]:
    """
    Get list of available fund abbreviations.
    
    Returns:
        List of fund abbreviations (e.g., ["CHIMERA", "WEBULL"])
    """
    config = load_fund_config()
    return list(config.get("funds", {}).keys())


def get_market_folder() -> str:
    """
    Get market folder name from config.
    
    Returns:
        Market folder name (default: "_MARKET")
    """
    config = load_fund_config()
    return config.get("market_folder", "_MARKET")


def get_fund_from_folder(folder_name: str) -> Optional[str]:
    """
    Get fund abbreviation from folder name.
    
    Args:
        folder_name: Folder name (e.g., "_CHIMERA", "_WEBULL")
        
    Returns:
        Fund abbreviation (e.g., "CHIMERA") or None if not found
    """
    config = load_fund_config()
    for fund_abbrev, fund_info in config.get("funds", {}).items():
        if fund_info.get("folder") == folder_name:
            return fund_abbrev
    return None


def ensure_research_folder() -> Path:
    """
    Ensure the Research folder exists, create it if it doesn't.
    
    Returns:
        Path to the Research directory
    """
    if not RESEARCH_BASE_DIR.exists():
        RESEARCH_BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created Research directory: {RESEARCH_BASE_DIR}")
    return RESEARCH_BASE_DIR


def scan_research_folder() -> List[Path]:
    """
    Scan Research/ directory for all PDF files.
    
    Returns:
        List of Path objects for all PDF files found
    """
    pdf_files = []
    
    # Ensure Research folder exists
    ensure_research_folder()
    
    if not RESEARCH_BASE_DIR.exists():
        logger.warning(f"Research directory does not exist: {RESEARCH_BASE_DIR}")
        return pdf_files
    
    # Scan all subdirectories
    for folder in RESEARCH_BASE_DIR.iterdir():
        if folder.is_dir():
            for pdf_file in folder.glob("*.pdf"):
                pdf_files.append(pdf_file)
    
    logger.info(f"Found {len(pdf_files)} PDF files in Research directory")
    return pdf_files


# Ensure Research folder exists on module import
try:
    ensure_research_folder()
except Exception as e:
    logger.warning(f"Could not create Research folder on import: {e}")


def add_date_prefix_to_filename(file_path: Path) -> Path:
    """
    Add YYYYMMDD date prefix to filename if not present.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        New Path with date prefix (file is renamed)
    """
    filename = file_path.name
    
    # Check if filename already starts with YYYYMMDD pattern
    date_pattern = re.compile(r'^\d{8}_')
    if date_pattern.match(filename):
        logger.debug(f"Filename already has date prefix: {filename}")
        return file_path
    
    # Add current date prefix
    today = datetime.now(timezone.utc)
    date_prefix = today.strftime("%Y%m%d")
    
    new_filename = f"{date_prefix}_{filename}"
    new_path = file_path.parent / new_filename
    
    # Rename file
    try:
        file_path.rename(new_path)
        logger.info(f"Renamed file: {file_path.name} -> {new_path.name}")
        return new_path
    except Exception as e:
        logger.error(f"Failed to rename file {file_path}: {e}")
        return file_path


def extract_title_from_filename(filename: str) -> str:
    """
    Remove YYYYMMDD_ prefix and .pdf extension to get clean title.
    
    Args:
        filename: Filename with optional date prefix
        
    Returns:
        Clean title without date prefix and extension
    """
    # Remove .pdf extension
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Remove YYYYMMDD_ prefix if present
    date_pattern = re.compile(r'^\d{8}_')
    title = date_pattern.sub('', title)
    
    # Clean up: replace underscores and hyphens with spaces, title case
    title = title.replace('_', ' ').replace('-', ' ').strip()
    
    return title


def determine_report_type(folder_path: Path) -> Dict[str, Optional[str]]:
    """
    Determine if ticker, market, or fund report from folder path.
    
    Args:
        folder_path: Path to the folder containing the PDF
        
    Returns:
        Dictionary with 'type', 'ticker', and 'fund' keys
    """
    folder_name = folder_path.name
    market_folder = get_market_folder()
    
    if folder_name == market_folder:
        return {
            'type': 'market',
            'ticker': None,
            'fund': None
        }
    
    # Check if it's a fund folder
    fund_abbrev = get_fund_from_folder(folder_name)
    if fund_abbrev:
        return {
            'type': 'fund',
            'ticker': None,
            'fund': fund_abbrev
        }
    
    # Assume it's a ticker folder
    return {
        'type': 'ticker',
        'ticker': folder_name.upper(),
        'fund': None
    }


def extract_ticker_from_folder(folder_path: Path) -> Optional[str]:
    """
    Extract ticker from folder name.
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        Ticker symbol (uppercase) or None
    """
    folder_name = folder_path.name
    market_folder = get_market_folder()
    
    # Check if it's market or fund folder
    if folder_name == market_folder:
        return None
    
    if get_fund_from_folder(folder_name):
        return None
    
    return folder_name.upper()


def parse_filename_date(filename: str) -> Optional[datetime]:
    """
    Parse date from filename YYYYMMDD prefix.
    
    Args:
        filename: Filename with YYYYMMDD prefix
        
    Returns:
        datetime object or None if no date found
    """
    date_pattern = re.compile(r'^(\d{8})_')
    match = date_pattern.match(filename)
    
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid date format in filename: {filename}")
            return None
    
    return None


def get_relative_path(file_path: Path) -> str:
    """
    Get relative path from project root.
    
    Args:
        file_path: Absolute path to file
        
    Returns:
        Relative path string (e.g., "Research/GANX/20250115_report.pdf")
    """
    project_root = Path(__file__).parent.parent
    
    try:
        relative_path = file_path.relative_to(project_root)
        # Convert to forward slashes for cross-platform compatibility
        return str(relative_path).replace('\\', '/')
    except ValueError:
        # File is not under project root, return absolute path as string
        logger.warning(f"File {file_path} is not under project root")
        return str(file_path)


def check_file_already_processed(file_path: Path, repository) -> bool:
    """
    Check if a file has already been processed by querying database.
    
    Args:
        file_path: Path to the PDF file
        repository: ResearchRepository instance
        
    Returns:
        True if file already exists in database, False otherwise
    """
    relative_path = get_relative_path(file_path)
    
    try:
        # Query by url field
        query = "SELECT id FROM research_articles WHERE url = %s"
        result = repository.client.execute_query(query, (relative_path,))
        return len(result) > 0
    except Exception as e:
        logger.error(f"Error checking if file is processed: {e}")
        return False

