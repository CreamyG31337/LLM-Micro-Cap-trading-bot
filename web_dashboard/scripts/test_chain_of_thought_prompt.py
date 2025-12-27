#!/usr/bin/env python3
"""
Interactive script to test and iterate on Chain of Thought prompts.
Tests prompts on real articles and allows you to review results before continuing.
"""

import sys
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.ollama_client import OllamaClient, get_ollama_client, check_ollama_health
from web_dashboard.research_repository import ResearchRepository
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    # Remove markdown code blocks
    clean_text = re.sub(r'```json\s*|\s*```', '', text).strip()
    # Remove leading/trailing whitespace
    clean_text = clean_text.strip()
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise


def test_prompt_on_article(
    ollama_client: OllamaClient,
    article_content: str,
    article_title: str,
    custom_system_prompt: str = None,
    model: str = "llama3.2:3b"
) -> Tuple[dict, float]:
    """Test a prompt on a single article and return the result with timing.
    
    Returns:
        (result_dict, elapsed_seconds)
    """
    
    # Use custom prompt or default from ollama_client
    if custom_system_prompt:
        # Truncate content
        max_chars = 6000
        if len(article_content) > max_chars:
            article_content = article_content[:max_chars] + "..."
        
        # Get model settings
        model_settings = ollama_client.get_model_settings(model)
        effective_temp = model_settings.get('temperature', 0.3)
        effective_ctx = model_settings.get('num_ctx', 4096)
        effective_max_tokens = model_settings.get('num_predict', 1024)
        
        # Prepare request
        payload = {
            "model": model,
            "prompt": article_content,
            "stream": False,
            "system": custom_system_prompt,
            "options": {
                "temperature": effective_temp,
                "num_predict": effective_max_tokens,
                "num_ctx": effective_ctx
            }
        }
        
        try:
            start_time = time.time()
            response = ollama_client.session.post(
                f"{ollama_client.base_url}/api/generate",
                json=payload,
                timeout=ollama_client.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            raw_response = data.get("response", "").strip()
            elapsed = time.time() - start_time
            
            if not raw_response:
                return {"error": "Empty response from Ollama"}, elapsed
            
            # Parse JSON
            parsed = extract_json_from_response(raw_response)
            return parsed, elapsed
            
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0.0
            return {"error": str(e)}, elapsed
    else:
        # Use the existing generate_summary method
        start_time = time.time()
        result = ollama_client.generate_summary(article_content, model=model)
        elapsed = time.time() - start_time
        return result, elapsed


def display_result(result: dict, article_title: str, elapsed_time: float = None, model_name: str = None) -> None:
    """Display the analysis result in a readable format."""
    print("\n" + "=" * 80)
    model_label = f" [{model_name}]" if model_name else ""
    print(f"Article: {article_title[:60]}{model_label}")
    if elapsed_time is not None:
        print(f"Time: {elapsed_time:.2f}s")
    print("=" * 80)
    
    if "error" in result:
        print(f"[ERROR] Error: {result['error']}")
        return
    
    # Sentiment
    sentiment = result.get("sentiment", "N/A")
    sentiment_score = result.get("sentiment_score", 0.0)
    print(f"\n[Sentiment] {sentiment} (Score: {sentiment_score})")
    
    # Summary
    summary = result.get("summary", "")
    if summary:
        print(f"\n[Summary]")
        # Handle Unicode encoding issues
        try:
            summary_display = summary[:200] + "..." if len(summary) > 200 else summary
            print(f"   {summary_display}")
        except UnicodeEncodeError:
            # Fallback: encode to ASCII with error handling
            summary_display = summary[:200] + "..." if len(summary) > 200 else summary
            summary_display = summary_display.encode('ascii', 'ignore').decode('ascii')
            print(f"   {summary_display}")
    
    # Claims
    claims = result.get("claims", [])
    if claims:
        print(f"\n[Claims] ({len(claims)}):")
        for i, claim in enumerate(claims[:5], 1):
            try:
                claim_display = claim[:100] + "..." if len(claim) > 100 else claim
                print(f"   {i}. {claim_display}")
            except UnicodeEncodeError:
                claim_display = (claim[:100] + "..." if len(claim) > 100 else claim).encode('ascii', 'ignore').decode('ascii')
                print(f"   {i}. {claim_display}")
        if len(claims) > 5:
            print(f"   ... and {len(claims) - 5} more")
    
    # Fact Check
    fact_check = result.get("fact_check", "")
    if fact_check:
        print(f"\n[Fact Check]")
        try:
            fact_check_display = fact_check[:200] + "..." if len(fact_check) > 200 else fact_check
            print(f"   {fact_check_display}")
        except UnicodeEncodeError:
            fact_check_display = (fact_check[:200] + "..." if len(fact_check) > 200 else fact_check).encode('ascii', 'ignore').decode('ascii')
            print(f"   {fact_check_display}")
    
    # Conclusion
    conclusion = result.get("conclusion", "")
    if conclusion:
        print(f"\n[Conclusion]")
        try:
            conclusion_display = conclusion[:200] + "..." if len(conclusion) > 200 else conclusion
            print(f"   {conclusion_display}")
        except UnicodeEncodeError:
            conclusion_display = (conclusion[:200] + "..." if len(conclusion) > 200 else conclusion).encode('ascii', 'ignore').decode('ascii')
            print(f"   {conclusion_display}")
    
    # Validation
    print("\n" + "-" * 80)
    print("Validation:")
    valid_sentiments = ["VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"]
    if sentiment not in valid_sentiments:
        print(f"   [WARN] Invalid sentiment: {sentiment}")
    else:
        print(f"   [OK] Valid sentiment")
    
    if not isinstance(claims, list):
        print(f"   [WARN] Claims is not a list: {type(claims)}")
    else:
        print(f"   [OK] Claims is a list ({len(claims)} items)")
    
    if sentiment_score != get_sentiment_score(sentiment):
        print(f"   [WARN] Sentiment score mismatch: {sentiment_score} != {get_sentiment_score(sentiment)}")
    else:
        print(f"   [OK] Sentiment score matches")


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


def find_articles(
    repo: ResearchRepository,
    search_text: str = None,
    ticker: str = None,
    limit: int = 20
) -> List[Dict]:
    """Find articles by search text or ticker.
    
    Returns list of articles with id, title, tickers, etc.
    """
    try:
        if ticker:
            # Search by ticker
            articles = repo.get_articles_by_ticker(ticker, limit=limit)
        elif search_text:
            # Search by text
            articles = repo.search_articles(search_text, limit=limit)
        else:
            # Get recent articles
            query = """
                SELECT id, title, tickers, sector, article_type, source, 
                       published_at, fetched_at, sentiment
                FROM research_articles
                WHERE content IS NOT NULL
                  AND LENGTH(content) > 200
                ORDER BY fetched_at DESC
                LIMIT %s
            """
            articles = repo.client.execute_query(query, (limit,))
        
        return articles or []
    except Exception as e:
        print(f"[ERROR] Error finding articles: {e}")
        return []


def display_article_list(articles: List[Dict], show_ids: bool = True) -> None:
    """Display a list of articles for selection."""
    if not articles:
        print("[INFO] No articles found")
        return
    
    print(f"\nFound {len(articles)} articles:\n")
    for i, article in enumerate(articles, 1):
        article_id = str(article.get('id', 'N/A'))
        title = article.get('title', 'Untitled')[:70]
        tickers = article.get('tickers', [])
        if isinstance(tickers, str):
            tickers = [tickers] if tickers else []
        ticker_str = ', '.join(tickers) if tickers else 'N/A'
        sentiment = article.get('sentiment', 'N/A')
        published = article.get('published_at', article.get('fetched_at', 'N/A'))
        
        id_display = f"ID: {article_id[:8]}..." if show_ids and len(article_id) > 8 else f"ID: {article_id}" if show_ids else ""
        print(f"  {i}. {title}")
        print(f"     Tickers: {ticker_str} | Sentiment: {sentiment} | {id_display}")
        if show_ids:
            print(f"     Full ID: {article_id}")
        print()


def main():
    """Main interactive testing loop."""
    print("=" * 80)
    print("Chain of Thought Prompt Tester")
    print("=" * 80)
    
    # Check Ollama
    if not check_ollama_health():
        print("[ERROR] Ollama is not available. Please start Ollama first.")
        return
    
    # Initialize clients
    try:
        db_client = PostgresClient()
        repo = ResearchRepository()
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("[ERROR] Failed to initialize Ollama client")
            return
    except Exception as e:
        print(f"[ERROR] Error initializing clients: {e}")
        return
    
    # Article selection mode
    print("\n" + "=" * 80)
    print("Article Selection")
    print("=" * 80)
    print("1. Use random articles (default - 5 articles missing Chain of Thought)")
    print("2. Search by text/keywords")
    print("3. Search by ticker")
    print("4. Enter specific article IDs (comma-separated)")
    print("5. Show recent articles and pick manually")
    
    is_interactive = sys.stdin.isatty()
    
    if is_interactive:
        try:
            selection_mode = input("\nSelection mode (1-5, default=1): ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            selection_mode = "1"
            is_interactive = False
    else:
        selection_mode = "1"
        print("\n[INFO] Non-interactive mode: using random articles")
    
    articles = []
    
    if selection_mode == "2":
        # Search by text
        if is_interactive:
            search_text = input("Search text (e.g., 'Meta Platforms', 'bargain', 'bullish'): ").strip()
        else:
            search_text = "Meta Platforms"
            print(f"[INFO] Using search: {search_text}")
        
        if search_text:
            found = find_articles(repo, search_text=search_text, limit=20)
            display_article_list(found)
            
            if is_interactive and found:
                selection = input("\nEnter article numbers (comma-separated, e.g., 1,3,5) or 'all': ").strip()
                if selection.lower() == 'all':
                    articles = found
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in selection.split(',')]
                        articles = [found[i] for i in indices if 0 <= i < len(found)]
                    except ValueError:
                        print("[ERROR] Invalid selection")
                        return
            else:
                articles = found[:5]  # Take first 5 in non-interactive mode
    
    elif selection_mode == "3":
        # Search by ticker
        if is_interactive:
            ticker = input("Ticker symbol (e.g., META, NVDA): ").strip().upper()
        else:
            ticker = "META"
            print(f"[INFO] Using ticker: {ticker}")
        
        if ticker:
            found = find_articles(repo, ticker=ticker, limit=20)
            display_article_list(found)
            
            if is_interactive and found:
                selection = input("\nEnter article numbers (comma-separated) or 'all': ").strip()
                if selection.lower() == 'all':
                    articles = found
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in selection.split(',')]
                        articles = [found[i] for i in indices if 0 <= i < len(found)]
                    except ValueError:
                        print("[ERROR] Invalid selection")
                        return
            else:
                articles = found[:5]
    
    elif selection_mode == "4":
        # Specific IDs
        if is_interactive:
            ids_input = input("Article IDs (comma-separated UUIDs): ").strip()
        else:
            ids_input = ""
            print("[INFO] No IDs provided in non-interactive mode")
        
        if ids_input:
            ids = [x.strip() for x in ids_input.split(',')]
            placeholders = ','.join(['%s'] * len(ids))
            query = f"""
                SELECT id, title, content, tickers, sentiment
                FROM research_articles
                WHERE id IN ({placeholders})
                  AND content IS NOT NULL
            """
            articles = db_client.execute_query(query, tuple(ids))
    
    elif selection_mode == "5":
        # Show recent and pick
        found = find_articles(repo, limit=20)
        display_article_list(found)
        
        if is_interactive and found:
            selection = input("\nEnter article numbers (comma-separated): ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                articles = [found[i] for i in indices if 0 <= i < len(found)]
            except ValueError:
                print("[ERROR] Invalid selection")
                return
        else:
            articles = found[:5]
    
    else:
        # Default: random articles missing Chain of Thought
        print("\n[INFO] Fetching articles missing Chain of Thought analysis...")
        query = """
            SELECT id, title, content, tickers, sentiment
            FROM research_articles 
            WHERE sentiment IS NULL 
              AND content IS NOT NULL 
              AND LENGTH(content) > 200
            ORDER BY fetched_at DESC
            LIMIT 5
        """
        articles = db_client.execute_query(query)
    
    if not articles:
        print("[ERROR] No articles found to test.")
        return
    
    # Ensure we have content for all articles
    articles_with_content = []
    for article in articles:
        if not article.get('content'):
            # Fetch full content if missing
            article_id = article.get('id')
            if article_id:
                content_query = "SELECT content FROM research_articles WHERE id = %s"
                content_result = db_client.execute_query(content_query, (article_id,))
                if content_result and content_result[0].get('content'):
                    article['content'] = content_result[0]['content']
        
        if article.get('content') and len(article.get('content', '')) > 200:
            articles_with_content.append(article)
    
    articles = articles_with_content
    
    if not articles:
        print("[ERROR] No articles with content found to test.")
        return
    
    print(f"\n[OK] Selected {len(articles)} articles to test")
    
    # Prompt selection
    print("\n" + "=" * 80)
    print("Prompt Selection:")
    print("1. Use current prompt from ollama_client.py (default)")
    print("2. Use custom prompt (paste or type)")
    print("3. Use simplified test prompt")
    
    if is_interactive:
        try:
            choice = input("\nChoice (1-3, default=1): ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Non-interactive mode detected: using default prompt (option 1)")
            choice = "1"
            is_interactive = False
    else:
        print("\n[INFO] Non-interactive mode: using default prompt (option 1)")
        choice = "1"
    
    custom_prompt = None
    if choice == "2":
        if is_interactive:
            print("\nPaste your custom system prompt (end with empty line or Ctrl+D):")
            lines = []
            try:
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
            except EOFError:
                pass
            custom_prompt = "\n".join(lines)
        else:
            print("[WARN] Custom prompt not supported in non-interactive mode, using default")
            choice = "1"
    elif choice == "3":
        custom_prompt = """You are a skeptical financial analyst. Analyze the following article in 3 steps:

Step 1 - Identify Claims: Extract specific numbers, dates, percentages, and causal claims.

Step 2 - Fact Check: Are claims plausible? Any obvious contradictions? Filter garbage/clickbait.

Step 3 - Conclusion: What's the net impact on the stock ticker(s)?

Categorize sentiment: VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, or VERY_BEARISH.

Return ONLY valid JSON:
{
  "summary": "Brief summary...",
  "claims": ["Claim 1", "Claim 2"],
  "fact_check": "Fact-checking analysis...",
  "conclusion": "Net impact...",
  "sentiment": "NEUTRAL"
}"""
    
    # Model selection
    models = ollama_client.get_filtered_models()
    if not models:
        print("[ERROR] No models available")
        return
    
    print(f"\nAvailable models: {', '.join(models)}")
    
    # Model selection - support comparison mode
    if is_interactive:
        print("\nModel Selection:")
        print("1. Single model")
        print("2. Compare two models (3b vs 8b)")
        mode_choice = input("Mode (1-2, default=2): ").strip() or "2"
    else:
        mode_choice = "2"  # Default to comparison mode
        print("\n[INFO] Using comparison mode (3b vs 8b)")
    
    if mode_choice == "2":
        # Comparison mode: find 3b and 8b models
        model_3b = None
        model_8b = None
        
        for m in models:
            if "3b" in m.lower() and ("llama" in m.lower() or "3.2" in m):
                model_3b = m
            elif "8b" in m.lower() and ("llama" in m.lower() or "3.1" in m or "3.2" in m):
                model_8b = m
        
        if not model_3b:
            # Try any 3b model
            for m in models:
                if "3b" in m.lower():
                    model_3b = m
                    break
        
        if not model_8b:
            # Try any 8b model
            for m in models:
                if "8b" in m.lower():
                    model_8b = m
                    break
        
        if not model_3b or not model_8b:
            print(f"[WARN] Could not find both 3b and 8b models")
            print(f"  3b models found: {[m for m in models if '3b' in m.lower()]}")
            print(f"  8b models found: {[m for m in models if '8b' in m.lower()]}")
            if model_3b:
                print(f"[INFO] Using single model: {model_3b}")
                model_list = [model_3b]
            elif model_8b:
                print(f"[INFO] Using single model: {model_8b}")
                model_list = [model_8b]
            else:
                print(f"[INFO] Using first available model: {models[0]}")
                model_list = [models[0]]
        else:
            model_list = [model_3b, model_8b]
            print(f"[INFO] Comparing: {model_3b} vs {model_8b}")
    else:
        # Single model mode
        if is_interactive:
            model = input(f"Model (default={models[0]}): ").strip() or models[0]
        else:
            model = models[0]
        model_list = [model]
        print(f"[INFO] Using model: {model}")
    
    # Test loop
    print("\n" + "=" * 80)
    print("Testing Articles")
    print("=" * 80)
    
    # Performance tracking
    model_stats: Dict[str, Dict] = {}
    for model in model_list:
        model_stats[model] = {
            "success": 0,
            "fail": 0,
            "total_time": 0.0,
            "times": [],
            "claims_count": [],
            "sentiment_dist": {}
        }
    
    for i, article in enumerate(articles, 1):
        article_id = article['id']
        title = article.get('title', 'Untitled')
        content = article.get('content', '')
        
        if not content:
            print(f"\n[{i}/{len(articles)}] [SKIP] Skipping {title[:50]}... (no content)")
            continue
        
        print(f"\n{'='*80}")
        print(f"[{i}/{len(articles)}] Article: {title[:60]}")
        print(f"{'='*80}")
        
        # Test each model
        for model_idx, model in enumerate(model_list, 1):
            print(f"\n--- Model {model_idx}/{len(model_list)}: {model} ---")
            
            # Analyze
            result, elapsed = test_prompt_on_article(
                ollama_client,
                content,
                title,
                custom_system_prompt=custom_prompt,
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
        if len(model_list) > 1:
            print(f"\n{'='*80}")
            print("Performance Comparison:")
            for model in model_list:
                stats = model_stats[model]
                avg_time = stats["total_time"] / (stats["success"] + stats["fail"]) if (stats["success"] + stats["fail"]) > 0 else 0
                avg_claims = sum(stats["claims_count"]) / len(stats["claims_count"]) if stats["claims_count"] else 0
                print(f"  {model}:")
                print(f"    Time: {stats['total_time']:.2f}s total, {avg_time:.2f}s avg")
                print(f"    Success: {stats['success']}/{stats['success'] + stats['fail']}")
                print(f"    Avg Claims: {avg_claims:.1f}")
        
        # User decision (only in interactive mode)
        if i < len(articles) and is_interactive:
            try:
                user_input = input("\nContinue? (Enter=yes, q=quit, s=skip): ").strip().lower()
                if user_input == 'q':
                    print("\n[INFO] Exiting early...")
                    break
                elif user_input == 's':
                    print("\n[INFO] Skipping remaining articles...")
                    break
            except (EOFError, KeyboardInterrupt):
                # If input fails, switch to non-interactive mode
                is_interactive = False
                print("\n[INFO] Switching to non-interactive mode, continuing automatically...")
        elif i < len(articles):
            # Non-interactive: continue automatically
            print()
    
    # Final Summary
    print("\n" + "=" * 80)
    print("Final Test Summary")
    print("=" * 80)
    
    for model in model_list:
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
    if len(model_list) > 1:
        print(f"\n{'='*80}")
        print("Speed Comparison:")
        model1, model2 = model_list[0], model_list[1]
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


if __name__ == "__main__":
    main()

