#!/usr/bin/env python3
"""
AI Service Helper for Console App
==================================

Simple helper to use AI service from the console trading app.

Uses cookie-based authentication for web AI service access.
"""

import sys
from pathlib import Path

# Add web_dashboard to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Use cookie-based web API wrapper
try:
    from webai_wrapper import query_webai, WebAIClient
    USE_WEBAPI = True
    AIServiceClient = None  # Not needed when using webapi
except ImportError:
    # Fallback to custom client
    from ai_service_client import AIServiceClient
    USE_WEBAPI = False


def get_ai_service_client():
    """
    Get an AI service client instance, automatically finding the cookie file.
    
    Returns:
        AIServiceClient instance
        
    Raises:
        FileNotFoundError: If cookie file not found
    """
    # Try project root first, then web_dashboard
    # Support multiple cookie file names for backward compatibility
    cookie_names = [
        "webai_cookies.json",  # Primary name
        "ai_service_cookies.json",
    ]
    
    for name in cookie_names:
        root_cookie = project_root / name
        web_cookie = project_root / "web_dashboard" / name
        for cookie_file in [root_cookie, web_cookie]:
            if cookie_file.exists():
                return AIServiceClient(cookies_file=str(cookie_file))
    
    raise FileNotFoundError(
        f"Cookie file not found. Checked:\n"
        f"  - {project_root / 'webai_cookies.json'}\n"
        f"  - {project_root / 'ai_service_cookies.json'}\n"
        f"\nExtract cookies with: python web_dashboard/extract_ai_cookies.py --browser manual"
    )


def query_ai_service(prompt: str, auto_refresh: bool = False) -> str:
    """
    Simple function to query the AI service.
    
    Uses cookie-based web API wrapper if available, otherwise falls back
    to custom client.
    
    Args:
        prompt: The query/prompt to send
        auto_refresh: Whether to automatically refresh cookies (default: False)
                     Note: Enabling this may cause browser sessions to be invalidated
        
    Returns:
        Response text from the service
        
    Raises:
        FileNotFoundError: If cookie file not found
        RuntimeError: If query fails
        ImportError: If required package not installed
    """
    if USE_WEBAPI:
        # Use cookie-based web API wrapper
        try:
            return query_webai(prompt, auto_refresh=auto_refresh)
        except ImportError:
            raise ImportError(
                "Required package not installed. Install with: pip install gemini-webapi\n"
                "Or use the custom client (may require browser automation)"
            )
    else:
        # Fallback to custom client
        client = get_ai_service_client()
        
        # Test authentication first
        if not client.test_authentication():
            raise RuntimeError("Authentication failed. Your cookies may have expired.")
        
        response = client.query(prompt)
        if not response:
            raise RuntimeError("Failed to get response from AI service")
        
        return response




if __name__ == "__main__":
    # Simple test
    if len(sys.argv) < 2:
        print("Usage: python ai_service_helper.py 'Your query here'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    try:
        response = query_ai_service(query)
        print("\n" + "=" * 60)
        print("AI SERVICE RESPONSE:")
        print("=" * 60)
        print(response)
        print("=" * 60)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

