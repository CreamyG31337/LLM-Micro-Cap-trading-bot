import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

from settings import get_alpha_research_domains, get_alpha_search_queries

def print_status(msg): print(f"\n🔵 {msg}")
def print_success(msg): print(f"✅ {msg}")
def print_error(msg): print(f"❌ {msg}")
def print_warning(msg): print(f"⚠️ {msg}")

def test_alpha_search():
    print_status("Testing Alpha Research Query Construction...")
    
    # 1. Test Settings
    try:
        domains = get_alpha_research_domains()
        queries = get_alpha_search_queries()
    except Exception as e:
        print_error(f"Failed to get settings: {e}")
        return
    
    if not domains:
        print_error("No alpha domains found!")
        return
    if not queries:
        print_error("No alpha queries found!")
        return
        
    print_success(f"Found {len(domains)} domains and {len(queries)} queries.")
    print(f"Domains: {domains[:3]}...")
    print(f"Queries: {queries[:3]}...")
    
    # 2. Test Query Construction
    site_dork = " OR ".join([f"site:{d}" for d in domains])
    base_query = queries[0]
    final_query = f'{base_query} ({site_dork})'
    
    print_status(" Constructed Query:")
    print(f" > {final_query}")
    
    # 3. Test Search (Dry Run)
    try:
        from searxng_client import get_searxng_client
        client = get_searxng_client()
        
        if not client:
            print_warning("SearXNG client not available - skipping live search test.")
            return

        print_status("🚀 Running live test search (limit 3)...")
        results = client.search_news(query=final_query, max_results=3)
        
        if results and results.get('results'):
            count = len(results['results'])
            print_success(f"✅ Search successful! Found {count} results.")
            for i, res in enumerate(results['results']):
                print(f"  {i+1}. [{res.get('source', 'Unknown')}] {res.get('title', 'No Title')} ({res.get('url')})")
        else:
            print_warning("⚠️ No results found. This might be due to strict dorks or no matches right now.")
            
    except Exception as e:
        print_error(f"Search failed: {e}")

if __name__ == "__main__":
    test_alpha_search()
