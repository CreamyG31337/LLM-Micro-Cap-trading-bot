
"""
Shared navigation configuration for both Streamlit and Flask.
"""

# MIGRATED_PAGES dictionary maps Streamlit page keys to Flask URLs.
# Pages that have been migrated to Flask should be added here.
MIGRATED_PAGES = {
    'dashboard': '/dashboard',
    'settings': '/v2/settings',  # Routed to Flask via Caddy /v2/* handler
    'admin_funds': '/v2/admin/funds',
    'admin_logs': '/v2/logs',
    'admin_users': '/v2/admin/users',
    'admin_scheduler': '/v2/admin/scheduler',
    'admin_trade_entry': '/v2/admin/trade-entry',
    'admin_contributions': '/v2/admin/contributions',
    'admin_ai_settings': '/v2/admin/ai-settings',
    'admin_system': '/v2/admin/system',
}

def is_page_migrated(page_key: str) -> bool:
    """Check if a page has been migrated to Flask."""
    return page_key in MIGRATED_PAGES

def get_page_url(page_key: str) -> str:
    """Get the Flask URL for a migrated page."""
    return MIGRATED_PAGES.get(page_key, '#')

# Menu structure matching shared_utils/navigation.py
# Updated to match new URLs
NAVIGATION_STRUCTURE = {
    # ... (rest of the structure if used by other components)
}
