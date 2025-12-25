#!/usr/bin/env python3
"""
AI Assistant Chat Interface
===========================

Streamlit page for AI-powered portfolio investigation.
Users can chat with AI about their portfolio data.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import List, Dict, Optional
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, get_user_email, get_user_id
from chat_context import ChatContextManager, ContextItemType
from ollama_client import get_ollama_client, check_ollama_health, list_available_models
from ai_context_builder import (
    format_holdings, format_thesis, format_trades, format_performance_metrics,
    format_cash_balances, format_investor_allocations, format_sector_allocation
)
from ai_prompts import get_system_prompt
from user_preferences import get_user_ai_model, set_user_ai_model
from streamlit_utils import (
    get_current_positions, get_trade_log, get_cash_balances,
    calculate_portfolio_value_over_time, calculate_performance_metrics,
    get_fund_thesis_data, get_investor_allocations, get_available_funds
)
import os

# Page configuration
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Hide Streamlit's default page navigation
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Check authentication
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Initialize chat context manager
if 'chat_context' not in st.session_state:
    st.session_state.chat_context = ChatContextManager()

chat_context = st.session_state.chat_context

# Initialize conversation history
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages: List[Dict[str, str]] = []

# Limit conversation history to prevent context overflow
MAX_CONVERSATION_HISTORY = 20  # Keep last N messages (10 exchanges)

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# 🤖 AI Portfolio Assistant")
with col2:
    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()

# Check Ollama connection
ollama_available = check_ollama_health()
if not ollama_available:
    st.error("❌ Cannot connect to Ollama API. Please check if Ollama is running.")
    st.info("The AI assistant requires Ollama to be running and accessible.")
    st.stop()

# Sidebar - Navigation, Settings and Context
from navigation import render_navigation
render_navigation(show_ai_assistant=False, show_settings=True)  # Don't show AI Assistant link on this page

with st.sidebar:
    st.header("⚙️ Model")
    
    # Get the system default model (admin-configured)
    from user_preferences import get_user_ai_model
    selected_model = get_user_ai_model()
    
    # Display current model (read-only)
    st.info(f"**Using:** {selected_model}")
    
    # Get model description if available
    client = get_ollama_client()
    if client:
        desc = client.get_model_description(selected_model)
        if desc:
            st.caption(f"ℹ️ {desc}")
    
    st.markdown("---")
    
    # Fund selection
    st.header("📊 Data Source")
    funds = get_available_funds()
    if funds:
        selected_fund = st.selectbox("Fund", options=funds, help="Select fund for AI analysis", key="fund_selector")
    else:
        selected_fund = None
        st.warning("No funds available")
    
    st.markdown("---")
    
    # Context selection toggles
    st.header("📋 Include in Analysis")
    st.caption("Select data to include:")
    
    # Get current context items for this fund
    context_items = chat_context.get_items()
    current_types = {item.item_type for item in context_items if item.fund == selected_fund}
    
    # Holdings toggle
    include_holdings = st.checkbox(
        "Current Holdings",
        value=ContextItemType.HOLDINGS in current_types,
        help="Include your current portfolio positions",
        key="toggle_holdings"
    )
    
    # Thesis toggle
    include_thesis = st.checkbox(
        "Investment Thesis",
        value=ContextItemType.THESIS in current_types,
        help="Include your investment strategy and pillars",
        key="toggle_thesis"
    )
    
    # Trades toggle
    include_trades = st.checkbox(
        "Recent Trades",
        value=ContextItemType.TRADES in current_types,
        help="Include recent trading activity",
        key="toggle_trades"
    )
    
    # Metrics toggle
    include_metrics = st.checkbox(
        "Performance Metrics",
        value=ContextItemType.METRICS in current_types,
        help="Include performance statistics",
        key="toggle_metrics"
    )
    
    # Cash balances toggle
    include_cash = st.checkbox(
        "Cash Balances",
        value=ContextItemType.CASH_BALANCES in current_types,
        help="Include current cash positions by currency",
        key="toggle_cash"
    )
    
    # Investor allocations toggle
    include_investors = st.checkbox(
        "Investor Allocations",
        value=ContextItemType.INVESTOR_ALLOCATIONS in current_types,
        help="Include investor ownership breakdown",
        key="toggle_investors"
    )
    
    # Apply context updates
    if selected_fund:
        # Update context based on toggles
        if include_holdings and ContextItemType.HOLDINGS not in current_types:
            chat_context.add_item(ContextItemType.HOLDINGS, fund=selected_fund)
        elif not include_holdings and ContextItemType.HOLDINGS in current_types:
            chat_context.remove_item(ContextItemType.HOLDINGS, fund=selected_fund)
        
        if include_thesis and ContextItemType.THESIS not in current_types:
            chat_context.add_item(ContextItemType.THESIS, fund=selected_fund)
        elif not include_thesis and ContextItemType.THESIS in current_types:
            chat_context.remove_item(ContextItemType.THESIS, fund=selected_fund)
        
        if include_trades and ContextItemType.TRADES not in current_types:
            chat_context.add_item(ContextItemType.TRADES, fund=selected_fund, metadata={'limit': 50})
        elif not include_trades and ContextItemType.TRADES in current_types:
            chat_context.remove_item(ContextItemType.TRADES, fund=selected_fund, metadata={'limit': 50})
        
        if include_metrics and ContextItemType.METRICS not in current_types:
            chat_context.add_item(ContextItemType.METRICS, fund=selected_fund)
        elif not include_metrics and ContextItemType.METRICS in current_types:
            chat_context.remove_item(ContextItemType.METRICS, fund=selected_fund)
        
        if include_cash and ContextItemType.CASH_BALANCES not in current_types:
            chat_context.add_item(ContextItemType.CASH_BALANCES, fund=selected_fund)
        elif not include_cash and ContextItemType.CASH_BALANCES in current_types:
            chat_context.remove_item(ContextItemType.CASH_BALANCES, fund=selected_fund)
        
        if include_investors and ContextItemType.INVESTOR_ALLOCATIONS not in current_types:
            chat_context.add_item(ContextItemType.INVESTOR_ALLOCATIONS, fund=selected_fund)
        elif not include_investors and ContextItemType.INVESTOR_ALLOCATIONS in current_types:
            chat_context.remove_item(ContextItemType.INVESTOR_ALLOCATIONS, fund=selected_fund)
    
    # Show count
    updated_items = chat_context.get_items()
    if updated_items:
        st.caption(f"✅ {len(updated_items)} data source(s) selected")
        if st.button("🗑️ Clear All", use_container_width=True, key="clear_all"):
            chat_context.clear_all()
            st.rerun()

# Main chat area
st.markdown("### 💬 Chat")

# Display conversation history
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Generate context data from selected items
def build_context_string() -> str:
    """Build formatted context string from selected items."""
    if not context_items:
        return ""
    
    context_parts = []
    
    for item in context_items:
        fund = item.fund or selected_fund
        
        try:
            if item.item_type == ContextItemType.HOLDINGS:
                positions_df = get_current_positions(fund)
                context_parts.append(format_holdings(positions_df, fund or "Unknown"))
            
            elif item.item_type == ContextItemType.THESIS:
                thesis_data = get_fund_thesis_data(fund or "")
                if thesis_data:
                    context_parts.append(format_thesis(thesis_data))
            
            elif item.item_type == ContextItemType.TRADES:
                limit = item.metadata.get('limit', 100)
                trades_df = get_trade_log(limit=limit, fund=fund)
                context_parts.append(format_trades(trades_df, limit))
            
            elif item.item_type == ContextItemType.METRICS:
                portfolio_df = calculate_portfolio_value_over_time(fund, days=365) if fund else None
                metrics = calculate_performance_metrics(fund) if fund else {}
                context_parts.append(format_performance_metrics(metrics, portfolio_df))
            
            elif item.item_type == ContextItemType.CASH_BALANCES:
                cash = get_cash_balances(fund) if fund else {}
                context_parts.append(format_cash_balances(cash))
            
            elif item.item_type == ContextItemType.INVESTOR_ALLOCATIONS:
                allocations = get_investor_allocations(fund) if fund else {}
                context_parts.append(format_investor_allocations(allocations))
            
        except Exception as e:
            st.warning(f"Error loading {item.item_type.value}: {e}")
            continue
    
    return "\n\n---\n\n".join(context_parts)

# Prompt preview section
if updated_items:
    with st.expander("📝 Prompt Preview", expanded=False):
        preview_prompt = chat_context.generate_prompt()
        st.caption("The AI assistant will analyze:")
        st.info(preview_prompt)
        st.caption(f"_{len(updated_items)} data source(s) selected from {selected_fund if selected_fund else 'N/A'}_")

# Chat input
user_query = st.chat_input("Ask about your portfolio...")

if user_query:
    # Add user message to history
    st.session_state.chat_messages.append({
        "role": "user",
        "content": user_query
    })
    
    # Build context
    context_string = build_context_string()
    
    # Generate prompt
    if context_items:
        prompt = chat_context.generate_prompt(user_query)
    else:
        prompt = user_query
    
    # Combine context and prompt
    full_prompt = prompt
    if context_string:
        full_prompt = f"{context_string}\n\n{prompt}"
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_query)
    
    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            client = get_ollama_client()
            if not client:
                st.error("AI client not available")
                st.stop()
            
            system_prompt = get_system_prompt()
            
            # Stream response
            # Pass None for temperature and max_tokens to let the client handle model-specific defaults
            # Model settings come from model_config.json and database overrides
            for chunk in client.query_ollama(
                prompt=full_prompt,
                model=selected_model,
                stream=True,
                temperature=None,  # Use model default
                max_tokens=None,   # Use model default
                system_prompt=system_prompt
            ):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Error getting AI response: {e}")
            full_response = f"Sorry, I encountered an error: {str(e)}"
        
        # Add assistant message to history
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": full_response
        })
        
        # Enforce conversation history limit (trim oldest messages)
        if len(st.session_state.chat_messages) > MAX_CONVERSATION_HISTORY:
            st.session_state.chat_messages = st.session_state.chat_messages[-MAX_CONVERSATION_HISTORY:]

# Footer
st.markdown("---")
st.caption(f"Using model: {selected_model} | Context items: {len(context_items)}")

