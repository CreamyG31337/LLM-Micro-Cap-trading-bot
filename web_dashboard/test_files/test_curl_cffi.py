#!/usr/bin/env python3
"""Test curl_cffi against archive.is with different impersonation profiles."""

from curl_cffi import requests
import time

def test_with_profile(url, profile):
    print(f"\n--- Testing with {profile} ---")
    try:
        response = requests.get(
            url, 
            impersonate=profile, 
            timeout=30,
            allow_redirects=True
        )
        
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            if len(response.text) > 5000:
                print(f"✅ SUCCESS! Content length: {len(response.text)}")
                return True
            else:
                print(f"⚠️ Short content: {len(response.text)} bytes")
        elif response.status_code == 429:
            # Check response body for hints
            body = response.text[:500] if response.text else ""
            if "rate" in body.lower() or "limit" in body.lower():
                print("Rate limit message found in body")
            if "captcha" in body.lower() or "human" in body.lower():
                print("CAPTCHA/human check found in body")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    import sys
    from pathlib import Path
    # test_url_loader is in parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from test_url_loader import get_test_url
    
    # Get obfuscated test URL
    ft_url = get_test_url("FT_ARTICLE_1")
    
    # Test a different URL first (maybe the specific FT article is hot-cached for rate limiting)
    test_urls = [
        f"https://archive.ph/newest/{ft_url}",
        # Also try a direct archived URL (bypassing /newest/)
        f"https://archive.ph/20251230112134/{ft_url}",
    ]
    
    profiles = ["chrome124", "chrome", "safari", "edge"]
    
    for url in test_urls[:1]:  # Just test first URL
        print(f"\n=== Testing URL: {url[:60]}... ===")
        for profile in profiles:
            success = test_with_profile(url, profile)
            if success:
                print(f"\n🎉 Found working profile: {profile}")
                return
            time.sleep(2)  # Brief pause between attempts
    
    print("\n❌ All profiles failed")

if __name__ == "__main__":
    main()
