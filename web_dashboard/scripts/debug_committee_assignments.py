#!/usr/bin/env python3
"""
Debug Committee Assignments in Congress Trades Analysis
=======================================================

This script searches all congress trade analysis records for messages indicating
that committee assignments could not be found, and reports which politicians
are affected.

Usage:
    python web_dashboard/scripts/debug_committee_assignments.py
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient
from postgres_client import PostgresClient

# Error messages to search for
COMMITTEE_ERROR_MESSAGES = [
    "no committee assignments found",
    "committee assignments could not be found",
    "None (no committee assignments found)",
    "Unknown (politician",
    "Error fetching committee data",
    "No committee assignments found",
    "Unable to determine regulatory power",
    "No recognized committee assignments"
]


def search_analysis_for_committee_errors() -> List[Dict[str, Any]]:
    """Search all analysis records for committee assignment errors."""
    print("Searching congress_trades_analysis for committee assignment errors...")
    print("=" * 70)
    
    postgres = PostgresClient()
    supabase = SupabaseClient()
    
    # Build SQL query to search for error messages in reasoning text
    # Use ILIKE for case-insensitive search
    conditions = " OR ".join([f"reasoning ILIKE '%{msg}%'" for msg in COMMITTEE_ERROR_MESSAGES])
    
    query = f"""
        SELECT 
            id,
            trade_id,
            conflict_score,
            confidence_score,
            reasoning,
            analyzed_at,
            model_used
        FROM congress_trades_analysis
        WHERE {conditions}
        ORDER BY analyzed_at DESC
    """
    
    print(f"Query: Searching for patterns: {', '.join(COMMITTEE_ERROR_MESSAGES[:3])}...")
    print()
    
    results = postgres.execute_query(query)
    
    if not results:
        print("[OK] No committee assignment errors found in analysis records!")
        return []
    
    print(f"[WARNING] Found {len(results)} analysis records with committee assignment issues\n")
    
    # Get trade details from Supabase to identify politicians
    trade_ids = [r['trade_id'] for r in results]
    
    # Fetch trades in batches (Supabase has limits)
    trades_data = {}
    batch_size = 100
    
    for i in range(0, len(trade_ids), batch_size):
        batch = trade_ids[i:i+batch_size]
        # Use enriched view which includes politician name from join
        try:
            trades_result = supabase.supabase.table('congress_trades_enriched')\
                .select('id, politician, politician_id, ticker, transaction_date, chamber, party, state')\
                .in_('id', batch)\
                .execute()
        except Exception:
            # Fallback: join manually if view doesn't work
            trades_result = supabase.supabase.table('congress_trades')\
                .select('id, politician_id, ticker, transaction_date, chamber, party, state, politicians(name)')\
                .in_('id', batch)\
                .execute()
            # Transform to match expected format
            for trade in trades_result.data:
                politician_name = 'Unknown'
                if trade.get('politicians'):
                    politician_name = trade['politicians'].get('name', 'Unknown')
                trade['politician'] = politician_name
        
        for trade in trades_result.data:
            trades_data[trade['id']] = trade
    
    # Enrich results with trade information
    enriched_results = []
    for result in results:
        trade_id = result['trade_id']
        trade = trades_data.get(trade_id, {})
        
        enriched_results.append({
            'analysis_id': result['id'],
            'trade_id': trade_id,
            'politician': trade.get('politician', 'Unknown'),
            'politician_id': trade.get('politician_id'),
            'ticker': trade.get('ticker', 'Unknown'),
            'transaction_date': trade.get('transaction_date'),
            'chamber': trade.get('chamber'),
            'party': trade.get('party'),
            'state': trade.get('state'),
            'conflict_score': result.get('conflict_score'),
            'confidence_score': result.get('confidence_score'),
            'reasoning': result.get('reasoning', ''),
            'analyzed_at': result.get('analyzed_at'),
            'model_used': result.get('model_used')
        })
    
    return enriched_results


def group_by_politician(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group results by politician name."""
    grouped = defaultdict(list)
    
    for result in results:
        politician = result.get('politician', 'Unknown')
        grouped[politician].append(result)
    
    return dict(grouped)


def check_politician_committees(politician_id: int, supabase: SupabaseClient) -> Dict[str, Any]:
    """Check if a politician has committee assignments in the database."""
    if not politician_id:
        return {'has_committees': False, 'reason': 'No politician_id provided'}
    
    try:
        # Check if politician exists
        pol_result = supabase.supabase.table('politicians')\
            .select('id, name, bioguide_id')\
            .eq('id', politician_id)\
            .execute()
        
        if not pol_result.data:
            return {'has_committees': False, 'reason': f'Politician ID {politician_id} not found'}
        
        politician = pol_result.data[0]
        
        # Check for committee assignments
        assignments_result = supabase.supabase.table('committee_assignments')\
            .select('id, committee_id, committees(name, target_sectors)')\
            .eq('politician_id', politician_id)\
            .execute()
        
        if assignments_result.data:
            committees = []
            for assignment in assignments_result.data:
                committee = assignment.get('committees', {})
                committees.append({
                    'name': committee.get('name', 'Unknown'),
                    'sectors': committee.get('target_sectors', [])
                })
            
            return {
                'has_committees': True,
                'politician_name': politician.get('name'),
                'bioguide_id': politician.get('bioguide_id'),
                'committees': committees,
                'committee_count': len(committees)
            }
        else:
            return {
                'has_committees': False,
                'politician_name': politician.get('name'),
                'bioguide_id': politician.get('bioguide_id'),
                'reason': 'No committee assignments found in database'
            }
    except Exception as e:
        return {'has_committees': False, 'reason': f'Error checking: {str(e)}'}


def print_report(results: List[Dict[str, Any]]):
    """Print a detailed report of the findings."""
    if not results:
        return
    
    print("\n" + "=" * 70)
    print("DETAILED REPORT")
    print("=" * 70)
    
    # Group by politician
    grouped = group_by_politician(results)
    
    print(f"\n[SUMMARY] {len(results)} trades affected across {len(grouped)} politicians\n")
    
    # Check each politician's actual committee status
    supabase = SupabaseClient()
    
    print("Politicians with Committee Assignment Issues:")
    print("-" * 70)
    
    for politician_name, trades in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n[POLITICIAN] {politician_name}")
        print(f"   Affected trades: {len(trades)}")
        
        # Get politician_id from first trade (they should all be the same politician)
        politician_id = trades[0].get('politician_id')
        
        if politician_id:
            committee_status = check_politician_committees(politician_id, supabase)
            
            if committee_status.get('has_committees'):
                print(f"   [OK] HAS COMMITTEES in database:")
                for committee in committee_status.get('committees', []):
                    sectors = ', '.join(committee.get('sectors', [])) or 'None'
                    print(f"      - {committee.get('name')} (Sectors: {sectors})")
                print(f"   [WARNING] Issue: Analysis incorrectly reported no committees!")
            else:
                print(f"   [ERROR] NO COMMITTEES in database")
                print(f"      Reason: {committee_status.get('reason', 'Unknown')}")
                if committee_status.get('bioguide_id'):
                    print(f"      Bioguide ID: {committee_status.get('bioguide_id')}")
        
        # Show sample trades
        print(f"   Sample trades:")
        for trade in trades[:3]:  # Show first 3
            print(f"      - {trade.get('ticker')} ({trade.get('transaction_date')}) "
                  f"Score: {trade.get('conflict_score')}")
        
        if len(trades) > 3:
            print(f"      ... and {len(trades) - 3} more")
    
    # Show reasoning samples
    print("\n" + "=" * 70)
    print("SAMPLE REASONING TEXT (showing error messages):")
    print("=" * 70)
    
    for i, result in enumerate(results[:5], 1):  # Show first 5
        print(f"\n[{i}] {result.get('politician')} - {result.get('ticker')}")
        print(f"    Date: {result.get('transaction_date')}")
        reasoning = result.get('reasoning', '')
        # Show first 200 chars of reasoning
        if len(reasoning) > 200:
            print(f"    Reasoning: {reasoning[:200]}...")
        else:
            print(f"    Reasoning: {reasoning}")
    
    if len(results) > 5:
        print(f"\n... and {len(results) - 5} more records")


def main():
    """Main execution function."""
    print("Congress Trades Analysis - Committee Assignment Debug")
    print("=" * 70)
    print()
    
    try:
        # Search for errors
        results = search_analysis_for_committee_errors()
        
        if results:
            # Print detailed report
            print_report(results)
            
            # Summary statistics
            print("\n" + "=" * 70)
            print("SUMMARY STATISTICS")
            print("=" * 70)
            
            politicians_with_committees = 0
            politicians_without_committees = 0
            
            supabase = SupabaseClient()
            checked_politicians = set()
            
            for result in results:
                politician_id = result.get('politician_id')
                if politician_id and politician_id not in checked_politicians:
                    checked_politicians.add(politician_id)
                    status = check_politician_committees(politician_id, supabase)
                    if status.get('has_committees'):
                        politicians_with_committees += 1
                    else:
                        politicians_without_committees += 1
            
            print(f"\nPoliticians that HAVE committees in DB: {politicians_with_committees}")
            print(f"Politicians that DON'T have committees in DB: {politicians_without_committees}")
            print(f"\n[WARNING] If politicians_with_committees > 0, there's a bug in the analysis code!")
            print(f"[WARNING] If politicians_without_committees > 0, committee data needs to be synced!")
        else:
            print("\n[OK] No issues found!")
    
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

