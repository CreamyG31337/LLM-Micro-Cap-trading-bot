#!/usr/bin/env python3
"""
Cookie Refresher Service
========================

Automatically refreshes WebAI cookies using a headless browser.
Runs as a sidecar container that stays running independently of the main app.

This service:
1. Periodically checks if cookies need refreshing
2. Uses Playwright to visit the web AI service with existing cookies
3. Extracts fresh cookies (especially __Secure-1PSIDTS which expires frequently)
4. Writes cookies to a shared volume for the main app to use
"""

import sys
import json
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

try:
    from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("[ERROR] Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REFRESH_INTERVAL = int(os.getenv("COOKIE_REFRESH_INTERVAL", "3600"))  # 1 hour default
COOKIE_OUTPUT_FILE = os.getenv("COOKIE_OUTPUT_FILE", "/shared/cookies/webai_cookies.json")
COOKIE_INPUT_FILE = os.getenv("COOKIE_INPUT_FILE", "/shared/cookies/webai_cookies.json")  # Read existing cookies
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds


def get_service_url() -> str:
    """Get the web AI service URL from environment variable or obfuscated keys."""
    # Try environment variable first (for Docker containers)
    env_url = os.getenv("AI_SERVICE_WEB_URL")
    if env_url:
        return env_url
    
    # Try obfuscated keys file (for local development)
    try:
        from ai_service_keys import get_service_url
        return get_service_url("WEB_BASE_URL")
    except (ImportError, FileNotFoundError, KeyError) as e:
        logger.warning(f"Could not load obfuscated URL: {e}")
        # Fallback (should not be used in production)
        return "https://webai.google.com/app"


def load_existing_cookies() -> Optional[Dict[str, str]]:
    """Load existing cookies from the shared volume."""
    cookie_path = Path(COOKIE_INPUT_FILE)
    
    if not cookie_path.exists():
        logger.warning(f"Cookie file not found: {cookie_path}")
        return None
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        if not isinstance(cookies, dict):
            logger.error(f"Invalid cookie file format: expected dict, got {type(cookies)}")
            return None
        
        logger.info(f"Loaded existing cookies from {cookie_path}")
        return cookies
    except Exception as e:
        logger.error(f"Failed to load existing cookies: {e}")
        return None


def save_cookies(cookies: Dict[str, str]) -> bool:
    """Save cookies to the shared volume."""
    cookie_path = Path(COOKIE_OUTPUT_FILE)
    
    # Ensure directory exists
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Only save the cookies we need
        output = {
            "__Secure-1PSID": cookies.get("__Secure-1PSID", ""),
            "__Secure-1PSIDTS": cookies.get("__Secure-1PSIDTS", ""),
        }
        
        # Remove empty values
        output = {k: v for k, v in output.items() if v}
        
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved cookies to {cookie_path}")
        logger.info(f"  __Secure-1PSID: {output.get('__Secure-1PSID', 'MISSING')[:50]}...")
        logger.info(f"  __Secure-1PSIDTS: {output.get('__Secure-1PSIDTS', 'MISSING')[:50] if output.get('__Secure-1PSIDTS') else 'MISSING'}...")
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False


def refresh_cookies_with_browser(existing_cookies: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Use Playwright to refresh cookies by visiting the web AI service.
    
    Args:
        existing_cookies: Existing cookies to use for authentication
        
    Returns:
        Dictionary of refreshed cookies, or None if failed
    """
    service_url = get_service_url()
    logger.info(f"Refreshing cookies by visiting {service_url}")
    
    with sync_playwright() as p:
        try:
            # Launch browser in headless mode
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']  # Required for Docker
            )
            
            # Create context with existing cookies if available
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            context = browser.new_context(**context_options)
            
            # Add existing cookies if we have them
            if existing_cookies:
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed = urlparse(service_url)
                domain = parsed.netloc
                
                # Add cookies to context
                cookie_list = []
                for name, value in existing_cookies.items():
                    if name.startswith("__Secure-") or "PSID" in name:
                        cookie_list.append({
                            "name": name,
                            "value": value,
                            "domain": domain,
                            "path": "/",
                            "secure": True,
                            "httpOnly": True,
                            "sameSite": "Lax"
                        })
                
                if cookie_list:
                    context.add_cookies(cookie_list)
                    logger.info(f"Added {len(cookie_list)} existing cookies to browser context")
            
            # Create page and navigate
            page = context.new_page()
            
            logger.info(f"Navigating to {service_url}...")
            try:
                page.goto(service_url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeout:
                logger.warning("Navigation timeout, but continuing...")
                # Wait a bit for page to load
                time.sleep(3)
            
            # Wait for page to fully load and cookies to be set
            logger.info("Waiting for page to load and cookies to be set...")
            time.sleep(5)
            
            # Extract all cookies from the context
            all_cookies = context.cookies()
            logger.info(f"Extracted {len(all_cookies)} cookies from browser")
            
            # Convert to dictionary format
            cookies_dict = {}
            for cookie in all_cookies:
                cookies_dict[cookie["name"]] = cookie["value"]
            
            # Check if we got the required cookies
            if "__Secure-1PSID" not in cookies_dict:
                logger.error("Failed to get __Secure-1PSID cookie")
                browser.close()
                return None
            
            if "__Secure-1PSIDTS" not in cookies_dict:
                logger.warning("__Secure-1PSIDTS not found - may need manual login")
                # Continue anyway, as __Secure-1PSID might be enough
            
            browser.close()
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Error refreshing cookies: {e}")
            import traceback
            traceback.print_exc()
            return None


def refresh_cookies() -> bool:
    """
    Main function to refresh cookies.
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting cookie refresh...")
    
    # Load existing cookies
    existing_cookies = load_existing_cookies()
    
    if not existing_cookies:
        logger.error("No existing cookies found. Cannot refresh without initial cookies.")
        logger.error("Please set initial cookies manually or via Woodpecker secret.")
        return False
    
    # Try to refresh with browser
    for attempt in range(MAX_RETRIES):
        logger.info(f"Refresh attempt {attempt + 1}/{MAX_RETRIES}")
        
        refreshed_cookies = refresh_cookies_with_browser(existing_cookies)
        
        if refreshed_cookies:
            # Save the refreshed cookies
            if save_cookies(refreshed_cookies):
                logger.info("Cookie refresh successful!")
                return True
            else:
                logger.error("Failed to save refreshed cookies")
                return False
        else:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Refresh failed, retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("All refresh attempts failed")
                return False
    
    return False


def main():
    """Main loop - runs continuously, refreshing cookies periodically."""
    logger.info("Cookie Refresher Service starting...")
    logger.info(f"  Refresh interval: {REFRESH_INTERVAL} seconds")
    logger.info(f"  Cookie output: {COOKIE_OUTPUT_FILE}")
    logger.info(f"  Cookie input: {COOKIE_INPUT_FILE}")
    
    if not HAS_PLAYWRIGHT:
        logger.error("Playwright not available. Exiting.")
        sys.exit(1)
    
    # Initial refresh on startup
    logger.info("Performing initial cookie refresh...")
    refresh_cookies()
    
    # Main loop
    while True:
        try:
            logger.info(f"Sleeping for {REFRESH_INTERVAL} seconds until next refresh...")
            time.sleep(REFRESH_INTERVAL)
            
            logger.info("Starting scheduled cookie refresh...")
            refresh_cookies()
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, exiting...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            import traceback
            traceback.print_exc()
            # Continue running despite errors
            time.sleep(60)  # Wait a bit before retrying


if __name__ == "__main__":
    main()

