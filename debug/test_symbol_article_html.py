#!/usr/bin/env python3
"""
Quick helper script to fetch and inspect symbol page HTML structure.
Use this to understand the page structure before writing the scraper.
"""

import sys
import base64
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

try:
    import trafilatura
    from bs4 import BeautifulSoup
    from symbol_article_scraper import build_symbol_url
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install trafilatura beautifulsoup4")
    sys.exit(1)

def fetch_and_inspect(ticker: str):
    """Fetch a symbol page and inspect its structure."""
    print(f"\n{'='*70}")
    print(f"Inspecting symbol page for: {ticker}")
    print(f"{'='*70}\n")
    
    # Construct URL using the scraper function
    url = build_symbol_url(ticker)
    print(f"URL: {url}\n")
    
    # Fetch HTML
    print("Fetching HTML...")
    try:
        html = trafilatura.fetch_url(url)
        if not html:
            print("❌ Failed to fetch HTML")
            return
        
        print(f"✅ Fetched {len(html)} characters\n")
    except Exception as e:
        print(f"❌ Error fetching: {e}")
        return
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all links
    print("=" * 70)
    print("ALL LINKS FOUND:")
    print("=" * 70)
    all_links = soup.find_all('a', href=True)
    print(f"Total links found: {len(all_links)}\n")
    
    # Categorize links
    article_links = []
    news_links = []
    analysis_links = []
    other_links = []
    
    for link in all_links:
        href = link.get('href', '')
        if not href:
            continue
        
        # Make absolute URL if relative
        if href.startswith('/'):
            from symbol_article_scraper import BASE_URL
            href = f"{BASE_URL}{href}"
        
        text = link.get_text(strip=True)
        
        if '/article/' in href:
            article_links.append((href, text))
        elif '/news/' in href:
            news_links.append((href, text))
        elif '/analysis/' in href:
            analysis_links.append((href, text))
        else:
            other_links.append((href, text))
    
    # Print categorized links
    print(f"\n📄 ARTICLE LINKS (/article/): {len(article_links)}")
    for href, text in article_links[:10]:  # Show first 10
        print(f"  - {text[:60]:<60} {href[:80]}")
    if len(article_links) > 10:
        print(f"  ... and {len(article_links) - 10} more")
    
    print(f"\n📰 NEWS LINKS (/news/): {len(news_links)}")
    for href, text in news_links[:10]:
        print(f"  - {text[:60]:<60} {href[:80]}")
    if len(news_links) > 10:
        print(f"  ... and {len(news_links) - 10} more")
    
    print(f"\n📊 ANALYSIS LINKS (/analysis/): {len(analysis_links)}")
    for href, text in analysis_links[:10]:
        print(f"  - {text[:60]:<60} {href[:80]}")
    if len(analysis_links) > 10:
        print(f"  ... and {len(analysis_links) - 10} more")
    
    # Look for common containers
    print(f"\n{'='*70}")
    print("HTML STRUCTURE ANALYSIS:")
    print(f"{'='*70}\n")
    
    # Check for common article container patterns
    containers = [
        ('div', {'class': lambda x: x and 'article' in x.lower()}),
        ('div', {'class': lambda x: x and 'news' in x.lower()}),
        ('section', {'class': lambda x: x and 'article' in x.lower()}),
        ('article', {}),
    ]
    
    for tag, attrs in containers:
        found = soup.find_all(tag, attrs)
        if found:
            print(f"Found {len(found)} <{tag}> elements matching pattern")
            if found:
                print(f"  First element classes: {found[0].get('class', [])}")
    
    # Look for data attributes or IDs that might indicate articles
    print("\nLooking for data attributes...")
    data_attrs = soup.find_all(attrs={'data-testid': True})
    if data_attrs:
        test_ids = set([elem.get('data-testid') for elem in data_attrs[:20]])
        print(f"  Found data-testid values: {sorted(list(test_ids))[:10]}")
    
    # Save HTML sample for inspection
    sample_file = Path(__file__).parent / f"symbol_article_{ticker}_sample.html"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(html[:50000])  # First 50k chars
    print(f"\n💾 Saved HTML sample to: {sample_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Inspect symbol page HTML')
    parser.add_argument('ticker', nargs='?', default='STLD', help='Ticker symbol to inspect (default: STLD)')
    args = parser.parse_args()
    
    fetch_and_inspect(args.ticker.upper())

