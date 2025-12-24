#!/usr/bin/env python3
"""
Chat Context Manager
====================

Manages selected context items for AI chat interface.
Handles click-to-add selections and intelligent prompt generation.
"""

import streamlit as st
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum


class ContextItemType(Enum):
    """Types of context items that can be added to chat."""
    HOLDINGS = "holdings"
    THESIS = "thesis"
    TRADES = "trades"
    PERFORMANCE_CHART = "performance_chart"
    METRICS = "metrics"
    CASH_BALANCES = "cash_balances"
    INVESTOR_ALLOCATIONS = "investor_allocations"
    PNL_CHART = "pnl_chart"
    SECTOR_ALLOCATION = "sector_allocation"


@dataclass
class ContextItem:
    """Represents a single context item selected by the user."""
    item_type: ContextItemType
    fund: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        """Make ContextItem hashable for use in sets."""
        return hash((self.item_type.value, self.fund, tuple(sorted(self.metadata.items()))))
    
    def __eq__(self, other):
        """Compare ContextItems for equality."""
        if not isinstance(other, ContextItem):
            return False
        return (self.item_type == other.item_type and 
                self.fund == other.fund and 
                self.metadata == other.metadata)


class ChatContextManager:
    """Manages chat context items and generates prompts."""
    
    def __init__(self):
        """Initialize the context manager."""
        if 'context_items' not in st.session_state:
            st.session_state.context_items: Set[ContextItem] = set()
    
    def add_item(
        self,
        item_type: ContextItemType,
        fund: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a context item.
        
        Args:
            item_type: Type of context item
            fund: Fund name (if applicable)
            metadata: Additional metadata (date ranges, limits, etc.)
            
        Returns:
            True if added, False if already exists
        """
        item = ContextItem(
            item_type=item_type,
            fund=fund,
            metadata=metadata or {}
        )
        
        if item in st.session_state.context_items:
            return False
        
        st.session_state.context_items.add(item)
        return True
    
    def remove_item(
        self,
        item_type: ContextItemType,
        fund: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Remove a context item.
        
        Args:
            item_type: Type of context item
            fund: Fund name (if applicable)
            metadata: Additional metadata
            
        Returns:
            True if removed, False if not found
        """
        item = ContextItem(
            item_type=item_type,
            fund=fund,
            metadata=metadata or {}
        )
        
        if item in st.session_state.context_items:
            st.session_state.context_items.remove(item)
            return True
        return False
    
    def clear_all(self):
        """Clear all context items."""
        st.session_state.context_items.clear()
    
    def get_items(self) -> List[ContextItem]:
        """Get all context items as a list.
        
        Returns:
            List of context items
        """
        return list(st.session_state.context_items)
    
    def has_item(self, item_type: ContextItemType) -> bool:
        """Check if a specific item type is in context.
        
        Args:
            item_type: Type to check
            
        Returns:
            True if item type exists in context
        """
        return any(item.item_type == item_type for item in st.session_state.context_items)
    
    def get_item_count(self) -> int:
        """Get the number of context items.
        
        Returns:
            Number of items
        """
        return len(st.session_state.context_items)
    
    def generate_prompt(self, user_query: Optional[str] = None) -> str:
        """Generate a prompt based on selected context items.
        
        Uses pattern matching to create intelligent prompts based on combinations.
        
        Args:
            user_query: Optional user query to include
            
        Returns:
            Generated prompt string
        """
        items = self.get_items()
        
        if not items:
            return user_query or "Please help me analyze my portfolio."
        
        # Get item types for pattern matching
        item_types = {item.item_type for item in items}
        
        # Pattern matching logic
        prompt_parts = []
        
        # Holdings + Thesis → Alignment analysis
        if ContextItemType.HOLDINGS in item_types and ContextItemType.THESIS in item_types:
            prompt_parts.append(
                "Analyze how the current portfolio holdings align with the investment thesis. "
                "Evaluate whether the positions support the stated investment strategy and pillars."
            )
        
        # Trades + P&L → Trade performance
        elif ContextItemType.TRADES in item_types and ContextItemType.PNL_CHART in item_types:
            prompt_parts.append(
                "Review the trade history and P&L patterns. "
                "Identify successful trades, areas for improvement, and any patterns in trading behavior."
            )
        
        # Performance Chart + Metrics → Trend analysis
        elif ContextItemType.PERFORMANCE_CHART in item_types and ContextItemType.METRICS in item_types:
            prompt_parts.append(
                "Analyze the performance trends over time along with key performance metrics. "
                "Provide insights on portfolio performance, risk-adjusted returns, and areas of strength or concern."
            )
        
        # Holdings only → Portfolio analysis
        elif ContextItemType.HOLDINGS in item_types and len(item_types) == 1:
            prompt_parts.append(
                "Provide a comprehensive analysis of the current portfolio holdings. "
                "Include insights on diversification, concentration risk, sector allocation, and individual position performance."
            )
        
        # Trades only → Trade analysis
        elif ContextItemType.TRADES in item_types and len(item_types) == 1:
            prompt_parts.append(
                "Analyze the recent trading activity. "
                "Review trade patterns, frequency, win rate, and identify any notable trends or concerns."
            )
        
        # Multiple items → Comparison/relationship analysis
        elif len(item_types) > 1:
            item_names = [item.item_type.value.replace("_", " ").title() for item in items]
            prompt_parts.append(
                f"Compare and analyze the relationship between {', '.join(item_names[:-1])} and {item_names[-1]}. "
                "Provide insights on how these elements interact and what they reveal about portfolio performance."
            )
        
        # Single item (other types)
        else:
            item = items[0]
            item_name = item.item_type.value.replace("_", " ").title()
            prompt_parts.append(
                f"Analyze the {item_name}. "
                "Provide insights and recommendations based on this data."
            )
        
        # Add user query if provided
        if user_query:
            prompt_parts.append(f"\n\nUser question: {user_query}")
        
        return " ".join(prompt_parts)
    
    def get_formatted_context_summary(self) -> str:
        """Get a human-readable summary of selected context items.
        
        Returns:
            Summary string
        """
        items = self.get_items()
        if not items:
            return "No context items selected."
        
        summaries = []
        for item in items:
            item_name = item.item_type.value.replace("_", " ").title()
            if item.fund:
                summaries.append(f"{item_name} ({item.fund})")
            else:
                summaries.append(item_name)
        
        return ", ".join(summaries)
    
    def render_context_ui(self, sidebar: bool = True):
        """Render the context UI showing selected items.
        
        Args:
            sidebar: If True, render in sidebar, else render in main area
        """
        container = st.sidebar if sidebar else st
        
        with container.expander("💬 Chat Assistant", expanded=False):
            items = self.get_items()
            
            if not items:
                st.caption("No items selected. Click 'Add to Chat' buttons on dashboard objects.")
            else:
                st.caption(f"{len(items)} item(s) selected:")
                
                for item in items:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        item_name = item.item_type.value.replace("_", " ").title()
                        if item.fund:
                            st.text(f"• {item_name} ({item.fund})")
                        else:
                            st.text(f"• {item_name}")
                    
                    with col2:
                        if st.button("Remove", key=f"remove_{id(item)}", use_container_width=True):
                            self.remove_item(item.item_type, item.fund, item.metadata)
                            st.rerun()
                
                st.markdown("---")
                
                if st.button("🗑️ Clear All", use_container_width=True):
                    self.clear_all()
                    st.rerun()
                
                if st.button("💬 Open Chat", use_container_width=True, type="primary"):
                    st.switch_page("pages/ai_assistant.py")

