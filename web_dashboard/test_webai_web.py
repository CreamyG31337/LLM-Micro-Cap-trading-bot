#!/usr/bin/env python3
"""
Test Gemini Web Interface Access
=================================

Explores different methods to interact with Google Gemini's web interface
without using the official API.

Methods tested:
1. Direct HTTP POST requests (reverse-engineering API calls)
2. Selenium browser automation
3. Playwright browser automation (alternative)

Usage:
    python web_dashboard/test_gemini_web.py [--method METHOD] [--query "your query"]
"""

import sys
import os
import time
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GEMINI_URL = "https://gemini.google.com"


def method_http_post(query: str) -> Optional[str]:
    """
    Attempt to interact with Gemini using direct HTTP POST requests.
    
    This method tries to reverse-engineer Gemini's API endpoints by:
    1. Fetching the main page to get authentication tokens
    2. Extracting API endpoints from JavaScript
    3. Making POST requests to those endpoints
    
    Note: This is likely to fail because Gemini uses complex authentication
    and may require browser cookies, CSRF tokens, and other security measures.
    """
    logger.info("Attempting HTTP POST method...")
    
    session = requests.Session()
    
    # Set browser-like headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        # Step 1: Fetch the main page to get cookies and tokens
        logger.info(f"Fetching {GEMINI_URL}...")
        response = session.get(GEMINI_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Cookies: {dict(session.cookies)}")
        
        # Step 2: Try to find API endpoints in the HTML/JavaScript
        # Gemini likely uses internal API endpoints that we'd need to discover
        # This is where it gets tricky - we'd need to:
        # - Parse JavaScript bundles
        # - Find API endpoint patterns
        # - Extract authentication tokens
        
        # For now, let's try a common pattern: /api/chat or similar
        api_endpoints = [
            "/api/chat",
            "/api/generate",
            "/api/query",
            "/_/api/chat",
            "/_/api/generate",
        ]
        
        for endpoint in api_endpoints:
            try:
                api_url = f"{GEMINI_URL}{endpoint}"
                logger.info(f"Trying endpoint: {api_url}")
                
                # Try a POST request with the query
                payload = {
                    "query": query,
                    "prompt": query,
                    "message": query,
                }
                
                response = session.post(
                    api_url,
                    json=payload,
                    headers={
                        **headers,
                        "Content-Type": "application/json",
                        "Referer": GEMINI_URL,
                    },
                    timeout=30
                )
                
                logger.info(f"Response status: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"Success! Response: {response.text[:200]}")
                    return response.text
                else:
                    logger.info(f"Failed: {response.text[:200]}")
                    
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
                continue
        
        logger.warning("HTTP POST method failed - Gemini likely requires browser-based authentication")
        return None
        
    except Exception as e:
        logger.error(f"HTTP POST method error: {e}")
        return None


def method_selenium(query: str, headless: bool = True) -> Optional[str]:
    """
    Interact with Gemini using Selenium browser automation.
    
    This method:
    1. Opens a browser (Chrome/Firefox)
    2. Navigates to Gemini
    3. Finds the input field
    4. Enters the query
    5. Submits and waits for response
    6. Extracts the response text
    
    Requires: pip install selenium
    Also requires: ChromeDriver or GeckoDriver installed
    """
    logger.info("Attempting Selenium method...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        logger.error("Selenium not installed. Install with: pip install selenium")
        logger.info("Also install ChromeDriver: https://chromedriver.chromium.org/")
        return None
    
    driver = None
    try:
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        logger.info("Starting Chrome browser...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to Gemini
        logger.info(f"Navigating to {GEMINI_URL}...")
        driver.get(GEMINI_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        # Try to find the input field
        # Gemini's interface may have different selectors - we'll try common ones
        input_selectors = [
            "textarea",
            "input[type='text']",
            "[contenteditable='true']",
            ".input",
            "#input",
            "[data-testid='input']",
        ]
        
        input_element = None
        for selector in input_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                input_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if input_element and input_element.is_displayed():
                    logger.info(f"Found input with selector: {selector}")
                    break
            except:
                continue
        
        if not input_element:
            logger.error("Could not find input field. Page structure may have changed.")
            logger.info("Taking screenshot for debugging...")
            driver.save_screenshot("gemini_debug.png")
            logger.info("Screenshot saved as gemini_debug.png")
            return None
        
        # Enter the query
        logger.info(f"Entering query: {query[:50]}...")
        input_element.clear()
        input_element.send_keys(query)
        time.sleep(1)
        
        # Submit (try Enter key or find submit button)
        input_element.send_keys(Keys.RETURN)
        logger.info("Query submitted, waiting for response...")
        
        # Wait for response (look for response elements)
        time.sleep(5)  # Give it time to generate
        
        # Try to find the response
        response_selectors = [
            ".response",
            ".output",
            "[data-testid='response']",
            ".message",
            ".content",
        ]
        
        response_text = None
        for selector in response_selectors:
            try:
                response_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if response_elements:
                    response_text = response_elements[-1].text  # Get last response
                    if response_text:
                        logger.info(f"Found response with selector: {selector}")
                        break
            except:
                continue
        
        if not response_text:
            # Fallback: get all text from page
            logger.warning("Could not find response element, extracting page text...")
            response_text = driver.find_element(By.TAG_NAME, "body").text
        
        logger.info(f"Response length: {len(response_text)} characters")
        return response_text
        
    except Exception as e:
        logger.error(f"Selenium method error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")


def method_playwright(query: str, headless: bool = True) -> Optional[str]:
    """
    Interact with Gemini using Playwright browser automation.
    
    Playwright is often more reliable than Selenium for modern web apps.
    
    Requires: pip install playwright
    Also requires: playwright install chromium
    """
    logger.info("Attempting Playwright method...")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Install with: pip install playwright")
        logger.info("Then run: playwright install chromium")
        return None
    
    try:
        with sync_playwright() as p:
            logger.info("Starting browser...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            logger.info(f"Navigating to {GEMINI_URL}...")
            page.goto(GEMINI_URL, wait_until="networkidle")
            
            # Wait a bit for page to fully load
            page.wait_for_timeout(3000)
            
            # Try to find and fill the input
            input_selectors = [
                "textarea",
                "input[type='text']",
                "[contenteditable='true']",
            ]
            
            input_found = False
            for selector in input_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        logger.info(f"Found input with selector: {selector}")
                        element.fill(query)
                        element.press("Enter")
                        input_found = True
                        break
                except:
                    continue
            
            if not input_found:
                logger.error("Could not find input field")
                page.screenshot(path="gemini_playwright_debug.png")
                browser.close()
                return None
            
            logger.info("Query submitted, waiting for response...")
            page.wait_for_timeout(5000)  # Wait for response
            
            # Try to get response
            response_text = None
            response_selectors = [
                ".response",
                ".output",
                "[data-testid='response']",
            ]
            
            for selector in response_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        response_text = element.inner_text()
                        if response_text:
                            break
                except:
                    continue
            
            if not response_text:
                # Fallback
                response_text = page.inner_text("body")
            
            browser.close()
            logger.info(f"Response length: {len(response_text)} characters")
            return response_text
            
    except Exception as e:
        logger.error(f"Playwright method error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Test Gemini web interface access methods")
    parser.add_argument(
        "--method",
        choices=["http", "selenium", "playwright", "all"],
        default="all",
        help="Method to test (default: all)"
    )
    parser.add_argument(
        "--query",
        default="What is Python?",
        help="Query to send to Gemini (default: 'What is Python?')"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Gemini Web Interface Test")
    logger.info("=" * 60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Method: {args.method}")
    logger.info("")
    
    results = {}
    
    if args.method in ["http", "all"]:
        logger.info("\n" + "=" * 60)
        logger.info("Testing HTTP POST Method")
        logger.info("=" * 60)
        result = method_http_post(args.query)
        results["http"] = result
        logger.info("")
    
    if args.method in ["selenium", "all"]:
        logger.info("\n" + "=" * 60)
        logger.info("Testing Selenium Method")
        logger.info("=" * 60)
        result = method_selenium(args.query, headless=args.headless)
        results["selenium"] = result
        logger.info("")
    
    if args.method in ["playwright", "all"]:
        logger.info("\n" + "=" * 60)
        logger.info("Testing Playwright Method")
        logger.info("=" * 60)
        result = method_playwright(args.query, headless=args.headless)
        results["playwright"] = result
        logger.info("")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    for method, result in results.items():
        status = "✓ Success" if result else "✗ Failed"
        logger.info(f"{method.upper():12} : {status}")
        if result:
            logger.info(f"  Response preview: {result[:100]}...")
    
    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

