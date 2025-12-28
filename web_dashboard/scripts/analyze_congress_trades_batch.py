#!/usr/bin/env python3
"""
Analyze Congress Trades Batch Script
====================================

This script analyzes congress trades using the local LLM to detect potential
conflicts of interest. It processes trades that haven't been scored yet.

Features:
- Batched processing (newest to oldest)
- Resumable (skips already scored trades)
- Fixes "failed" 0.0 scores to NULL so they can be retried
- Enriches data with company sector from securities table

Usage:
    python scripts/analyze_congress_trades_batch.py [--batch-size 10] [--model granite3.3:8b]
"""

import sys
import os
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient
from ollama_client import OllamaClient
from postgres_client import PostgresClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("congress_analysis.log")
    ]
)
logger = logging.getLogger(__name__)

# Prompt template
PROMPT_TEMPLATE = """
Analyze this trade for potential Insider Trading/Conflict of Interest.
Data:
- Politician: {politician} ({party} - {state})
- Chamber: {chamber}
- Asset Owner: {owner}
- Committee Assignments: {committees}
- Ticker: {ticker}
- Company: {company_name}
- Sector: {sector}
- Date: {date}
- Type: {type}
- Amount: {amount}

Task:
Calculate a 'conflict_score' from 0.0 to 1.0 based on these rules:
1. HIGH SCORE (0.8-1.0): Direct overlap (e.g., Armed Services member buying Defense stock, spouse trades, timing near votes).
2. MEDIUM SCORE (0.4-0.7): Sector overlap or related industries.
3. LOW SCORE (0.0-0.3): Broad index funds or clearly unrelated industries.

Consider:
- Committee jurisdiction over company's sector
- Asset owner (Self vs Spouse/Dependent) - spouse trades can still be concerning
- Political party relevance to industry
- State interests (e.g., CA rep + tech stocks, TX rep + energy)

Return JSON:
{{
  "conflict_score": 0.95,
  "reasoning": "Rep. Smith (R-TX) sits on House Armed Services and bought $50k RTX. High overlap between committee jurisdiction and defense contractor."
}}
"""

def fix_failed_scores(client: SupabaseClient):
    """Reset trades with 0.0 score and failure notes to NULL so they can be retried.
    
    WARNING: This should ONLY be run manually via --fix-only flag.
    Do NOT call this automatically in scheduled jobs, as 0.0 might be a legitimate score.
    This function is only for fixing buggy scores from previous versions.
    """
    logger.info("Checking for failed scores (0.0 with error notes)...")
    
    try:
        # Find records with 0 score and "Error" or "Failed" in notes
        # Supabase filtering limitations might require fetching and filtering in python if logic is complex
        # But we can try a simple query first.
        
        # Note: We can't easily do LIKE query for multiple conditions in one go via simple client methods sometimes
        # So we fetch 0 scores and check notes in Python for safety
        
        response = client.supabase.table("congress_trades")\
            .select("id, notes")\
            .eq("conflict_score", 0.0)\
            .execute()
            
        to_fix = []
        for row in response.data:
            notes = str(row.get('notes', '')).lower()
            if 'error' in notes or 'fail' in notes or 'optimization failed' in notes:
                to_fix.append(row['id'])
        
        if to_fix:
            logger.info(f"Found {len(to_fix)} failed records to reset.")
            # Update in batches
            batch_size = 50
            for i in range(0, len(to_fix), batch_size):
                batch_ids = to_fix[i:i+batch_size]
                client.supabase.table("congress_trades")\
                    .update({"conflict_score": None})\
                    .in_("id", batch_ids)\
                    .execute()
            logger.info("   [FIXED] Reset failed scores to NULL.")
        else:
            logger.info("No failed scores found.")
            
    except Exception as e:
        logger.error(f"Error fixing failed scores: {e}")

def get_trade_context(client: SupabaseClient, trade: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich trade data with sector, company info, and committee assignments."""
    ticker = trade.get('ticker')
    politician_name = trade.get('politician', 'Unknown')
    
    context = {
        'politician': politician_name,
        'party': trade.get('party') or 'Unknown',
        'state': trade.get('state') or 'Unknown',
        'chamber': trade.get('chamber') or 'Unknown',
        'owner': trade.get('owner') or 'Self',  # Default to Self if not specified
        'committees': 'Unknown',
        'ticker': ticker,
        'company_name': 'Unknown',
        'sector': 'Unknown',
        'date': trade.get('transaction_date'),
        'type': trade.get('type'),
        'amount': trade.get('amount')
    }
    
    # Fetch metadata from securities table
    try:
        response = client.supabase.table("securities")\
            .select("company_name, sector")\
            .eq("ticker", ticker)\
            .execute()
            
        if response.data:
            sec = response.data[0]
            if sec.get('company_name'):
                context['company_name'] = sec.get('company_name')
            if sec.get('sector'):
                context['sector'] = sec.get('sector')
                
    except Exception as e:
        logger.warning(f"Failed to fetch security metadata for {ticker}: {e}")
    
    # Fetch committee assignments for this politician
    try:
        # First, find the politician by name (fuzzy match - try exact first, then partial)
        politician_result = client.supabase.table("politicians")\
            .select("id, name")\
            .ilike("name", f"%{politician_name}%")\
            .limit(1)\
            .execute()
        
        if politician_result.data:
            politician_id = politician_result.data[0]['id']
            
            # Get all committee assignments for this politician
            assignments_result = client.supabase.table("committee_assignments")\
                .select("""
                    committee_id,
                    rank,
                    title,
                    committees (
                        name,
                        target_sectors
                    )
                """)\
                .eq("politician_id", politician_id)\
                .execute()
            
            if assignments_result.data:
                committees_list = []
                for assignment in assignments_result.data:
                    committee = assignment.get('committees', {})
                    committee_name = committee.get('name', 'Unknown')
                    target_sectors = committee.get('target_sectors', [])
                    rank = assignment.get('rank')
                    title = assignment.get('title', 'Member')
                    
                    # Format: "House Committee on Armed Services (Chairman) - Defense, Aerospace"
                    sectors_str = ', '.join(target_sectors) if target_sectors else 'None'
                    title_str = f" ({title})" if title else ""
                    committees_list.append(f"{committee_name}{title_str} - Sectors: {sectors_str}")
                
                context['committees'] = '; '.join(committees_list) if committees_list else 'None'
            else:
                context['committees'] = 'None (no committee assignments found)'
        else:
            context['committees'] = f'Unknown (politician "{politician_name}" not found in database)'
            
    except Exception as e:
        logger.warning(f"Failed to fetch committee data for {politician_name}: {e}")
        context['committees'] = 'Error fetching committee data'
        
    return context

def analyze_trade(ollama: OllamaClient, context: Dict[str, Any], model: str, verbose: bool = False) -> Dict[str, Any]:
    """Run AI analysis on a single trade."""
    prompt = PROMPT_TEMPLATE.format(**context)
    
    logger.info(f"Analyzing {context['politician']} - {context['ticker']}...")
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"🤖 Granite Analysis: {context['politician']} ({context['party']}-{context['state']}) - {context['ticker']}")
        print(f"{'='*80}")
    
    # System prompt to enforce JSON
    system_prompt = "You are a financial ethics analyzer. Return ONLY valid JSON."
    
    try:
        # Use query_ollama generator but join result
        full_response = ""
        for chunk in ollama.query_ollama(
            prompt=prompt,
            model=model,
            stream=True,
            system_prompt=system_prompt,
            temperature=0.1 # Low temp for consistent JSON
        ):
            full_response += chunk
            if verbose:
                print(chunk, end='', flush=True)
        
        if verbose:
            print(f"\n{'='*80}\n")
            
        # Parse JSON
        import re
        json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            return result
        else:
            # Try parsing raw if no clean match found
            return json.loads(full_response)
            
    except Exception as e:
        logger.error(f"AI Analysis failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Analyze Congress Trades')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of trades to process per batch')
    parser.add_argument('--model', type=str, default='granite3.3:8b', help='Ollama model to use')
    parser.add_argument('--limit', type=int, default=0, help='Total limit of trades to process (0 for infinite/until done)')
    parser.add_argument('--fix-only', action='store_true', help='Only fix failed scores and exit')
    parser.add_argument('--rescore', action='store_true', help='Re-analyze trades that already have conflict scores (for testing/debugging with new metadata)')
    parser.add_argument('--verbose', action='store_true', help='Show Granite\'s streaming output in real-time (useful for manual runs/debugging)')
    parser.add_argument('--skip-nulls', action='store_true', help='Skip trades with null party or state metadata (useful when scraper is still running)')
    args = parser.parse_args()
    
    logger.info("Starting AI Analysis Job")
    
    try:
        client = SupabaseClient(use_service_role=True)
        ollama = OllamaClient()
        postgres = PostgresClient()  # For storing analysis results
        
        if not ollama.check_health():
            logger.error("   [ERROR] Ollama is not accessible. Is it running?")
            sys.exit(1)
            
        # Step 1: Fix failed scores
        fix_failed_scores(client)
        
        if args.fix_only:
            logger.info("Fix-only mode enabled. Exiting.")
            sys.exit(0)
        
        total_processed = 0
        
        # Determine mode
        if args.rescore:
            logger.info("🔄 RESCORE MODE: Re-analyzing trades (allows multiple analyses)")
        else:
            logger.info("📊 NORMAL MODE: Analyzing trades without analysis in current version")
        
        if args.skip_nulls:
            logger.info("⏭️  SKIP NULLS: Only processing trades with complete metadata (party, state)")
        
        while True:
            # Fetch trades based on mode
            if args.rescore:
                # Rescore mode: analyze ALL trades (allows multiple analyses)
                query = client.supabase.table("congress_trades").select("*")
            else:
                # Normal mode: only analyze trades not yet analyzed with this version
                # Get trade IDs that have been analyzed (from Postgres)
                analyzed_result = postgres.execute_query(
                    "SELECT trade_id FROM congress_trades_analysis WHERE model_used = %s AND analysis_version = %s",
                    (args.model, 1)
                )
                
                analyzed_ids = [row['trade_id'] for row in analyzed_result] if analyzed_result else []
                
                # Fetch trades NOT in the analyzed list
                query = client.supabase.table("congress_trades").select("*")
                if analyzed_ids:
                    query = query.not_.in_("id", analyzed_ids)
            
            # Skip trades with null metadata if requested
            if args.skip_nulls:
                query = query.not_.is_("party", "null").not_.is_("state", "null")
            
            response = query\
                .order("transaction_date", desc=True)\
                .limit(args.batch_size)\
                .execute()
            
            trades = response.data
            
            if not trades:
                logger.info("   [DONE] No more unscored trades found.")
                break
                
            logger.info(f"Processing batch of {len(trades)} trades...")
            
            for trade in trades:
                try:
                    # Enrich
                    context = get_trade_context(client, trade)
                    
                    # Analyze
                    analysis = analyze_trade(ollama, context, args.model, verbose=args.verbose)
                    
                    if analysis and 'conflict_score' in analysis:
                        score = float(analysis['conflict_score'])
                        reasoning = analysis.get('reasoning', 'No reasoning provided')
                        
                        # Save to postgres analysis table (separate database to save Supabase costs)
                        try:
                            postgres.execute_update(
                                """
                                INSERT INTO congress_trades_analysis 
                                    (trade_id, conflict_score, reasoning, model_used, analysis_version)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (trade_id, model_used, analysis_version) 
                                DO UPDATE SET 
                                    conflict_score = EXCLUDED.conflict_score,
                                    reasoning = EXCLUDED.reasoning,
                                    analyzed_at = NOW()
                                """,
                                (trade['id'], score, reasoning, args.model, 1)
                            )
                            logger.info(f"   [SCORED] {score} ({reasoning})")
                            total_processed += 1
                        except Exception as db_error:
                            logger.error(f"   [ERROR] Failed to save analysis to Postgres: {db_error}")
                            
                    else:
                        logger.warning(f"   [WARN] Failed to parse AI response for ID {trade['id']}")
                        # We do NOT update the record, so it stays NULL and can be retried.
                        # Optionally, we could set a "failed_attempts" counter if we had one.
                        
                except Exception as e:
                    logger.error(f"Error processing trade {trade['id']}: {e}")
                
            # Check limit
            if args.limit > 0 and total_processed >= args.limit:
                logger.info(f"Reached limit of {args.limit} trades.")
                break
            
            # Small delay between batches
            time.sleep(1)
            
        logger.info(f"Job complete. Processed {total_processed} trades.")
        
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
