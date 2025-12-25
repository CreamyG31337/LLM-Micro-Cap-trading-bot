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
    Render the shared navigation sidebar component.
    
    Args:
        show_ai_assistant: Whether to show AI Assistant link (default: True)
        show_settings: Whether to show Settings link (default: True)
    """
    try:
        from auth_utils import is_admin, get_user_email, get_user_id
        from streamlit_utils import get_supabase_client
    except ImportError:
        # If auth utils not available, render minimal navigation
        st.sidebar.title("Navigation")
        st.sidebar.markdown("### Pages")
        st.sidebar.page_link("streamlit_app.py", label="Dashboard", icon="📈")
        return
    
    # Navigation title
    st.sidebar.title("Navigation")
    
    # Page links
    st.sidebar.markdown("### Pages")
    st.sidebar.page_link("streamlit_app.py", label="Dashboard", icon="📈")
    
    # Show admin status and link
    admin_status = is_admin()
    user_email = get_user_email()
    
    if user_email:
        if admin_status:
            st.sidebar.success("✅ Admin Access")
            # Admin page link (only visible to admins)
            st.sidebar.page_link("pages/admin.py", label="Admin Panel", icon="🔧")
        else:
            # Check if user profile exists and show role
            try:
                client = get_supabase_client()
                if client:
                    profile_result = client.supabase.table("user_profiles").select("role").eq("user_id", get_user_id()).execute()
                    if profile_result.data:
                        role = profile_result.data[0].get('role', 'user')
                        if role != 'admin':
                            st.sidebar.info(f"👤 Role: {role}")
                            with st.sidebar.expander("🔧 Need Admin Access?"):
                                st.write("To become an admin, run this command on the server:")
                                st.code("python web_dashboard/setup_admin.py", language="bash")
                                st.write(f"Then enter your email: `{user_email}`")
            except Exception:
                pass  # Silently fail if we can't check
    
    # AI Assistant link (if available and requested)
    if show_ai_assistant:
        try:
            from ollama_client import check_ollama_health
            
            if check_ollama_health():
                st.sidebar.page_link("pages/ai_assistant.py", label="AI Assistant", icon="🤖")
            else:
                with st.sidebar.expander("💬 Chat Assistant", expanded=False):
                    st.warning("AI Assistant unavailable")
                    st.caption("Ollama is not running or not accessible.")
        except Exception:
            # Silently fail if Ollama check not available
            pass
    
    # Settings link (if requested)
    if show_settings:
        st.sidebar.page_link("pages/settings.py", label="User Preferences", icon="👤")
    
    st.sidebar.markdown("---")

