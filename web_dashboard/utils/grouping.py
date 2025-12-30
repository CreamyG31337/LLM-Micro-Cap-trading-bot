#!/usr/bin/env python3
"""
Trade Grouping Utilities
========================

This module provides utilities for grouping Congress trades into sessions
based on temporal patterns.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Union


def get_trade_sessions(
    trades: List[Dict[str, Any]], 
    gap_days: int = 7,
    max_group_size: int = 0,
    date_field: str = 'transaction_date'
) -> List[List[Dict[str, Any]]]:
    """Group trades into sessions based on time gaps between consecutive trades.
    
    A "session" is a sequence of trades where each trade occurs within `gap_days`
    of the previous trade. When a gap exceeds `gap_days`, a new session starts.
    
    If `max_group_size` is > 0, a new session is forced when the current session
    reaches that size, regardless of the gap.
    
    This is useful for detecting trading patterns and bursts of activity that may
    cross calendar month boundaries.
    
    Args:
        trades: List of trade dictionaries. Each trade must have a date field.
        gap_days: Maximum number of days between trades in the same session (default: 7)
        max_group_size: Maximum number of trades per session (0 = unlimited)
        date_field: Name of the date field in trade dicts (default: 'transaction_date')
    
    Returns:
        List of sessions, where each session is a list of trade dictionaries.
        Sessions are ordered chronologically (oldest first).
        Empty input returns empty list.
    
    Example:
        >>> trades = [
        ...     {'transaction_date': '2024-01-01', 'ticker': 'AAPL'},
        ...     {'transaction_date': '2024-01-03', 'ticker': 'MSFT'},
        ...     {'transaction_date': '2024-01-10', 'ticker': 'GOOGL'},  # Gap < 7 days
        ...     {'transaction_date': '2024-02-15', 'ticker': 'TSLA'},   # Gap > 7 days → new session
        ... ]
        >>> sessions = get_trade_sessions(trades)
        >>> len(sessions)
        2
        >>> len(sessions[0])  # First session has 3 trades
        3
        >>> len(sessions[1])  # Second session has 1 trade
        1
    """
    if not trades:
        return []
    
    # Helper to parse dates
    def parse_date(date_val: Union[str, datetime]) -> datetime:
        """Parse a date value to datetime object."""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            # Handle ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
            return datetime.fromisoformat(date_val.replace('Z', '+00:00').split('T')[0])
        raise ValueError(f"Cannot parse date: {date_val}")
    
    # Sort trades by date (oldest first)
    sorted_trades = sorted(
        trades,
        key=lambda t: parse_date(t.get(date_field, '1970-01-01'))
    )
    
    # Group into sessions
    sessions = []
    current_session = [sorted_trades[0]]
    
    for i in range(1, len(sorted_trades)):
        current_trade = sorted_trades[i]
        previous_trade = sorted_trades[i - 1]
        
        # Calculate day gap
        current_date = parse_date(current_trade.get(date_field))
        previous_date = parse_date(previous_trade.get(date_field))
        day_gap = (current_date - previous_date).days
        
        # Check conditions:
        # 1. Gap is within limit
        # 2. Size limit not reached (if set)
        gap_ok = day_gap <= gap_days
        size_ok = (max_group_size == 0) or (len(current_session) < max_group_size)
        
        if gap_ok and size_ok:
            # Same session
            current_session.append(current_trade)
        else:
            # New session - save current and start fresh
            sessions.append(current_session)
            current_session = [current_trade]
    
    # Don't forget the last session
    if current_session:
        sessions.append(current_session)
    
    return sessions


def group_by_politician(
    trades: List[Dict[str, Any]], 
    politician_field: str = 'politician'
) -> Dict[str, List[Dict[str, Any]]]:
    """Group trades by politician name.
    
    Args:
        trades: List of trade dictionaries
        politician_field: Name of the politician field (default: 'politician')
    
    Returns:
        Dictionary mapping politician name to list of their trades
    """
    grouped = {}
    for trade in trades:
        politician = trade.get(politician_field, 'Unknown')
        if politician not in grouped:
            grouped[politician] = []
        grouped[politician].append(trade)
    return grouped


def get_politician_sessions(
    trades: List[Dict[str, Any]],
    gap_days: int = 7,
    max_group_size: int = 0,
    politician_field: str = 'politician',
    date_field: str = 'transaction_date'
) -> Dict[str, List[List[Dict[str, Any]]]]:
    """Group trades by politician, then into sessions for each politician.
    
    This is a convenience function that combines group_by_politician and
    get_trade_sessions.
    
    Args:
        trades: List of all trade dictionaries
        gap_days: Maximum days between trades in same session (default: 7)
        max_group_size: Maximum trades per session (default: 0 = unlimited)
        politician_field: Name of politician field (default: 'politician')
        date_field: Name of date field (default: 'transaction_date')
    
    Returns:
        Dictionary mapping politician name to list of sessions.
        Each session is a list of trade dictionaries.
    
    Example:
        >>> trades = [... all Congress trades ...]
        >>> politician_sessions = get_politician_sessions(trades)
        >>> pelosi_sessions = politician_sessions.get('Nancy Pelosi', [])
        >>> print(f"Pelosi has {len(pelosi_sessions)} trading sessions")
    """
    # First group by politician
    by_politician = group_by_politician(trades, politician_field)
    
    # Then get sessions for each politician
    politician_sessions = {}
    for politician, politician_trades in by_politician.items():
        sessions = get_trade_sessions(politician_trades, gap_days, max_group_size, date_field)
        politician_sessions[politician] = sessions
    
    return politician_sessions


# Test / Example usage
if __name__ == "__main__":
    print("Testing Trade Session Grouping")
    print("=" * 80)
    
    # Example: Nancy Pelosi trades
    test_trades = [
        {'politician': 'Nancy Pelosi', 'transaction_date': '2024-01-01', 'ticker': 'AAPL', 'type': 'Purchase'},
        {'politician': 'Nancy Pelosi', 'transaction_date': '2024-01-03', 'ticker': 'MSFT', 'type': 'Purchase'},
        {'politician': 'Nancy Pelosi', 'transaction_date': '2024-01-10', 'ticker': 'GOOGL', 'type': 'Sale'},
        # 35-day gap here
        {'politician': 'Nancy Pelosi', 'transaction_date': '2024-02-15', 'ticker': 'NVDA', 'type': 'Purchase'},
        {'politician': 'Nancy Pelosi', 'transaction_date': '2024-02-16', 'ticker': 'TSLA', 'type': 'Purchase'},
        # Other politician
        {'politician': 'Josh Hawley', 'transaction_date': '2024-01-05', 'ticker': 'F', 'type': 'Purchase'},
        {'politician': 'Josh Hawley', 'transaction_date': '2024-01-20', 'ticker': 'GM', 'type': 'Sale'},
    ]
    
    print("\nTest 1: Basic session grouping")
    print("-" * 80)
    pelosi_trades = [t for t in test_trades if t['politician'] == 'Nancy Pelosi']
    sessions = get_trade_sessions(pelosi_trades, gap_days=7)
    
    print(f"Nancy Pelosi has {len(sessions)} trading sessions:\n")
    for i, session in enumerate(sessions, 1):
        print(f"Session {i}: {len(session)} trades")
        for trade in session:
            print(f"  - {trade['transaction_date']}: {trade['type']} {trade['ticker']}")
        print()
    
    print("\nTest 2: Group all trades by politician + sessions")
    print("-" * 80)
    politician_sessions = get_politician_sessions(test_trades, gap_days=7)
    
    for politician, sessions in politician_sessions.items():
        print(f"\n{politician}: {len(sessions)} session(s)")
        for i, session in enumerate(sessions, 1):
            dates = [t['transaction_date'] for t in session]
            print(f"  Session {i}: {dates[0]} to {dates[-1]} ({len(session)} trades)")
    
    print("\n" + "=" * 80)
    print("[OK] All tests completed successfully!")
