#!/usr/bin/env python3
"""
Shared Navigation Component
===========================

Provides consistent navigation across all pages in the web dashboard.
Handles page links, admin status, and AI Assistant availability.
"""

import streamlit as st


def render_navigation(show_ai_assistant: bool = True, show_settings: bool = True) -> None:
    """
    Render the shared navigation sidebar component with modern card-based design.
    
    Args:
        show_ai_assistant: Whether to show AI Assistant link (default: True)
        show_settings: Whether to show Settings link (default: True)
    """
    # CRITICAL: Restore session from cookies FIRST before any preference checks
    # This ensures we have valid auth context when checking v2_enabled
    try:
        from auth_utils import ensure_session_restored
        ensure_session_restored()
    except Exception:
        pass  # Continue with navigation even if restoration fails
    
    # Apply user's theme preference (dark/light mode override)
    try:
        from user_preferences import apply_user_theme, get_user_preference, set_user_preference
        apply_user_theme()
    except Exception:
        def get_user_preference(key, default=None): return default
        def set_user_preference(*args): return False
    
    # V2 preference: Always reload from database if authenticated
    # This ensures it persists even after auth failures/redirects
    try:
        # Check if we're authenticated first
        from auth_utils import is_authenticated
        if is_authenticated():
            # Always reload from DB to get latest value (survives session resets)
            db_value = get_user_preference('v2_enabled', default=False)
            # Update session state to match DB
            st.session_state._v2_enabled = db_value
        else:
            # Not authenticated - use session state if exists, otherwise default to False
            if '_v2_enabled' not in st.session_state:
                st.session_state._v2_enabled = False
    except Exception:
        # Fallback: use session state if exists
        if '_v2_enabled' not in st.session_state:
            st.session_state._v2_enabled = False
    
    is_v2_enabled = st.session_state._v2_enabled
    
    try:
        from auth_utils import is_admin, get_user_email, get_user_id
        from streamlit_utils import get_supabase_client
    except ImportError:
        # If auth utils not available, render minimal navigation
        st.sidebar.title("Navigation")
        st.sidebar.markdown('<div class="nav-section-title">Pages</div>', unsafe_allow_html=True)
        st.sidebar.page_link("streamlit_app.py", label="Dashboard", icon="📈")
        return
    
    # Inject custom CSS for consistent navigation styling
    st.sidebar.markdown("""
        <style>
            .nav-section-title {
                color: rgba(128, 128, 128, 0.8);
                font-size: 0.75rem;
                font-weight: 600;
                margin: 1.25rem 0 0.5rem 0;
                text-transform: uppercase;
                letter-spacing: 0.05rem;
                padding-left: 0.5rem;
            }
            .v2-nav-link {
                display: flex;
                align-items: center;
                padding: 0.35rem 0.75rem;
                border-radius: 0.5rem;
                text-decoration: none;
                color: inherit;
                transition: background-color 0.15s ease;
                margin: 0.1rem 0;
                cursor: pointer;
                border: 1px solid transparent;
            }
            .v2-nav-link:hover {
                background-color: rgba(151, 166, 195, 0.1);
                border-color: rgba(128, 128, 128, 0.1);
            }
            .v2-nav-icon {
                margin-right: 0.75rem;
                font-size: 1.1rem;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 1.25rem;
                min-width: 1.25rem;
            }
            .v2-nav-label {
                font-size: 0.875rem;
                font-weight: 400;
                line-height: 1.5;
            }
            .nav-divider {
                margin: 1rem 0;
                border: none;
                border-top: 1px solid rgba(128, 128, 128, 0.2);
            }
            .nav-badge {
                padding: 0.15rem 0.5rem;
                border-radius: 0.5rem;
                font-size: 0.7rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                display: inline-block;
                width: fit-content;
            }
            .nav-badge-admin { 
                background-color: rgba(46, 204, 113, 0.15); 
                color: #2ecc71; 
                border: 1px solid rgba(46, 204, 113, 0.2); 
            }
            .nav-badge-role { 
                background-color: rgba(52, 152, 219, 0.15); 
                color: #3498db; 
                border: 1px solid rgba(52, 152, 219, 0.2); 
            }
        </style>
    """, unsafe_allow_html=True)

    # Navigation title with modern styling
    st.sidebar.title("Navigation")
    
    # Page links section with styled header
    st.sidebar.markdown('<div class="nav-section-title">Pages</div>', unsafe_allow_html=True)
    st.sidebar.page_link("streamlit_app.py", label="Dashboard", icon="📈")
    
    # Research Repository link (if PostgreSQL is available)
    try:
        from postgres_client import PostgresClient
        client = PostgresClient()
        if client.test_connection():
            st.sidebar.page_link("pages/research.py", label="Research Repository", icon="📚")
            st.sidebar.page_link("pages/social_sentiment.py", label="Social Sentiment", icon="💬")
            st.sidebar.page_link("pages/etf_holdings.py", label="ETF Holdings", icon="💼")
    except Exception:
        pass  # Silently fail if Postgres not available
    
    # Congress Trades link (if Supabase is available)
    try:
        client = get_supabase_client()
        if client and client.test_connection():
            st.sidebar.page_link("pages/congress_trades.py", label="Congress Trades", icon="🏛️")
            # Ticker Lookup - check if migrated to Flask
            try:
                from shared_navigation import is_page_migrated, get_page_url
                if is_v2_enabled and is_page_migrated('ticker_details'):
                    # Use markdown link for Flask route with matching Streamlit styling
                    ticker_url = get_page_url('ticker_details')
                    st.sidebar.markdown(f'''
                        <a href="{ticker_url}" target="_self" class="v2-nav-link">
                            <span class="v2-nav-icon">🔍</span>
                            <span class="v2-nav-label">Ticker Lookup</span>
                        </a>
                    ''', unsafe_allow_html=True)
                else:
                    st.sidebar.page_link("pages/ticker_details.py", label="Ticker Lookup", icon="🔍")
            except ImportError:
                # Fallback if shared_navigation not available
                st.sidebar.page_link("pages/ticker_details.py", label="Ticker Lookup", icon="🔍")
    except Exception:
        pass  # Silently fail if Supabase not available
    
    # AI Assistant link (if available and requested)
    if show_ai_assistant:
        try:
            from ollama_client import check_ollama_health
            
            if check_ollama_health():
                # AI Assistant emoji options:
                # 🤖 (robot - default, may be wider)
                # 🧠 (brain - good alignment)
                # 💡 (lightbulb - good alignment)
                # ⚡ (lightning - good alignment)
                # 🎯 (target - good alignment)
                # 🔮 (crystal ball - good alignment)
                # ✨ (sparkles - good alignment)
                # 🚀 (rocket - good alignment)
                # 💬 (speech bubble - good alignment)
                # 🎓 (graduation cap - good alignment)
                ai_emoji = "🧠"  # Change this to any emoji from the list above
                st.sidebar.page_link("pages/ai_assistant.py", label="AI Assistant", icon=ai_emoji)
            else:
                with st.sidebar.expander("💬 Chat Assistant", expanded=False):
                    st.warning("AI Assistant unavailable")
                    st.caption("Ollama is not running or not accessible.")
        except Exception:
            # Silently fail if Ollama check not available
            pass
    
    # Settings link (if requested)
    if show_settings:
        # Check if settings page is migrated to Flask
        try:
            from shared_navigation import is_page_migrated, get_page_url
            if is_v2_enabled and is_page_migrated('settings'):
                # Use markdown link for Flask route with matching Streamlit styling
                settings_url = get_page_url('settings')
                st.sidebar.markdown(f'''
                    <a href="{settings_url}" target="_self" class="v2-nav-link">
                        <span class="v2-nav-icon">👤</span>
                        <span class="v2-nav-label">User Preferences</span>
                    </a>
                ''', unsafe_allow_html=True)
            else:
                st.sidebar.page_link("pages/settings.py", label="User Preferences", icon="👤")
        except ImportError:
            # Fallback if shared_navigation not available
            st.sidebar.page_link("pages/settings.py", label="User Preferences", icon="👤")
    
    # Admin section (moved to end of menu)
    try:
        from auth_utils import has_admin_access
        admin_status = has_admin_access()
    except ImportError:
        admin_status = is_admin()
    user_email = get_user_email()
    
    if user_email:
        if admin_status:
            # Modern badge for admin status
            st.sidebar.markdown(
                '<div class="nav-badge nav-badge-admin">✅ Admin Access</div>',
                unsafe_allow_html=True
            )
            # Admin pages (only visible to admins)
            st.sidebar.page_link("pages/admin_scheduler.py", label="Jobs", icon="🔨")
            st.sidebar.page_link("pages/admin_users.py", label="User & Access", icon="👥")
            st.sidebar.page_link("pages/admin_funds.py", label="Fund Management", icon="🏦")
            st.sidebar.page_link("pages/admin_trade_entry.py", label="Trade Entry", icon="📈")
            st.sidebar.page_link("pages/admin_contributions.py", label="Contributions", icon="💰")
            st.sidebar.page_link("pages/admin_ai_settings.py", label="AI Settings", icon="⚙️")
            st.sidebar.page_link("pages/admin_system.py", label="System Monitoring", icon="📊")
            
            # Logs link - check if migrated to Flask
            try:
                from shared_navigation import is_page_migrated, get_page_url
                if is_v2_enabled and is_page_migrated('admin_logs'):
                    # Use markdown link for Flask route with matching Streamlit styling
                    logs_url = get_page_url('admin_logs')
                    st.sidebar.markdown(f'''
                        <a href="{logs_url}" target="_self" class="v2-nav-link">
                            <span class="v2-nav-icon">📜</span>
                            <span class="v2-nav-label">Logs</span>
                        </a>
                    ''', unsafe_allow_html=True)
                else:
                    st.sidebar.page_link("pages/admin_logs.py", label="Logs", icon="📜")
            except ImportError:
                # Fallback if shared_navigation not available
                st.sidebar.page_link("pages/admin_logs.py", label="Logs", icon="📜")
        else:
            # Check if user profile exists and show role
            try:
                client = get_supabase_client()
                if client:
                    profile_result = client.supabase.table("user_profiles").select("role").eq("user_id", get_user_id()).execute()
                    if profile_result.data:
                        role = profile_result.data[0].get('role', 'user')
                        if role == 'readonly_admin':
                            # Modern badge for readonly admin role
                            st.sidebar.markdown(
                                '<div class="nav-badge nav-badge-role">👁️ Role: Read-Only Admin</div>',
                                unsafe_allow_html=True
                            )
                        elif role != 'admin':
                            # Modern badge for user role
                            st.sidebar.markdown(
                                f'<div class="nav-badge nav-badge-role">👤 Role: {role.title()}</div>',
                                unsafe_allow_html=True
                            )
                            with st.sidebar.expander("🔧 Need Admin Access?", expanded=False):
                                st.write("To become an admin, run this command on the server:")
                                st.code("python web_dashboard/setup_admin.py", language="bash")
                                st.write(f"Then enter your email: `{user_email}`")
            except Exception:
                pass  # Silently fail if we can't check
    
    # Modern divider
    st.sidebar.markdown('<hr class="nav-divider">', unsafe_allow_html=True)

    # V2 Beta Toggle - uses session state as source of truth
    v2_current = st.sidebar.toggle(
        "🚀 Try v2 Beta", 
        value=st.session_state._v2_enabled,
        key="v2_beta_toggle",
        help="Enable new Flask-based pages (faster, better UI)"
    )
    
    # Save when value changes
    if v2_current != st.session_state._v2_enabled:
        st.session_state._v2_enabled = v2_current  # Update session state IMMEDIATELY
        try:
            from user_preferences import set_user_preference
            set_user_preference('v2_enabled', v2_current)  # Save to DB for persistence across sessions
        except Exception:
            pass  # Session state is already updated, DB save is best-effort
        st.rerun()  # Rerun to update navigation links with new preference

