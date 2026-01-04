
import requests
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _get_browser_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def test_archive(test_url):
    domains = ['archive.ph', 'archive.is', 'archive.md', 'archive.li', 'archive.today']
    
    for domain in domains:
        url = f"https://{domain}/newest/{test_url}"
        print(f"\nTesting {url}...")
        try:
            headers = _get_browser_headers()
            # Try without Referer first
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            print(f"Status Code: {resp.status_code}")
            print(f"Final URL: {resp.url}")
            print(f"Server: {resp.headers.get('Server')}")
            
            if resp.status_code == 200:
                print(f"Success! Content length: {len(resp.text)}")
                if "wants to see if you are a human" in resp.text:
                    print("CAPTCHA detected!")
                elif "document.getElementById('any')" in resp.text:
                    print("JS challenge detected!")
                else:
                    print("Content seems clean.")
            elif resp.status_code == 429:
                print("Rate limited (429)")
            else:
                print(f"Error status: {resp.status_code}")
                
        except Exception as e:
            print(f"Request failed: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # test_url_loader is in parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from test_url_loader import get_test_url
    
    target = get_test_url("FT_ARTICLE_1")
    test_archive(target)
