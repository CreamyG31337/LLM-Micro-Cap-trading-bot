#!/usr/bin/env python3
"""
Backfill Chain of Thought analysis for existing articles.
Stops early if results are bad (configurable threshold).
"""

import sys
import json
from pathlib import Path
from typing import Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.ollama_client import get_ollama_client, check_ollama_health
from web_dashboard.research_repository import ResearchRepository
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")


def get_sentiment_score(label: str) -> float:
    """Get numeric score for sentiment label."""
    mapping = {
        "VERY_BULLISH": 2.0,
        "BULLISH": 1.0,
        "NEUTRAL": 0.0,
        "BEARISH": -1.0,
        "VERY_BEARISH": -2.0
    }
    return mapping.get(label, 0.0)


def validate_result(result: dict) -> Tuple[bool, str]:
    """Validate that the result has all required fields and they're correct.
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(result, dict):
        return False, "Result is not a dictionary"
    
    # Check sentiment
    sentiment = result.get("sentiment", "")
    valid_sentiments = ["VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"]
    if not sentiment or sentiment not in valid_sentiments:
        return False, f"Invalid sentiment: {sentiment}"
    
    # Check sentiment_score matches
    sentiment_score = result.get("sentiment_score", 0.0)
    expected_score = get_sentiment_score(sentiment)
    if abs(sentiment_score - expected_score) > 0.01:  # Allow small floating point differences
        return False, f"Sentiment score mismatch: {sentiment_score} != {expected_score}"
    
    # Check claims is a list
    claims = result.get("claims", [])
    if not isinstance(claims, list):
        return False, f"Claims is not a list: {type(claims)}"
    
    # Check required fields exist (even if empty)
    required_fields = ["summary", "fact_check", "conclusion"]
    for field in required_fields:
        if field not in result:
            return False, f"Missing required field: {field}"
    
    return True, "OK"


def backfill_articles(
    max_articles: int = None,
    stop_on_failures: int = 3,
    min_success_rate: float = 0.7,
    model: str = None
) -> None:
    """Backfill Chain of Thought analysis for articles missing it.
    
    Args:
        max_articles: Maximum number of articles to process (None = all)
        stop_on_failures: Stop after N consecutive failures
        min_success_rate: Minimum success rate to continue (0.0 to 1.0)
        model: Model to use (None = use default from settings)
    """
    print("=" * 80)
    print("Chain of Thought Backfill")
    print("=" * 80)
    
    # Check Ollama
    if not check_ollama_health():
        print("❌ Ollama is not available. Please start Ollama first.")
        return
    
    # Initialize clients
    try:
        repo = ResearchRepository()
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("❌ Failed to initialize Ollama client")
            return
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        return
    
    # Get model
    if model is None:
        try:
            from web_dashboard.settings import get_summarizing_model
            model = get_summarizing_model()
        except Exception:
            model = "llama3.2:3b"
    
    print(f"📊 Using model: {model}")
    
    # Get articles needing analysis
    print("\n🔍 Finding articles needing Chain of Thought analysis...")
    query = """
        SELECT id, title, content 
        FROM research_articles 
        WHERE sentiment IS NULL 
          AND content IS NOT NULL 
          AND LENGTH(content) > 200
        ORDER BY fetched_at DESC
    """
    
    if max_articles:
        query += f" LIMIT {max_articles}"
    
    articles = repo.client.execute_query(query)
    
    if not articles:
        print("✅ No articles need backfilling. All articles already have Chain of Thought analysis.")
        return
    
    print(f"📚 Found {len(articles)} articles to process")
    print(f"⚙️  Settings: stop after {stop_on_failures} failures, min success rate: {min_success_rate*100:.0f}%")
    
    # Process articles
    success_count = 0
    fail_count = 0
    consecutive_failures = 0
    
    for i, article in enumerate(articles, 1):
        article_id = article['id']
        title = article.get('title', 'Untitled')[:60]
        content = article.get('content', '')
        
        print(f"\n[{i}/{len(articles)}] Processing: {title}...")
        
        # Generate analysis
        try:
            summary_data = ollama_client.generate_summary(content, model=model)
            
            if not summary_data or not isinstance(summary_data, dict):
                print(f"   ❌ Invalid response format")
                fail_count += 1
                consecutive_failures += 1
                if consecutive_failures >= stop_on_failures:
                    print(f"\n⚠️  Stopping: {consecutive_failures} consecutive failures")
                    break
                continue
            
            # Validate result
            is_valid, error_msg = validate_result(summary_data)
            if not is_valid:
                print(f"   ❌ Validation failed: {error_msg}")
                print(f"   📋 Result keys: {list(summary_data.keys())}")
                fail_count += 1
                consecutive_failures += 1
                if consecutive_failures >= stop_on_failures:
                    print(f"\n⚠️  Stopping: {consecutive_failures} consecutive failures")
                    break
                continue
            
            # Update article
            success = repo.update_article_analysis(
                article_id=article_id,
                summary=summary_data.get("summary"),
                claims=summary_data.get("claims"),
                fact_check=summary_data.get("fact_check"),
                conclusion=summary_data.get("conclusion"),
                sentiment=summary_data.get("sentiment"),
                sentiment_score=summary_data.get("sentiment_score")
            )
            
            if success:
                sentiment = summary_data.get("sentiment", "N/A")
                score = summary_data.get("sentiment_score", 0.0)
                print(f"   ✅ Updated (Sentiment: {sentiment}, Score: {score})")
                success_count += 1
                consecutive_failures = 0  # Reset failure counter
            else:
                print(f"   ❌ Database update failed")
                fail_count += 1
                consecutive_failures += 1
                if consecutive_failures >= stop_on_failures:
                    print(f"\n⚠️  Stopping: {consecutive_failures} consecutive failures")
                    break
            
            # Check success rate
            total_processed = success_count + fail_count
            if total_processed > 0:
                current_success_rate = success_count / total_processed
                if current_success_rate < min_success_rate and total_processed >= 5:
                    print(f"\n⚠️  Stopping: Success rate {current_success_rate*100:.1f}% below threshold {min_success_rate*100:.0f}%")
                    break
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            fail_count += 1
            consecutive_failures += 1
            if consecutive_failures >= stop_on_failures:
                print(f"\n⚠️  Stopping: {consecutive_failures} consecutive failures")
                break
    
    # Summary
    total_processed = success_count + fail_count
    print("\n" + "=" * 80)
    print("Backfill Summary")
    print("=" * 80)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    if total_processed > 0:
        print(f"📊 Success rate: {success_count / total_processed * 100:.1f}%")
    print(f"📝 Total processed: {total_processed} / {len(articles)}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill Chain of Thought analysis for existing articles")
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of articles to process (default: all)"
    )
    parser.add_argument(
        "--stop-failures",
        type=int,
        default=3,
        help="Stop after N consecutive failures (default: 3)"
    )
    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=0.7,
        help="Minimum success rate to continue (0.0-1.0, default: 0.7)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use (default: from settings)"
    )
    
    args = parser.parse_args()
    
    backfill_articles(
        max_articles=args.max,
        stop_on_failures=args.stop_failures,
        min_success_rate=args.min_success_rate,
        model=args.model
    )

