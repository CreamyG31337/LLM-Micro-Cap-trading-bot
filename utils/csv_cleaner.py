#!/usr/bin/env python3
"""
CSV file cleaning utilities.

This module provides utilities to clean up CSV files, particularly removing
blank lines that can occur when appending data to existing files.
"""

import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def remove_blank_lines_from_csv(file_path: Path) -> int:
    """Remove blank lines from a CSV file.
    
    Args:
        file_path: Path to the CSV file to clean
        
    Returns:
        Number of blank lines removed
    """
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return 0
    
    try:
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out blank lines (lines that are empty or contain only whitespace)
        non_blank_lines = [line for line in lines if line.strip()]
        
        # Count removed lines
        removed_count = len(lines) - len(non_blank_lines)
        
        if removed_count > 0:
            # Write back the cleaned lines
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(non_blank_lines)
            
            logger.info(f"Removed {removed_count} blank lines from {file_path}")
        else:
            logger.info(f"No blank lines found in {file_path}")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"Failed to clean CSV file {file_path}: {e}")
        return 0


def ensure_csv_ends_with_newline(file_path: Path) -> bool:
    """Ensure a CSV file ends with a single newline.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        True if file was modified, False if already correct
    """
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file ends with exactly one newline
        if content.endswith('\n') and not content.endswith('\n\n'):
            logger.info(f"File {file_path} already ends with proper newline")
            return False
        
        # Remove trailing newlines and add exactly one
        content = content.rstrip('\n') + '\n'
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Fixed newline ending in {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix newline in {file_path}: {e}")
        return False


def clean_trading_data_csvs(data_dir: str) -> dict:
    """Clean all CSV files in the trading data directory.
    
    Args:
        data_dir: Path to the trading data directory
        
    Returns:
        Dictionary with cleaning results for each file
    """
    data_path = Path(data_dir)
    results = {}
    
    if not data_path.exists():
        logger.error(f"Data directory does not exist: {data_path}")
        return results
    
    # Find all CSV files
    csv_files = list(data_path.glob("**/*.csv"))
    
    for csv_file in csv_files:
        logger.info(f"Cleaning {csv_file}")
        
        # Remove blank lines
        blank_lines_removed = remove_blank_lines_from_csv(csv_file)
        
        # Ensure proper newline ending
        newline_fixed = ensure_csv_ends_with_newline(csv_file)
        
        results[str(csv_file)] = {
            'blank_lines_removed': blank_lines_removed,
            'newline_fixed': newline_fixed
        }
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean CSV files in trading data directory")
    parser.add_argument("--data-dir", default="trading_data/dev", help="Data directory to clean")
    parser.add_argument("--file", help="Specific CSV file to clean")
    
    args = parser.parse_args()
    
    if args.file:
        # Clean specific file
        file_path = Path(args.file)
        blank_removed = remove_blank_lines_from_csv(file_path)
        newline_fixed = ensure_csv_ends_with_newline(file_path)
        print(f"Cleaned {file_path}: {blank_removed} blank lines removed, newline fixed: {newline_fixed}")
    else:
        # Clean all CSV files in directory
        results = clean_trading_data_csvs(args.data_dir)
        print(f"Cleaned {len(results)} CSV files in {args.data_dir}")
        for file_path, result in results.items():
            print(f"  {file_path}: {result['blank_lines_removed']} blank lines removed, newline fixed: {result['newline_fixed']}")
