#!/usr/bin/env python3
"""
Test Archive Service Integration
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from archive_service import check_archived, get_archived_content
from test_url_loader import get_test_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_integration():
    url = get_test_url("FT_ARTICLE_1")
    
    print(f"Testing integration for: {url}")
    
    # 1. Check archive
    print("Checking archive...")
    archived_url = check_archived(url)
    print(f"Archived URL: {archived_url}")
    
    if archived_url:
        # 2. Get content
        print("Fetching content...")
        content = get_archived_content(archived_url)
        
        if content:
            print(f"✅ Success! Content length: {len(content)}")
            if "Japanese stocks" in content:
                print("✅ Valid content verified")
            else:
                print("⚠️ Content retrieved but verification string not found (might be different article or blocked)")
        else:
            print("❌ Failed to fetch content")
    else:
        print("❌ Failed to resolve archive URL")

if __name__ == "__main__":
    test_integration()
