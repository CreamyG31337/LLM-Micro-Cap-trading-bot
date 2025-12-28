#!/usr/bin/env python3
"""
Session Management Utilities for Congress Trades
=================================================

Manages "living sessions" of related trades that tell an evolving story.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def find_or_create_session(
    postgres,
    politician_name: str,
    trade_date: str,
    gap_days: int = 7
) -> Optional[int]:
    """Find existing session or create new one for a trade.
    
    Logic:
    1. Find politician's most recent session
    2. If session.end_date is within gap_days of trade_date:
       - Update session end_date, trade_count
       - Mark needs_reanalysis = TRUE
       - Return existing session_id
    3. Else:
       - Create new session
       - Return new session_id
    
    Args:
        postgres: PostgresClient instance
        politician_name: Name of politician
        trade_date: Date of trade (YYYY-MM-DD string or datetime)
        gap_days: Maximum gap between trades in same session (default: 7)
    
    Returns:
        session_id (int) or None on error
    """
    # Parse trade date
    if isinstance(trade_date, str):
        trade_dt = datetime.fromisoformat(trade_date.split('T')[0])
    else:
        trade_dt = trade_date
    
    try:
        # Find most recent session for this politician
        result = postgres.execute_query(
            """
            SELECT id, end_date, trade_count
            FROM congress_trade_sessions
            WHERE politician_name = %s
            ORDER BY end_date DESC
            LIMIT 1
            """,
            (politician_name,)
        )
        
        if result and len(result) > 0:
            session = result[0]
            session_id = session['id']
            end_date = session['end_date']
            trade_count = session['trade_count']
            
            # Calculate gap
            if isinstance(end_date, str):
                end_dt = datetime.fromisoformat(end_date.split('T')[0])
            else:
                end_dt = end_date
            
            day_gap = (trade_dt - end_dt).days
            
            if day_gap <= gap_days and day_gap >= 0:
                # Extend existing session
                postgres.execute_update(
                    """
                    UPDATE congress_trade_sessions
                    SET end_date = %s,
                        trade_count = trade_count + 1,
                        needs_reanalysis = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (trade_dt.date(), session_id)
                )
                logger.info(f"Extended session {session_id} for {politician_name} (gap: {day_gap} days)")
                return session_id
        
        # Create new session
        result = postgres.execute_query(
            """
            INSERT INTO congress_trade_sessions 
                (politician_name, start_date, end_date, trade_count, needs_reanalysis)
            VALUES (%s, %s, %s, 1, TRUE)
            RETURNING id
            """,
            (politician_name, trade_dt.date(), trade_dt.date())
        )
        
        if result and len(result) > 0:
            new_session_id = result[0]['id']
            logger.info(f"Created new session {new_session_id} for {politician_name}")
            return new_session_id
        
    except Exception as e:
        logger.error(f"Error in find_or_create_session: {e}")
        return None


def get_sessions_needing_analysis(
    postgres,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get sessions that need re-analysis.
    
    Args:
        postgres: PostgresClient instance
        limit: Maximum number of sessions to return
    
    Returns:
        List of session dicts with id, politician_name, trade_count, dates
    """
    try:
        result = postgres.execute_query(
            """
            SELECT 
                id,
                politician_name,
                start_date,
                end_date,
                trade_count,
                last_analyzed_at
            FROM congress_trade_sessions
            WHERE needs_reanalysis = TRUE
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        
        return result or []
        
    except Exception as e:
        logger.error(f"Error getting sessions needing analysis: {e}")
        return []


def should_skip_session(trades: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if session should be skipped (contains ONLY low-risk trades).
    
    Args:
        trades: List of trade dicts in the session
    
    Returns:
        Tuple of (should_skip: bool, reason: str)
    """
    # Import here to avoid circular dependency
    from scripts.analyze_congress_trades_batch import is_low_risk_asset
    
    has_analyzable_trade = False
    
    for trade in trades:
        is_low_risk, _ = is_low_risk_asset(trade)
        if not is_low_risk:
            has_analyzable_trade = True
            break
    
    if not has_analyzable_trade:
        return True, "Session contains only low-risk trades (ETFs, exchanges, etc.)"
    
    return False, ""


def get_session_trades(
    supabase,
    postgres,
    session_id: int
) -> List[Dict[str, Any]]:
    """Get all trades for a session.
    
    Args:
        supabase: SupabaseClient instance
        postgres: PostgresClient instance
        session_id: Session ID to fetch trades for
    
    Returns:
        List of trade dicts
    """
    try:
        # Get trade IDs from analysis table
        result = postgres.execute_query(
            """
            SELECT DISTINCT trade_id
            FROM congress_trades_analysis
            WHERE session_id = %s
            """,
            (session_id,)
        )
        
        if not result:
            return []
        
        trade_ids = [row['trade_id'] for row in result]
        
        # Fetch full trade data from Supabase
        response = supabase.supabase.table("congress_trades")\
            .select("*")\
            .in_("id", trade_ids)\
            .execute()
        
        return response.data or []
        
    except Exception as e:
        logger.error(f"Error getting session trades: {e}")
        return []


def mark_session_analyzed(
    postgres,
    session_id: int,
    conflict_score: float,
    confidence_score: float,
    ai_summary: str,
    model_used: str
):
    """Mark session as analyzed and save results.
    
    Args:
        postgres: PostgresClient instance
        session_id: Session ID
        conflict_score: AI conflict score (0.0-1.0)
        confidence_score: AI confidence score (0.0-1.0)
        ai_summary: AI-generated summary/reasoning
        model_used: Name of AI model used
    """
    try:
        postgres.execute_update(
            """
            UPDATE congress_trade_sessions
            SET conflict_score = %s,
                confidence_score = %s,
                ai_summary = %s,
                model_used = %s,
                last_analyzed_at = NOW(),
                needs_reanalysis = FALSE,
                updated_at = NOW()
            WHERE id = %s
            """,
            (conflict_score, confidence_score, ai_summary, model_used, session_id)
        )
        logger.info(f"Marked session {session_id} as analyzed (score: {conflict_score})")
        
    except Exception as e:
        logger.error(f"Error marking session as analyzed: {e}")


# Test functionality
if __name__ == "__main__":
    print("Session Manager Utilities")
    print("=" * 80)
    print("\nThis module provides utilities for managing Congress trade sessions.")
    print("\nKey Functions:")
    print("  - find_or_create_session(): Assign trades to sessions")
    print("  - get_sessions_needing_analysis(): Find sessions to analyze")
    print("  - should_skip_session(): Check if session is low-risk only")
    print("  - mark_session_analyzed(): Save analysis results")
    print("\n" + "=" * 80)
