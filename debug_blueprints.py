
import sys
import os
from unittest.mock import MagicMock, patch

# Add web_dashboard to path
sys.path.append(os.path.abspath('web_dashboard'))

# Mock dependencies
with patch('supabase_client.SupabaseClient'), \
     patch('auth.auth_manager'), \
     patch('flask_caching.Cache'), \
     patch('log_handler.setup_logging'):
    
    try:
        print("Attempting to import dashboard_routes...")
        from routes import dashboard_routes
        print("dashboard_routes imported successfully")
        from app import app
        print("Blueprints:", app.blueprints.keys())
        print("URL Map rules for dashboard:", [r for r in app.url_map.iter_rules() if 'dashboard' in str(r)])
    except Exception as e:
        print("Error importing app:", e)
        import traceback
        traceback.print_exc()
