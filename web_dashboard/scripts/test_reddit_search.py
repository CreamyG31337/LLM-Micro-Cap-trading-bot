import requests
import time
from datetime import datetime, timezone, timedelta

def test_reddit_search(ticker):
    print(f"\n{'='*50}")
    print(f"Testing Reddit Search for: {ticker}")
    print(f"{'='*50}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Test both query types
    queries = [f"${ticker}", ticker]
    
    for query in queries:
        print(f"\n🔎 Query: '{query}'")
        print(f"{'-'*30}")
        
        try:
            url = f"https://www.reddit.com/search.json?q={query}&sort=new&t=day&limit=5"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                continue
                
            data = response.json()
            posts = []
            
            if 'data' in data and 'children' in data['data']:
                for child in data['data']['children']:
                    post = child.get('data', {})
                    if not post: continue
                    
                    posts.append({
                        'title': post.get('title', 'N/A')[:80], # Truncate for display
                        'subreddit': post.get('subreddit', 'N/A'),
                        'score': post.get('score', 0),
                        'created': datetime.fromtimestamp(post.get('created_utc', 0)).strftime('%H:%M:%S'),
                        'url': post.get('url', '')
                    })
            
            if not posts:
                print("   (No results found)")
            else:
                for p in posts:
                    print(f"   [{p['subreddit']}] {p['title']}...")
                    print(f"    ↳ Score: {p['score']} | Time: {p['created']}")
            
            time.sleep(2) # Respect rate limits between queries
            
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # Test a mix of distinct and common-word tickers
    test_tickers = ["LUNR", "NVDA", "CAT", "AI", "GOOD"]
    
    for t in test_tickers:
        test_reddit_search(t)
