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
    print_status("Alpha Research Configuration Review")
    
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
        
    print_success(f"Total Alpha Domains: {len(domains)}")
    print(f"Sites: {', '.join(domains[:10])}...")
    
    print_success(f"Total Alpha Queries: {len(queries)}")
    print(f"Sample Queries: {queries[:3]}...")
    
    # 2. Test Query Construction
    site_dork = " OR ".join([f"site:{d}" for d in domains])
    # Pick a random query to show
    import random
    base_query = random.choice(queries)
    final_query = f'{base_query} ({site_dork})'
    
    print_status(f"Example Constructed Query (Query: '{base_query}'):")
    print("-" * 50)
    print(final_query)
    print("-" * 50)
    print(f"Query Length: {len(final_query)} characters")

    if len(final_query) > 2000:
        print_warning("Note: Query is very long. Some search engines may truncate queries over 2048 characters.")
    
    # 3. Connectivity Check (Simple)
    print_status("Environment Connectivity Check:")
    import os
    base_url = os.getenv("SEARXNG_BASE_URL", "default")
    print(f"SEARXNG_BASE_URL: {base_url}")
    if "host.docker.internal" in base_url:
        print_info = "Running from host? 'host.docker.internal' only works inside containers. This is likely why live search fails here."
        print(f"ℹ️ {print_info}")

if __name__ == "__main__":
    test_alpha_search()
