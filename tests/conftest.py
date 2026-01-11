import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add web_dashboard to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web_dashboard')))

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Mock Supabase dependencies before importing app to prevent connection attempts
    with patch('supabase_client.SupabaseClient'), \
         patch('auth.auth_manager'), \
         patch('flask_caching.Cache'), \
         patch('log_handler.setup_logging'):
        
        from app import app
        
        app.config.update({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
            "DEBUG": False
        })

        yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()
