#!/usr/bin/env python3
"""
Check data source configuration
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

def check_config():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Check what data source is configured
    from web_dashboard.app import get_data_source_config

    print('=== Checking Data Source Configuration ===')
    data_source = get_data_source_config()
    print(f'Configured data source: {data_source}')

    # Check if repository config exists
    config_file = Path('repository_config.json')
    if config_file.exists():
        print('Repository config exists')
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f'Web dashboard data source: {config.get("web_dashboard", {}).get("data_source")}')
    else:
        print('No repository config file found')

if __name__ == "__main__":
    check_config()
