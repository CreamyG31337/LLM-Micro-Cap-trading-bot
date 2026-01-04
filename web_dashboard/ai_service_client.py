#!/usr/bin/env python3
"""
AI Service Cookie-Based Client
===============================

Uses browser cookies to authenticate with AI service web interface.
This allows you to use your Pro account without API access.

Usage:
    1. Extract cookies from your browser (see extract_ai_cookies.py)
    2. Save cookies to a JSON file
    3. Use this client to interact with the service

Example:
    from ai_service_client import AIServiceClient
    
    client = AIServiceClient(cookies_file="ai_service_cookies.json")
    response = client.query("What is Python?")
    print(response)
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load obfuscated URLs
try:
    from ai_service_keys import get_service_url
    BASE_URL = get_service_url("WEB_BASE_URL")
    API_BASE = get_service_url("BASE_URL")
except (ImportError, FileNotFoundError, KeyError) as e:
    logger.warning(f"Could not load obfuscated URLs: {e}")
    # Fallback (should not be used in production)
    BASE_URL = "https://generativelanguage.googleapis.com"
    API_BASE = "https://generativelanguage.googleapis.com"


class AIServiceClient:
    """Client for interacting with AI service web interface using browser cookies."""
    
    def __init__(self, cookies_file: Optional[str] = None, cookies_dict: Optional[Dict] = None):
        """
        Initialize the client with cookies.
        
        Args:
            cookies_file: Path to JSON file containing cookies
            cookies_dict: Dictionary of cookies (alternative to file)
        """
        self.session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": BASE_URL,
            "Origin": BASE_URL,
        })
        
        # Load cookies
        if cookies_file:
            self.load_cookies_from_file(cookies_file)
        elif cookies_dict:
            self.load_cookies_from_dict(cookies_dict)
        else:
            logger.warning("No cookies provided. Authentication may fail.")
    
    def load_cookies_from_file(self, cookies_file: str) -> None:
        """Load cookies from a JSON file."""
        # If relative path, try both project root and web_dashboard
        cookie_path = Path(cookies_file)
        if not cookie_path.is_absolute():
            # Try project root first
            project_root = Path(__file__).parent.parent
            root_cookie = project_root / cookies_file
            web_cookie = Path(__file__).parent / cookies_file
            
            if root_cookie.exists():
                cookie_path = root_cookie
            elif web_cookie.exists():
                cookie_path = web_cookie
            else:
                # If neither exists, use the original path (will fail with clear error)
                cookie_path = Path(cookies_file)
        
        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            if isinstance(cookies_data, list):
                # Format: [{"name": "...", "value": "...", "domain": "..."}, ...]
                for cookie in cookies_data:
                    self.session.cookies.set(
                        cookie.get("name"),
                        cookie.get("value"),
                        domain=cookie.get("domain", ".google.com")
                    )
            elif isinstance(cookies_data, dict):
                # Format: {"cookie_name": "cookie_value", ...}
                for name, value in cookies_data.items():
                    self.session.cookies.set(name, value, domain=".google.com")
            
            logger.info(f"Loaded cookies from {cookie_path}")
            
        except Exception as e:
            logger.error(f"Failed to load cookies from {cookie_path}: {e}")
            raise
    
    def load_cookies_from_dict(self, cookies_dict: Dict[str, str]) -> None:
        """Load cookies from a dictionary."""
        for name, value in cookies_dict.items():
            self.session.cookies.set(name, value, domain=".google.com")
        logger.info(f"Loaded {len(cookies_dict)} cookies from dictionary")
    
    def _discover_api_endpoint(self) -> Optional[str]:
        """
        Try to discover the API endpoint by inspecting the main page.
        
        The web interface is a single-page app that uses internal endpoints.
        We need to extract these from the JavaScript bundles.
        
        Returns:
            API endpoint URL if found, None otherwise
        """
        try:
            logger.info("Fetching main page to discover API endpoint...")
            response = self.session.get(BASE_URL, timeout=30)
            response.raise_for_status()
            
            # Look for API endpoints in the HTML/JavaScript
            # The web interface embeds API URLs in script tags or data attributes
            content = response.text
            
            # Common patterns to look for in the web interface
            import re
            patterns = [
                # Look for generativelanguage API endpoints
                r'["\']([^"\']*generativelanguage[^"\']*v1beta[^"\']*)["\']',
                r'["\']([^"\']*generativelanguage[^"\']*v1[^"\']*)["\']',
                # Look for generateContent endpoints
                r'["\']([^"\']*generateContent[^"\']*)["\']',
                # Look for chat API endpoints
                r'["\']([^"\']*chat[^"\']*api[^"\']*)["\']',
                r'["\']([^"\']*api[^"\']*chat[^"\']*)["\']',
                # Look for any API endpoint patterns
                r'https://[^"\']*generativelanguage[^"\']*',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Filter out relative URLs and get full URLs
                    for match in matches:
                        if match.startswith('http'):
                            logger.info(f"Found potential API endpoint: {match}")
                            return match
                        elif match.startswith('/'):
                            # Construct full URL
                            full_url = f"https://generativelanguage.googleapis.com{match}"
                            logger.info(f"Found potential API endpoint: {full_url}")
                            return full_url
            
            # Also check for WebSocket endpoints or streaming endpoints
            ws_patterns = [
                r'wss://[^"\']*generativelanguage[^"\']*',
                r'ws://[^"\']*generativelanguage[^"\']*',
            ]
            
            for pattern in ws_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    logger.info(f"Found WebSocket endpoint: {matches[0]}")
                    # Note: WebSocket would need different handling
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover API endpoint: {e}")
            return None
    
    def query(self, prompt: str, model: Optional[str] = None) -> Optional[str]:
        """
        Send a query to the AI service and get the response.
        
        Args:
            prompt: The query/prompt to send
            model: Model to use (default: from keys file)
            
        Returns:
            Response text if successful, None otherwise
        """
        # Get model name from keys file if not provided
        if model is None:
            try:
                from ai_service_keys import get_service_url
                model = get_service_url("MODEL_NAME")
            except:
                model = "default-model"  # Fallback
        
        # Get API paths from keys file
        try:
            from ai_service_keys import get_service_url
            api_v1beta = get_service_url("API_V1BETA")
            api_v1 = get_service_url("API_V1")
            generate_endpoint = get_service_url("GENERATE_ENDPOINT")
        except:
            api_v1beta = "/v1beta/models"
            api_v1 = "/v1/models"
            generate_endpoint = ":generateContent"
        
        # Try multiple endpoint patterns
        # Since Pro accounts don't have API access, we need to use web interface endpoints
        # These endpoints work with cookies, not API keys
        # The web interface uses internal API endpoints that are proxied through the web app
        api_endpoints = [
            # Web interface internal API endpoints (work with cookies)
            f"{BASE_URL}/_/api/generativelanguage/v1beta/models/{model}{generate_endpoint}",
            f"{BASE_URL}/_/api/generativelanguage/v1/models/{model}{generate_endpoint}",
            # Alternative web interface endpoints
            f"{BASE_URL}/api/generate",
            f"{BASE_URL}/_/api/chat",
            f"{BASE_URL}/_/api/stream",
            # Direct API endpoints (will fail without API key, but try as last resort)
            f"{API_BASE}{api_v1beta}/{model}{generate_endpoint}",
            f"{API_BASE}{api_v1}/{model}{generate_endpoint}",
        ]
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        for endpoint in api_endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                
                # Update headers for API request
                # The web interface may need specific headers
                headers = {
                    **self.session.headers,
                    "Content-Type": "application/json",
                }
                
                # For web interface endpoints, add referer
                if "_/api" in endpoint or BASE_URL in endpoint:
                    headers["Referer"] = f"{BASE_URL}/"
                    headers["X-Goog-AuthUser"] = "0"  # May be needed for some endpoints
                
                response = self.session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract response text from various possible response formats
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                    
                    # Fallback: return full response for debugging
                    logger.info(f"Response structure: {json.dumps(data, indent=2)[:500]}")
                    return response.text
                
                elif response.status_code == 401:
                    logger.error("Authentication failed. Check your cookies.")
                    return None
                elif response.status_code == 403:
                    # 403 might mean API key required (Pro accounts don't have API access)
                    # Continue to try other endpoints
                    logger.debug(f"403 Forbidden on {endpoint} - may require API key (trying next endpoint)")
                    continue
                else:
                    logger.warning(f"Unexpected status {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
                continue
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON response: {e}")
                continue
        
        # If all API endpoints fail, try to discover endpoints from the web page
        logger.info("Standard endpoints failed, trying to discover endpoints from web page...")
        discovered_endpoint = self._discover_api_endpoint()
        
        if discovered_endpoint:
            logger.info(f"Trying discovered endpoint: {discovered_endpoint}")
            try:
                response = self.session.post(
                    discovered_endpoint,
                    json=payload,
                    headers={
                        **self.session.headers,
                        "Content-Type": "application/json",
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
            except Exception as e:
                logger.debug(f"Discovered endpoint failed: {e}")
        
        # Last resort: try the web interface approach
        logger.info("Trying web interface approach...")
        return self._query_via_web_interface(prompt)
    
    def _query_via_web_interface(self, prompt: str) -> Optional[str]:
        """
        Alternative method: interact with the web interface directly.
        
        Note: The web interface is a single-page app that doesn't expose
        REST endpoints. This would require browser automation (Selenium/Playwright)
        to interact with the JavaScript interface.
        
        For now, this is a placeholder. Use browser automation for actual interaction.
        """
        logger.warning("Web interface requires browser automation (Selenium/Playwright)")
        logger.warning("Direct HTTP requests don't work with the single-page app")
        logger.info("Consider using the browser automation methods in test_ai_web.py")
        return None
    
    def test_authentication(self) -> bool:
        """
        Test if the cookies are valid.
        
        Since Pro accounts don't have API access, we can't test via API.
        We'll just verify cookies are loaded and proceed.
        
        Returns:
            True if cookies are loaded, False otherwise
        """
        # Check if we have cookies loaded
        if len(self.session.cookies) == 0:
            logger.warning("No cookies loaded - authentication will likely fail")
            return False
        
        # Check for the critical cookie
        has_psid = any("PSID" in str(cookie) for cookie in self.session.cookies)
        if not has_psid:
            logger.warning("No PSID cookie found - authentication may fail")
            return False
        
        logger.info(f"Authentication test: Cookies loaded ({len(self.session.cookies)} cookies)")
        logger.info("Note: Pro accounts don't have API access - will use web interface endpoints")
        return True


def main():
    """CLI interface for the AI service cookie client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Query AI service using browser cookies")
    parser.add_argument(
        "--cookies",
        required=True,
        help="Path to JSON file containing cookies"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Query to send to the service"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test authentication only"
    )
    
    args = parser.parse_args()
    
    # Initialize client
    client = AIServiceClient(cookies_file=args.cookies)
    
    # Test authentication
    if not client.test_authentication():
        logger.error("Authentication failed. Please check your cookies.")
        return 1
    
    if args.test:
        logger.info("Authentication test passed!")
        return 0
    
    # Send query
    logger.info(f"Sending query: {args.query}")
    response = client.query(args.query)
    
    if response:
        print("\n" + "=" * 60)
        print("RESPONSE:")
        print("=" * 60)
        print(response)
        print("=" * 60)
        return 0
    else:
        logger.error("Failed to get response from AI service")
        return 1


if __name__ == "__main__":
    sys.exit(main())

