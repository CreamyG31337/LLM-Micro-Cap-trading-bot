#!/usr/bin/env python3
"""
Research Report Processing Service
==================================

Handles scanning, parsing, and processing of PDF research reports
stored in organized folders (Research/{TICKER}/, Research/_NEWS/, Research/_FUND/).
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)

# Base research directory (relative to project root)
RESEARCH_BASE_DIR = Path(__file__).parent.parent / "Research"


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
    Determine if ticker, news, or fund report from folder path.
    
    Args:
        folder_path: Path to the folder containing the PDF
        
    Returns:
        Dictionary with 'type', 'ticker', and 'fund' keys
    """
    folder_name = folder_path.name
    
    if folder_name == "_NEWS":
        return {
            'type': 'news',
            'ticker': None,
            'fund': None
        }
    elif folder_name == "_FUND":
        return {
            'type': 'fund',
            'ticker': None,
            'fund': None  # Fund name would need to be determined separately
        }
    else:
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
    
    if folder_name in ["_NEWS", "_FUND"]:
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

