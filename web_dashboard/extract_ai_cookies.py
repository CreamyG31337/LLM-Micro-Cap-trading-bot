#!/usr/bin/env python3
"""
Extract AI Service Cookies from Browser
=======================================

Helps extract cookies from your browser to use with the AI service web interface.

Supports:
- Chrome/Edge (Windows)
- Firefox (Windows)
- Manual extraction instructions

Usage:
    python web_dashboard/extract_ai_cookies.py [--browser chrome|firefox|edge] [--output cookies.json]
"""

import sys
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from base64 import b64decode
try:
    import win32crypt  # Windows only
    HAS_WIN32CRYPT = True
except ImportError:
    HAS_WIN32CRYPT = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Browser cookie database paths (Windows)
CHROME_COOKIE_PATH = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"
EDGE_COOKIE_PATH = Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cookies"
FIREFOX_COOKIE_PATH = Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"


def extract_chrome_cookies(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract cookies from Chrome/Edge browser.
    
    Args:
        domain: Domain to extract cookies for (default: from keys file)
        
    Returns:
        List of cookie dictionaries
    """
    if domain is None:
        # Try to get domain from obfuscated keys
        try:
            from ai_service_keys import get_service_url
            # Extract domain from URL
            url = get_service_url("WEB_BASE_URL")
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or "generativelanguage.googleapis.com"
        except:
            domain = "generativelanguage.googleapis.com"
    cookies = []
    
    # Try Chrome first
    cookie_db = CHROME_COOKIE_PATH
    if not cookie_db.exists():
        # Try Edge
        cookie_db = EDGE_COOKIE_PATH
        if not cookie_db.exists():
            logger.error("Chrome/Edge cookie database not found")
            return cookies
    
    try:
        # Chrome/Edge encrypt cookies, we need to decrypt them
        # Copy the database first (Chrome locks it)
        import shutil
        import tempfile
        
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        shutil.copy2(cookie_db, temp_db.name)
        
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        
        # Query cookies for the domain
        cursor.execute("""
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE ?
        """, (f"%{domain}%",))
        
        for row in cursor.fetchall():
            name, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly = row
            
            try:
                # Decrypt the cookie value (Windows)
                if sys.platform == 'win32' and HAS_WIN32CRYPT:
                    try:
                        value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
                    except:
                        # Fallback: try base64 decode
                        try:
                            value = b64decode(encrypted_value).decode('utf-8')
                        except:
                            value = str(encrypted_value)
                else:
                    # Linux/Mac or no win32crypt: cookies may not be encrypted or use different method
                    if isinstance(encrypted_value, bytes):
                        try:
                            value = encrypted_value.decode('utf-8')
                        except:
                            value = str(encrypted_value)
                    else:
                        value = str(encrypted_value)
                
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": host_key,
                    "path": path,
                    "secure": bool(is_secure),
                    "httpOnly": bool(is_httponly),
                })
            except Exception as e:
                logger.debug(f"Failed to decrypt cookie {name}: {e}")
                continue
        
        conn.close()
        Path(temp_db.name).unlink()  # Clean up temp file
        
        logger.info(f"Extracted {len(cookies)} cookies from Chrome/Edge")
        
    except Exception as e:
        logger.error(f"Failed to extract Chrome cookies: {e}")
        if sys.platform == 'win32' and not HAS_WIN32CRYPT:
            logger.info("Note: For Windows, you may need to install pywin32: pip install pywin32")
        logger.info("Alternatively, use --browser manual for manual extraction instructions")
    
    return cookies


def extract_firefox_cookies(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract cookies from Firefox browser.
    
    Args:
        domain: Domain to extract cookies for (default: from keys file)
        
    Returns:
        List of cookie dictionaries
    """
    if domain is None:
        # Try to get domain from obfuscated keys
        try:
            from ai_service_keys import get_service_url
            # Extract domain from URL
            url = get_service_url("WEB_BASE_URL")
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or "generativelanguage.googleapis.com"
        except:
            domain = "generativelanguage.googleapis.com"
    cookies = []
    
    # Find Firefox profile
    profiles_dir = FIREFOX_COOKIE_PATH
    if not profiles_dir.exists():
        logger.error("Firefox profiles directory not found")
        return cookies
    
    # Find default profile
    profiles = list(profiles_dir.glob("*.default*"))
    if not profiles:
        logger.error("Firefox default profile not found")
        return cookies
    
    profile_path = profiles[0]
    cookie_db = profile_path / "cookies.sqlite"
    
    if not cookie_db.exists():
        logger.error("Firefox cookie database not found")
        return cookies
    
    try:
        conn = sqlite3.connect(cookie_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, value, host, path, expiry, isSecure, isHttpOnly
            FROM moz_cookies
            WHERE host LIKE ?
        """, (f"%{domain}%",))
        
        for row in cursor.fetchall():
            name, value, host, path, expiry, is_secure, is_httponly = row
            
            cookies.append({
                "name": name,
                "value": value,
                "domain": host,
                "path": path,
                "secure": bool(is_secure),
                "httpOnly": bool(is_httponly),
            })
        
        conn.close()
        logger.info(f"Extracted {len(cookies)} cookies from Firefox")
        
    except Exception as e:
        logger.error(f"Failed to extract Firefox cookies: {e}")
    
    return cookies


def manual_extraction_instructions():
    """Print instructions for manually extracting cookies."""
    print("\n" + "=" * 60)
    print("MANUAL COOKIE EXTRACTION INSTRUCTIONS")
    print("=" * 60)
    # Get the actual URL from obfuscated keys
    try:
        from ai_service_keys import get_service_url
        service_url = get_service_url("WEB_BASE_URL")
    except:
        # Fallback - user should know the URL
        service_url = "[service URL from keys file]"
    
    print(f"\n1. Open your browser (preferably incognito/private) and navigate to the service")
    print("2. Make sure you're logged in with your account")
    print("3. Open Developer Tools (F12 or Right-click > Inspect)")
    print("4. Go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox)")
    print("5. In the left sidebar, expand 'Cookies'")
    print("6. Click on the service domain")
    print("7. You'll see a list of cookies. Look for important ones like:")
    print("   - __Secure-1PSID")
    print("   - __Secure-1PSIDTS")
    print("   - __Secure-1PSIDCC")
    print("   - Any other cookies with 'Secure' or 'PSID' in the name")
    print("\n8. Copy the cookie values and create a JSON file like this:")
    print("\n   {")
    print('     "__Secure-1PSID": "your-cookie-value-here",')
    print('     "__Secure-1PSIDTS": "your-cookie-value-here",')
    print('     "__Secure-1PSIDCC": "your-cookie-value-here"')
    print("   }")
    print("\n9. Save it as 'webai_cookies.json' (or 'ai_service_cookies.json' for backward compatibility)")
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Extract cookies from browser for AI service")
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox", "edge", "manual"],
        default="chrome",
        help="Browser to extract cookies from"
    )
    parser.add_argument(
        "--output",
        default="webai_cookies.json",
        help="Output file for cookies (default: webai_cookies.json, saved to project root)"
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Domain to extract cookies for (default: from keys file)"
    )
    
    args = parser.parse_args()
    
    if args.browser == "manual":
        manual_extraction_instructions()
        return 0
    
    logger.info(f"Extracting cookies from {args.browser}...")
    
    cookies = []
    if args.browser in ["chrome", "edge"]:
        cookies = extract_chrome_cookies(args.domain)
    elif args.browser == "firefox":
        cookies = extract_firefox_cookies(args.domain)
    
    if not cookies:
        logger.warning("No cookies found. Trying manual extraction...")
        manual_extraction_instructions()
        return 1
    
    # Convert to simple dict format for easier use
    cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
    
    # Save to file (project root by default)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        # If relative path, save to project root
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_path.name
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cookies_dict, f, indent=2)
    
    logger.info(f"Saved {len(cookies)} cookies to {output_path}")
    logger.info(f"\nImportant cookies found:")
    for name in cookies_dict.keys():
        if any(keyword in name.lower() for keyword in ["secure", "psid", "session", "auth"]):
            logger.info(f"  - {name}")
    
    print(f"\n[OK] Cookies saved to: {output_path}")
    print(f"  You can now use them with: python web_dashboard/ai_service_client.py --cookies {output_path} --query 'Your question'")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

