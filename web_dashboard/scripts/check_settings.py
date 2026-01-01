
import sys
import os
import logging
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from settings import get_system_setting

def main():
    key = "model_granite3.3:8b_num_ctx"
    
    # Force settings to try both paths if possible, but just call the function
    value = get_system_setting(key)
    
    print(f"Checking key: {key}")
    print(f"Value from get_system_setting: {value}")

if __name__ == "__main__":
    main()
