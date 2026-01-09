#!/usr/bin/env python3
"""
Shared Navigation Component
============================

Provides navigation that works in both Flask and Streamlit contexts.
Tracks which pages have been migrated to Flask.
"""

# Registry of migrated pages (Flask routes)
# NOTE: Caddy reverse proxy handles routing:
#   - /v2/* → Flask (port 5001) - All new Flask pages under /v2 prefix
#   - /api/* → Flask (port 5001) - API endpoints
#   - everything else → Streamlit (port 8501)
MIGRATED_PAGES = {
    'settings': '/v2/settings',  # Routed to Flask via Caddy /v2/* handler
    'admin_logs': '/v2/logs',    # Admin logs viewer
    'ticker_details': '/v2/ticker',  # Ticker details page
    'research': '/v2/research',     # Research Repository page
}



def is_page_migrated(page_name: str) -> bool:
    """Check if a page has been migrated to Flask"""
    return page_name in MIGRATED_PAGES


def get_page_url(page_name: str) -> str:
    """Get the URL for a page (Flask route if migrated, Streamlit route otherwise)"""
    if is_page_migrated(page_name):
        return MIGRATED_PAGES[page_name]
    else:
        # Streamlit page route
        if page_name == 'dashboard':
            return '/'
        else:
            return f'/pages/{page_name}.py'


def get_navigation_links() -> list:
    """Get list of navigation links with their URLs"""
    links = [
        {'name': 'Dashboard', 'page': 'dashboard', 'icon': '📈'},
        {'name': 'Research Repository', 'page': 'research', 'icon': '📚'},
        {'name': 'Social Sentiment', 'page': 'social_sentiment', 'icon': '💬'},
        {'name': 'ETF Holdings', 'page': 'etf_holdings', 'icon': '💼'},
        {'name': 'Congress Trades', 'page': 'congress_trades', 'icon': '🏛️'},
        {'name': 'Ticker Lookup', 'page': 'ticker_details', 'icon': '🔍'},
        {'name': 'AI Assistant', 'page': 'ai_assistant', 'icon': '🧠'},
        {'name': 'User Preferences', 'page': 'settings', 'icon': '👤'},
    ]
    
    # Add URLs based on migration status
    for link in links:
        link['url'] = get_page_url(link['page'])
        link['is_migrated'] = is_page_migrated(link['page'])
    
    return links
