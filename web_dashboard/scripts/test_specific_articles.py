#!/usr/bin/env python3
"""
Test specific articles with Chain of Thought analysis.
Non-interactive script that takes article IDs as arguments.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.ollama_client import get_ollama_client, check_ollama_health
from web_dashboard.research_repository import ResearchRepository
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")

# Import the test functions from the main test script
from web_dashboard.scripts.test_chain_of_thought_prompt import (
    test_prompt_on_article,
    display_result,
    get_sentiment_score
)


def test_articles_by_ids(article_ids: list, models: list = None):
    """Test specific articles by their IDs."""
    print("=" * 80)
    print("Testing Specific Articles")
    print("=" * 80)
    
    # Check Ollama
    if not check_ollama_health():
        print("[ERROR] Ollama is not available. Please start Ollama first.")
        return
    
    # Initialize clients
    try:
        db_client = PostgresClient()
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("[ERROR] Failed to initialize Ollama client")
            return
    except Exception as e:
        print(f"[ERROR] Error initializing clients: {e}")
        return
    
    # Get models
    if models is None:
        available_models = ollama_client.get_filtered_models()
        # Default to 3b and 8b if available
        model_3b = None
        model_8b = None
        for m in available_models:
            if "3b" in m.lower() and ("llama" in m.lower() or "3.2" in m):
                model_3b = m
            elif "8b" in m.lower() and ("llama" in m.lower() or "3.1" in m):
                model_8b = m
        
        if model_3b and model_8b:
            models = [model_3b, model_8b]
        elif available_models:
            models = [available_models[0]]
        else:
            print("[ERROR] No models available")
            return
    
    print(f"\n[INFO] Using models: {', '.join(models)}")
    
    # Fetch articles
    print(f"\n[INFO] Fetching {len(article_ids)} articles...")
    placeholders = ','.join(['%s'] * len(article_ids))
    query = f"""
        SELECT id, title, content, tickers, sentiment
        FROM research_articles
        WHERE id IN ({placeholders})
          AND content IS NOT NULL
    """
    
    articles = db_client.execute_query(query, tuple(article_ids))
    
    if not articles:
        print("[ERROR] No articles found with the provided IDs")
        return
    
    # Ensure we have content
    articles_with_content = []
    for article in articles:
        if article.get('content') and len(article.get('content', '')) > 200:
            articles_with_content.append(article)
        else:
            # Fetch full content
            article_id = article.get('id')
            if article_id:
                content_query = "SELECT content FROM research_articles WHERE id = %s"
                content_result = db_client.execute_query(content_query, (article_id,))
                if content_result and content_result[0].get('content'):
                    article['content'] = content_result[0]['content']
                    if len(article['content']) > 200:
                        articles_with_content.append(article)
    
    if not articles_with_content:
        print("[ERROR] No articles with sufficient content found")
        return
    
    print(f"[OK] Found {len(articles_with_content)} articles with content")
    
    # Track stats
    model_stats = {}
    for model in models:
        model_stats[model] = {
            "success": 0,
            "fail": 0,
            "total_time": 0.0,
            "times": [],
            "claims_count": [],
            "sentiment_dist": {}
        }
    
    # Test each article with each model
    for i, article in enumerate(articles_with_content, 1):
        article_id = article['id']
        title = article.get('title', 'Untitled')
        content = article.get('content', '')
        
        print(f"\n{'='*80}")
        print(f"[{i}/{len(articles_with_content)}] Article: {title[:60]}")
        print(f"{'='*80}")
        
        for model_idx, model in enumerate(models, 1):
            print(f"\n--- Model {model_idx}/{len(models)}: {model} ---")
            
            # Analyze
            result, elapsed = test_prompt_on_article(
                ollama_client,
                content,
                title,
                custom_system_prompt=None,  # Use default prompt
                model=model
            )
            
            # Track stats
            stats = model_stats[model]
            stats["total_time"] += elapsed
            stats["times"].append(elapsed)
            
            # Display result
            display_result(result, title, elapsed, model)
            
            # Check if result is good
            if "error" not in result:
                sentiment = result.get("sentiment", "")
                valid_sentiments = ["VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"]
                if sentiment in valid_sentiments:
                    stats["success"] += 1
                    stats["sentiment_dist"][sentiment] = stats["sentiment_dist"].get(sentiment, 0) + 1
                    
                    # Track claims
                    claims = result.get("claims", [])
                    if isinstance(claims, list):
                        stats["claims_count"].append(len(claims))
                    
                    print(f"\n[OK] Result looks good! ({elapsed:.2f}s)")
                else:
                    stats["fail"] += 1
                    print(f"\n[WARN] Result has issues (invalid sentiment: {sentiment})")
            else:
                stats["fail"] += 1
                print(f"\n[ERROR] Analysis failed: {result.get('error', 'Unknown error')}")
        
        # Show comparison if multiple models
        if len(models) > 1:
            print(f"\n{'='*80}")
            print("Performance Comparison:")
            for model in models:
                stats = model_stats[model]
                avg_time = stats["total_time"] / (stats["success"] + stats["fail"]) if (stats["success"] + stats["fail"]) > 0 else 0
                avg_claims = sum(stats["claims_count"]) / len(stats["claims_count"]) if stats["claims_count"] else 0
                print(f"  {model}:")
                print(f"    Time: {stats['total_time']:.2f}s total, {avg_time:.2f}s avg")
                print(f"    Success: {stats['success']}/{stats['success'] + stats['fail']}")
                print(f"    Avg Claims: {avg_claims:.1f}")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("Final Test Summary")
    print("=" * 80)
    
    for model in models:
        stats = model_stats[model]
        total = stats["success"] + stats["fail"]
        success_rate = (stats["success"] / total * 100) if total > 0 else 0
        avg_time = stats["total_time"] / total if total > 0 else 0
        min_time = min(stats["times"]) if stats["times"] else 0
        max_time = max(stats["times"]) if stats["times"] else 0
        avg_claims = sum(stats["claims_count"]) / len(stats["claims_count"]) if stats["claims_count"] else 0
        
        print(f"\n{model}:")
        print(f"  Success Rate: {success_rate:.1f}% ({stats['success']}/{total})")
        print(f"  Time: {stats['total_time']:.2f}s total, {avg_time:.2f}s avg ({min_time:.2f}s - {max_time:.2f}s)")
        print(f"  Avg Claims per Article: {avg_claims:.1f}")
        if stats["sentiment_dist"]:
            print(f"  Sentiment Distribution: {dict(stats['sentiment_dist'])}")
    
    # Comparison summary
    if len(models) > 1:
        print(f"\n{'='*80}")
        print("Speed Comparison:")
        model1, model2 = models[0], models[1]
        stats1, stats2 = model_stats[model1], model_stats[model2]
        total1, total2 = stats1["success"] + stats1["fail"], stats2["success"] + stats2["fail"]
        avg1 = stats1["total_time"] / total1 if total1 > 0 else 0
        avg2 = stats2["total_time"] / total2 if total2 > 0 else 0
        
        if avg1 > 0 and avg2 > 0:
            if avg1 < avg2:
                speedup = avg2 / avg1
                print(f"  {model1}: {avg1:.2f}s avg")
                print(f"  {model2}: {avg2:.2f}s avg")
                print(f"  {model1} is {speedup:.2f}x faster")
            else:
                speedup = avg1 / avg2
                print(f"  {model1}: {avg1:.2f}s avg")
                print(f"  {model2}: {avg2:.2f}s avg")
                print(f"  {model2} is {speedup:.2f}x faster")
        
        print(f"\nQuality Comparison:")
        claims1 = sum(stats1["claims_count"]) / len(stats1["claims_count"]) if stats1["claims_count"] else 0
        claims2 = sum(stats2["claims_count"]) / len(stats2["claims_count"]) if stats2["claims_count"] else 0
        print(f"  {model1}: {claims1:.1f} avg claims")
        print(f"  {model2}: {claims2:.1f} avg claims")
        if claims2 > claims1:
            print(f"  {model2} extracts {claims2 - claims1:.1f} more claims on average")
        elif claims1 > claims2:
            print(f"  {model1} extracts {claims1 - claims2:.1f} more claims on average")
    
    print("=" * 80)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test specific articles with Chain of Thought analysis"
    )
    parser.add_argument(
        "article_ids",
        nargs="+",
        help="Article IDs (UUIDs) to test, space-separated"
    )
    parser.add_argument(
        "-m", "--models",
        nargs="+",
        help="Models to use (default: auto-detect 3b and 8b)"
    )
    
    args = parser.parse_args()
    
    test_articles_by_ids(args.article_ids, args.models)


if __name__ == "__main__":
    main()

