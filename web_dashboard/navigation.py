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
    # Apply user's theme preference (dark/light mode override)
    try:
        from user_preferences import apply_user_theme
        apply_user_theme()
    except Exception:
        pass  # Silently fail if theme can't be applied
    
    try:
        from auth_utils import is_admin, get_user_email, get_user_id
        from streamlit_utils import get_supabase_client
    except ImportError:
        # If auth utils not available, render minimal navigation
        st.sidebar.title("Navigation")
        st.sidebar.markdown('<div class="nav-section-title">Pages</div>', unsafe_allow_html=True)
        st.sidebar.page_link("streamlit_app.py", label="Dashboard", icon="📈")
        return
    
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
            # Ticker Lookup - always available if we have database access
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
            if is_page_migrated('settings'):
                # Use markdown link for Flask route (opens in same window)
                settings_url = get_page_url('settings')
                st.sidebar.markdown(f'<a href="{settings_url}" target="_self" style="text-decoration: none; color: inherit;">👤 User Preferences</a>', unsafe_allow_html=True)
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
                if is_page_migrated('admin_logs'):
                    # Use markdown link for Flask route
                    logs_url = get_page_url('admin_logs')
                    st.sidebar.markdown(f'<a href="{logs_url}" target="_self" style="text-decoration: none; color: inherit;">📜 Logs</a>', unsafe_allow_html=True)
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

