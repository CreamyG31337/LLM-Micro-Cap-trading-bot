#!/usr/bin/env python3
"""
Diagnostic script to find research articles with HTML code blocks in their summaries.
"""

import sys
import logging
from pathlib import Path
import re

# Add project root to path
# Add project root to path (web_dashboard/debug/script.py -> web_dashboard/debug -> web_dashboard -> root)
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_bad_summaries():
    client = PostgresClient()
    
    # Search for likely HTML patterns in summary
    # The user saw "<code class=" so let's look for that, and "st-emotion-cache"
    query = """
        SELECT id, ticker, title, summary, content
        FROM research_articles
        WHERE summary LIKE '%<code%' 
           OR summary LIKE '%st-emotion-cache%'
           OR content LIKE '%st-emotion-cache%'
           OR summary LIKE '%```%'
        LIMIT 20
    """
    
    try:
        results = client.execute_query(query)
        
        print(f"Found {len(results)} suspicious articles.")
        
        for art in results:
            print(f"\nID: {art['id']}")
            print(f"Ticker: {art['ticker']}")
            print(f"Title: {art['title']}")
            
            summary = art['summary']
            content = art['content']
            
            if "<code" in summary or "st-emotion-cache" in summary:
                print(">>> SUMMARY CONTAINS HTML/CODE BLOCKS <<<")
                # print snippet
                match = re.search(r'<code.*?</code>', summary, re.DOTALL)
                if match:
                    print(f"Snippet: {match.group(0)[:200]}...")
                else:
                    print(f"Summary start: {summary[:200]}...")
            
            if "st-emotion-cache" in content:
                print(">>> CONTENT CONTAINS STREAMLIT CLASSES <<<")
                idx = content.find("st-emotion-cache")
                start = max(0, idx - 50)
                end = min(len(content), idx + 100)
                print(f"Snippet: ...{content[start:end]}...")
                
    except Exception as e:
        logger.error(f"Error querying database: {e}")

if __name__ == "__main__":
    check_bad_summaries()
