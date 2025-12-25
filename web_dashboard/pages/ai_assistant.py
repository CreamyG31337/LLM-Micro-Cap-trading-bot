#!/usr/bin/env python3
"""
AI Assistant Chat Interface
===========================

Streamlit page for AI-powered portfolio investigation.
Users can chat with AI about their portfolio data.
"""

import streamlit as st
import sys
import logging
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)
from typing import List, Dict, Optional
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, get_user_email, get_user_id
from chat_context import ChatContextManager, ContextItemType
from ollama_client import get_ollama_client, check_ollama_health, list_available_models
from searxng_client import get_searxng_client, check_searxng_health
from search_utils import (
    format_search_results, build_search_query, search_portfolio_tickers,
    search_market_news
)
import os

# Configuration
MAX_SEARCH_TICKERS = int(os.getenv("MAX_SEARCH_TICKERS", "20"))  # Limit tickers to avoid overwhelming searches
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

# Check SearXNG connection (non-blocking)
searxng_available = check_searxng_health()
searxng_client = get_searxng_client()

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
    
    st.markdown("---")
    
    # Web Search section
    st.header("🔍 Web Search")
    if searxng_available:
        st.success("✅ SearXNG available")
        include_search = st.checkbox(
            "Enable Web Search",
            value=ContextItemType.SEARCH_RESULTS in current_types,
            help="Search the web for relevant information when answering questions",
            key="toggle_search"
        )
        
        # Auto-search for tickers option
        auto_search_tickers = st.checkbox(
            "Auto-search ticker news",
            value=False,
            help="Automatically search for news about portfolio tickers",
            key="auto_search_tickers"
        )
    else:
        st.warning("⚠️ SearXNG unavailable")
        st.caption("Web search will be disabled. SearXNG may be starting up or not configured.")
        include_search = False
        auto_search_tickers = False
    
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
    
    # Handle search context
    if include_search and searxng_available:
        if ContextItemType.SEARCH_RESULTS not in current_types:
            chat_context.add_item(ContextItemType.SEARCH_RESULTS, fund=selected_fund)
    elif not include_search and ContextItemType.SEARCH_RESULTS in current_types:
        chat_context.remove_item(ContextItemType.SEARCH_RESULTS, fund=selected_fund)
    
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
    """Build formatted context string from selected items.
    
    Returns:
        Formatted string containing all context items for the AI
    """
    items = chat_context.get_items()
    if not items:
        return ""
    
    context_parts = []
    
    for item in items:
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
            
            elif item.item_type == ContextItemType.SEARCH_RESULTS:
                # Search results are added dynamically when user queries
                # This is handled in the query processing section
                pass
            
        except Exception as e:
            st.warning(f"Error loading {item.item_type.value}: {e}")
            continue
    
    return "\n\n---\n\n".join(context_parts)

# Start Analysis Workflow vs Standard Chat
user_query = None

# If no messages yet, show the "Start Analysis" workflow
if updated_items and not st.session_state.chat_messages:
    st.info(f"✨ Ready to analyze {len(updated_items)} data source(s) from {selected_fund if selected_fund else 'N/A'}")
    
    with st.container():
        st.markdown("### 🚀 Start Analysis")
        st.caption("Review and edit the prompt below, then click Run to start.")
        
        # Generate default prompt
        default_prompt = chat_context.generate_prompt()
        
        # Editable prompt area
        initial_query = st.text_area(
            "Analysis Prompt",
            value=default_prompt,
            height=150,
            help="You can edit this prompt before sending",
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("▶️ Run Analysis", type="primary", use_container_width=True):
                user_query = initial_query

# Standard chat input (always available)
chat_input_query = st.chat_input("Ask about your portfolio...")
if chat_input_query:
    user_query = chat_input_query

if user_query:
    # Add user message to history
    st.session_state.chat_messages.append({
        "role": "user",
        "content": user_query
    })
    
    # Build context
    context_string = build_context_string()
    
    # Perform web search if enabled
    search_results_text = ""
    search_data = None
    if include_search and searxng_client and searxng_available:
        with st.spinner("🔍 Searching the web..."):
            try:
                # Get portfolio tickers if available for enhanced search
                tickers = []
                if selected_fund:
                    try:
                        positions_df = get_current_positions(selected_fund)
                        if not positions_df.empty and 'ticker' in positions_df.columns:
                            all_tickers = positions_df['ticker'].tolist()
                            # Limit to MAX_SEARCH_TICKERS to avoid overwhelming the search
                            tickers = all_tickers[:MAX_SEARCH_TICKERS]
                            if len(all_tickers) > MAX_SEARCH_TICKERS:
                                logger.info(f"Limited ticker search from {len(all_tickers)} to {MAX_SEARCH_TICKERS} tickers")
                    except Exception as e:
                        logger.warning(f"Could not fetch tickers for search: {e}")
                
                # Build optimized search query
                search_query = build_search_query(user_query, tickers if auto_search_tickers else None)
                
                # Perform search
                search_data = searxng_client.search_news(
                    query=search_query,
                    time_range='day',
                    max_results=10
                )
                
                if search_data and 'results' in search_data and search_data['results']:
                    search_results_text = format_search_results(search_data, max_results=10)
                    context_string = f"{context_string}\n\n---\n\n{search_results_text}" if context_string else search_results_text
                    
            except Exception as e:
                st.warning(f"Web search failed: {e}")
                logger.error(f"Search error: {e}")
    
    # Generate prompt
    current_context_items = chat_context.get_items()
    if current_context_items:
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
        
        # Show search results if available
        if search_data and search_data.get('results'):
            with st.expander("🔍 Web Search Results", expanded=False):
                st.markdown(format_search_results(search_data, max_results=5))
    
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
search_status = "✅" if searxng_available else "❌"
current_context_items = chat_context.get_items()
st.caption(f"Using model: {selected_model} | Context items: {len(current_context_items)} | Search: {search_status}")

# Debug section
with st.expander("🔧 Debug Context (Raw AI Input)", expanded=False):
    current_context_items = chat_context.get_items()
    st.caption(f"**Context Items Count:** {len(current_context_items)}")
    
    if current_context_items:
        st.caption("**Item Types:**")
        for item in current_context_items:
            st.text(f"  • {item.item_type.value} (Fund: {item.fund})")
        
        st.markdown("---")
        st.caption("**Full Context String:**")
        debug_context = build_context_string()
        if debug_context:
            st.code(debug_context, language="text")
        else:
            st.warning("Context string is empty (build_context_string returned nothing)")
    else:
        st.info("No context items selected.")

