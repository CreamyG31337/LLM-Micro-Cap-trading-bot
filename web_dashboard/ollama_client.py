#!/usr/bin/env python3
"""
Ollama API Client
=================

HTTP client for interacting with Ollama API running in Docker.
Supports streaming responses for real-time chat.
"""

import os
import json
import logging
import time
from typing import Generator, Optional, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This allows local development with .env file, but Docker/CI can override with actual env vars
load_dotenv()

logger = logging.getLogger(__name__)

# Default configuration from environment variables
# Priority: Docker env vars > .env file > Python defaults
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL (defaults to environment variable)
            timeout: Request timeout in seconds (defaults to environment variable)
        """
        self.base_url = base_url or OLLAMA_BASE_URL
        self.timeout = timeout or OLLAMA_TIMEOUT
        self.enabled = OLLAMA_ENABLED
        
        logger.info(f"Ollama client initialized: base_url={self.base_url}, timeout={self.timeout}s, enabled={self.enabled}")
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Load model configuration
        self.model_config = self._load_model_config()

    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration from JSON file.
        
        Returns:
            Dict containing model settings
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'model_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded configuration for {len(config.get('models', {}))} models")
                    return config
            else:
                logger.warning(f"Model config file not found at {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading model config: {e}")
            return {}

    def get_model_settings(self, model_name: str) -> Dict[str, Any]:
        """Get settings for specific model.
        
        Checks database for admin overrides first, then falls back to JSON config.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dict with settings (num_ctx, temperature, num_predict, etc.)
        """
        models = self.model_config.get('models', {})
        default_config = self.model_config.get('default_config', {})
        
        # Start with JSON defaults (exact match or global defaults)
        if model_name in models:
            settings = models[model_name].copy()
        else:
            settings = default_config.copy()
        
        # Check database for admin overrides
        try:
            from settings import get_system_setting
            
            # Check for temperature override
            db_temp = get_system_setting(f"model_{model_name}_temperature", default=None)
            if db_temp is not None:
                settings['temperature'] = db_temp
            
            # Check for context window override
            db_ctx = get_system_setting(f"model_{model_name}_num_ctx", default=None)
            if db_ctx is not None:
                settings['num_ctx'] = db_ctx
            
            # Check for max tokens override
            db_predict = get_system_setting(f"model_{model_name}_num_predict", default=None)
            if db_predict is not None:
                settings['num_predict'] = db_predict
                
        except Exception as e:
            logger.debug(f"Could not load database overrides for {model_name}: {e}")
        
        return settings
        
    def get_model_description(self, model_name: str) -> str:
        """Get description for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Description string
        """
        settings = self.get_model_settings(model_name)
        return settings.get('desc', '')
    
    def check_health(self) -> bool:
        """Check if Ollama API is available.
        
        Returns:
            True if Ollama is reachable, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Ollama health check failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"❌ Ollama health check failed: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """List all available models in Ollama (unfiltered).
        
        Returns:
            List of all model names from Ollama
        """
        if not self.enabled:
            logger.debug("Model listing skipped: Ollama disabled")
            return []
        
        try:
            logger.debug(f"Fetching available models from {self.base_url}...")
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]
            models = [m for m in models if m]  # Filter out empty strings
            logger.info(f"Found {len(models)} Ollama models: {', '.join(models) if models else 'none'}")
            return models
        except Exception as e:
            logger.error(f"❌ Error listing Ollama models: {e}")
            return []
    
    def get_filtered_models(self, include_hidden: bool = False) -> List[str]:
        """Get list of available models, filtered by JSON config.
        
        Filters out models marked as "hidden": true in model_config.json.
        Models not in the JSON config are included by default (backward compatibility).
        
        Args:
            include_hidden: If True, include models marked as hidden
            
        Returns:
            List of model names (filtered)
        """
        all_models = self.list_available_models()
        config_models = self.model_config.get('models', {})
        
        filtered = []
        for model in all_models:
            # If model not in config, include it (backward compatibility)
            if model not in config_models:
                filtered.append(model)
                continue
            
            # Model is in config - check if it's hidden
            model_config = config_models.get(model, {})
            is_hidden = model_config.get('hidden', False)
            
            # Include if not hidden, or if include_hidden=True
            if not is_hidden or include_hidden:
                filtered.append(model)
        
        logger.debug(f"Filtered {len(all_models)} models to {len(filtered)} visible models")
        return filtered
    
    def query_ollama(
        self,
        prompt: str,
        context: str = "",
        model: str = "llama3",
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Query Ollama API with a prompt and optional context.
        
        Args:
            prompt: User prompt/question
            context: Additional context data (formatted portfolio data, etc.)
            model: Model name to use
            stream: Whether to stream the response
            temperature: Model temperature (0.0-1.0). If None, uses model default.
            max_tokens: Maximum tokens in response (num_predict)
            num_ctx: Context window size. If None, uses model default.
            system_prompt: Optional system prompt to set model behavior
            
        Yields:
            Response chunks as strings (streaming) or full response (non-streaming)
        """
        if not self.enabled:
            logger.warning("Ollama query rejected: AI assistant disabled")
            yield "AI assistant is currently disabled."
            return
        
        # Combine context and prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\nUser question: {prompt}"
        
        # Get model-specific defaults if values not provided
        model_settings = self.get_model_settings(model)
        
        # Use provided values, or model specific defaults, or global defaults
        effective_temp = temperature if temperature is not None else model_settings.get('temperature', 0.7)
        effective_ctx = num_ctx if num_ctx is not None else model_settings.get('num_ctx', 4096)
        effective_max_tokens = max_tokens if max_tokens is not None else model_settings.get('num_predict', 2048)
        
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "temperature": effective_temp,
                "num_predict": effective_max_tokens,
                "num_ctx": effective_ctx
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.info(f"Ollama query: model={model}, temp={effective_temp}, ctx={effective_ctx}, max_tokens={effective_max_tokens}, stream={stream}")
            logger.debug(f"Prompt length: {len(full_prompt)} chars")
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug("Ollama response received, streaming...")
            
            if stream:
                # Stream response chunks
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            if "response" in chunk_data:
                                yield chunk_data["response"]
                            if chunk_data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                # Return full response
                data = response.json()
                yield data.get("response", "")
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Ollama request timed out after {self.timeout}s")
            yield "Request timed out. Please try again with a shorter prompt or context."
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Cannot connect to Ollama API at {self.base_url}: {e}")
            yield "Cannot connect to AI assistant. Please check if Ollama is running."
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Ollama API HTTP error: {e}")
            yield f"AI assistant error: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Unexpected error querying Ollama: {e}", exc_info=True)
            yield f"An error occurred: {str(e)}"
    
    def generate_summary(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate a comprehensive summary with Chain of Thought analysis and sentiment categorization.
        
        Uses a 3-step Chain of Thought process: Identify Claims, Fact Check, Conclusion.
        Also categorizes sentiment (VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, VERY_BEARISH).
        
        Args:
            text: Text to summarize (will be truncated to ~6000 chars)
            model: Model name to use. If None, uses get_summarizing_model() from settings.
            
        Returns:
            Dictionary containing:
            - summary: Enhanced text summary (5-7+ bullet points)
            - claims: List of specific claims with numbers/dates extracted from article
            - fact_check: Simple fact-checking analysis (filters garbage/clickbait)
            - conclusion: Net impact on ticker(s) with specific implications
            - sentiment: One of "VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"
            - sentiment_score: Numeric score for calculations (VERY_BULLISH=2.0, BULLISH=1.0, NEUTRAL=0.0, BEARISH=-1.0, VERY_BEARISH=-2.0)
            - tickers: List of ticker symbols mentioned (e.g., ["HOOD", "NVDA"])
            - sectors: List of sectors mentioned (e.g., ["Financial Services", "Technology"])
            - key_themes: List of key themes/topics
            - companies: List of company names mentioned
            
            Returns empty dict if generation fails or AI is disabled.
        """
        if not self.enabled:
            logger.warning("Ollama summary generation rejected: AI assistant disabled")
            return {}
        
        # Get model from settings if not provided
        if model is None:
            try:
                from settings import get_summarizing_model
                model = get_summarizing_model()
            except Exception as e:
                logger.warning(f"Could not load summarizing model from settings: {e}, using fallback")
                model = "granite3.3:8b"
        
        # Truncate text to ~6000 characters
        max_chars = 6000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.debug(f"Truncated text to {max_chars} characters for summarization")
        
        # Enhanced system prompt with Chain of Thought reasoning and sentiment categorization
        system_prompt = """You are a skeptical financial analyst. Analyze the following article using a 3-step Chain of Thought process, then provide a comprehensive analysis in JSON format.

ANALYSIS PROCESS (Chain of Thought):
Step 1 - Identify Claims: Extract specific numbers, dates, percentages, and causal claims made in the article. List all factual assertions with concrete data points.

Step 2 - Fact Check: Perform simple fact-checking to filter out garbage and clickbait. Ask yourself:
- Are the claims plausible? (e.g., "stock up 1000%" is likely clickbait)
- Are there obvious contradictions within the article?
- Does the headline match the content?
- Are there red flags (e.g., "guaranteed returns", "secret method")?
Keep this simple - you're a fact checker, not a PhD economist. Focus on filtering obvious noise.

Step 3 - Conclusion: Summarize the net impact on the stock ticker(s). What does this article actually mean for the stock? Be specific about potential price impact or business implications.

SENTIMENT CATEGORIZATION:
Categorize the article's sentiment into exactly ONE of these buckets:
- "VERY_BULLISH" - Game-changing positive news (e.g., massive earnings beat, breakthrough product, major acquisition)
- "BULLISH" - Good news (e.g., price target upgrade, partnership announcement, positive guidance)
- "NEUTRAL" - Noise, standard reporting, mixed results, routine updates
- "BEARISH" - Bad news (e.g., missed earnings, minor lawsuit, downgrade)
- "VERY_BEARISH" - Catastrophic news (e.g., fraud investigation, CEO fired, bankruptcy filing)

Most articles should be "NEUTRAL" - only categorize as BULLISH/BEARISH if there's significant news.

EXTRACTION REQUIREMENTS:
1. Generate a comprehensive summary with 5-7+ bullet points covering all key information
2. Extract all stock ticker symbols mentioned (e.g., HOOD, NVDA, AAPL, XMA.TO)
   - Tickers are SHORT symbols (1-10 characters), typically 1-5 uppercase letters
   - May include exchange suffixes like .TO, .V, .CN, .TSX
   - Do NOT extract company names (e.g., "Apple Inc" is NOT a ticker, "AAPL" is)
   - Do NOT extract long phrases or descriptions
   - First, look for explicit ticker symbols mentioned in the article
   - If no explicit tickers found BUT the article is clearly about specific companies, infer the likely ticker(s)
   - For well-known companies, provide your best guess of the ticker symbol
   - If you're uncertain about a ticker, add a '?' suffix (e.g., "RKLB?" for Rocket Lab)
   - Examples: "Apple" → "AAPL", "Microsoft" → "MSFT", "Tesla" → "TSLA", "NVIDIA" → "NVDA"
3. Identify all sectors/industries discussed (e.g., "Financial Services", "Technology", "Healthcare")
4. List key themes and topics (e.g., "crypto revenue", "subscription growth", "market expansion")
5. Extract company names mentioned (e.g., "Robinhood", "NVIDIA") - these go in "companies" field, NOT "tickers"

CRITICAL: Return ONLY valid, parseable JSON. Do NOT include:
- Explanatory text before or after the JSON
- Comments (// or /* */)
- Markdown formatting
- Any text outside the JSON object

The "summary" field must be a single STRING with bullet points separated by newlines (\\n), NOT an array.

Return your response as a valid JSON object with these exact fields:
{
  "summary": "• First key point...\\n• Second key point...\\n• Third key point...\\n• Fourth key point...\\n• Fifth key point...",
  "claims": ["Claim 1 with specific numbers/dates", "Claim 2 with percentages", "Claim 3..."],
  "fact_check": "Simple fact-checking analysis: Are claims plausible? Any obvious contradictions? Filter garbage/clickbait.",
  "conclusion": "Net impact on ticker(s): What does this article mean for the stock? Specific price impact or business implications.",
  "sentiment": "VERY_BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "VERY_BEARISH",
  "tickers": ["TICKER1", "TICKER2", "INFERRED?"],
  "sectors": ["Sector1", "Sector2"],
  "key_themes": ["theme1", "theme2"],
  "companies": ["Company1", "Company2"]
}

If no tickers, sectors, themes, or companies are found, use empty arrays []. The sentiment field is REQUIRED and must be exactly one of the 5 values listed above. Return ONLY the JSON object, nothing else."""
        
        # Get model settings
        model_settings = self.get_model_settings(model)
        effective_temp = model_settings.get('temperature', 0.3)
        effective_ctx = model_settings.get('num_ctx', 4096)
        effective_max_tokens = model_settings.get('num_predict', 1024)  # Increased for more comprehensive summaries
        
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": text,
            "stream": False,
            "system": system_prompt,
            "options": {
                "temperature": effective_temp,
                "num_predict": effective_max_tokens,
                "num_ctx": effective_ctx
            }
        }
        
        try:
            start_time = time.time()
            logger.info(f"Generating enhanced summary with model {model}")
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Summary generated in {elapsed_time:.2f}s")
            
            data = response.json()
            raw_response = data.get("response", "").strip()
            
            if not raw_response:
                logger.warning("Empty response from Ollama")
                return {}
            
            # Try to parse JSON response
            try:
                # Try to extract JSON from response (might have markdown code blocks)
                json_str = raw_response
                if "```json" in json_str:
                    # Extract JSON from markdown code block
                    start = json_str.find("```json") + 7
                    end = json_str.find("```", start)
                    if end > start:
                        json_str = json_str[start:end].strip()
                elif "```" in json_str:
                    # Extract JSON from generic code block
                    start = json_str.find("```") + 3
                    end = json_str.find("```", start)
                    if end > start:
                        json_str = json_str[start:end].strip()
                
                parsed = json.loads(json_str)
                
                # Helper function to safely extract string values from lists
                def extract_strings(value, default=[]):
                    """Extract string values from a list, handling mixed types."""
                    if not isinstance(value, list):
                        return default
                    result = []
                    for item in value:
                        if isinstance(item, str) and item.strip():
                            result.append(item.strip())
                        elif isinstance(item, (int, float)):
                            # Convert numbers to strings
                            result.append(str(item).strip())
                    return result
                
                # Validate and normalize structure
                summary_text = parsed.get("summary", "")
                if not isinstance(summary_text, str):
                    summary_text = str(summary_text) if summary_text else ""
                
                # Extract Chain of Thought fields
                claims = extract_strings(parsed.get("claims", []))
                fact_check = parsed.get("fact_check", "")
                if not isinstance(fact_check, str):
                    fact_check = str(fact_check) if fact_check else ""
                
                conclusion = parsed.get("conclusion", "")
                if not isinstance(conclusion, str):
                    conclusion = str(conclusion) if conclusion else ""
                
                # Extract sentiment (validate it's one of the allowed values)
                sentiment = parsed.get("sentiment", "NEUTRAL")
                if not isinstance(sentiment, str):
                    sentiment = str(sentiment) if sentiment else "NEUTRAL"
                sentiment = sentiment.strip().upper()
                valid_sentiments = ["VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"]
                if sentiment not in valid_sentiments:
                    logger.warning(f"Invalid sentiment '{sentiment}', defaulting to NEUTRAL")
                    sentiment = "NEUTRAL"
                
                # Calculate sentiment_score for database calculations (avoids CASE WHEN in queries)
                # Mapping: VERY_BULLISH=2.0, BULLISH=1.0, NEUTRAL=0.0, BEARISH=-1.0, VERY_BEARISH=-2.0
                sentiment_score_map = {
                    "VERY_BULLISH": 2.0,
                    "BULLISH": 1.0,
                    "NEUTRAL": 0.0,
                    "BEARISH": -1.0,
                    "VERY_BEARISH": -2.0
                }
                sentiment_score = sentiment_score_map.get(sentiment, 0.0)
                
                result = {
                    "summary": summary_text.strip(),
                    "claims": claims,
                    "fact_check": fact_check.strip(),
                    "conclusion": conclusion.strip(),
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "tickers": [t.upper() for t in extract_strings(parsed.get("tickers", []))],
                    "sectors": extract_strings(parsed.get("sectors", [])),
                    "key_themes": extract_strings(parsed.get("key_themes", [])),
                    "companies": extract_strings(parsed.get("companies", []))
                }
                
                logger.debug(f"Generated summary: {len(result['summary'])} chars, {len(result['tickers'])} tickers, {len(result['sectors'])} sectors, sentiment: {result['sentiment']}")
                logger.debug(f"Extracted tickers: {result['tickers']}, sectors: {result['sectors']}")
                logger.debug(f"Claims: {len(result['claims'])} items, Fact check: {len(result['fact_check'])} chars, Conclusion: {len(result['conclusion'])} chars")
                
                return result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response, falling back to text-only summary: {e}")
                logger.debug(f"Raw response: {raw_response[:500]}")
                # Fallback: return text summary only with default values for new fields
                return {
                    "summary": raw_response,
                    "claims": [],
                    "fact_check": "",
                    "conclusion": "",
                    "sentiment": "NEUTRAL",
                    "sentiment_score": 0.0,
                    "tickers": [],
                    "sectors": [],
                    "key_themes": [],
                    "companies": []
                }
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Ollama summary request timed out after {self.timeout}s")
            return {}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Cannot connect to Ollama API at {self.base_url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}", exc_info=True)
            return {}
    
    def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """Generate embedding vector for text using Ollama embedding API.
        
        Args:
            text: Text to generate embedding for
            model: Embedding model name (defaults to nomic-embed-text)
            
        Returns:
            List of floats (768 dimensions for nomic-embed-text)
        """
        if not self.enabled:
            logger.warning("Ollama embedding generation rejected: AI assistant disabled")
            return []
        
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": text
        }
        
        try:
            logger.debug(f"Generating embedding with model {model}")
            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            if not embedding:
                logger.warning(f"No embedding returned from model {model}")
                return []
            
            logger.debug(f"Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Ollama embedding request timed out after {self.timeout}s")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Cannot connect to Ollama API at {self.base_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}", exc_info=True)
            return []
    
    def query_ollama_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3",
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
        num_ctx: Optional[int] = None
    ) -> Generator[str, None, None]:
        """Query Ollama using chat API format.
        
        Args:
            messages: List of message dicts with "role" and "content" keys
            model: Model name to use
            stream: Whether to stream the response
            temperature: Model temperature (0.0-1.0). If None, uses model default.
            max_tokens: Maximum tokens in response
            num_ctx: Context window size. If None, uses model default.
            
        Yields:
            Response chunks as strings
        """
        if not self.enabled:
            yield "AI assistant is currently disabled."
            return
        
        # Get model-specific defaults if values not provided
        model_settings = self.get_model_settings(model)
        
        # Use provided values, or model specific defaults, or global defaults
        effective_temp = temperature if temperature is not None else model_settings.get('temperature', 0.7)
        effective_ctx = num_ctx if num_ctx is not None else model_settings.get('num_ctx', 4096)
        effective_max_tokens = max_tokens if max_tokens is not None else model_settings.get('num_predict', 2048)
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": effective_temp,
                "num_predict": effective_max_tokens,
                "num_ctx": effective_ctx
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            if "message" in chunk_data and "content" in chunk_data["message"]:
                                yield chunk_data["message"]["content"]
                            if chunk_data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                data = response.json()
                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]
                    
        except Exception as e:
            logger.error(f"Error in chat API: {e}")
            yield f"An error occurred: {str(e)}"


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> Optional[OllamaClient]:
    """Get or create global Ollama client instance.
    
    Returns:
        OllamaClient instance or None if disabled
    """
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client if _ollama_client.enabled else None


def check_ollama_health() -> bool:
    """Check if Ollama is available.
    
    Returns:
        True if Ollama is reachable
    """
    client = get_ollama_client()
    return client.check_health() if client else False


def list_available_models(include_hidden: bool = False) -> List[str]:
    """List available Ollama models, filtered by JSON config.
    
    By default, excludes models marked as "hidden": true in model_config.json.
    Models not in the JSON config are included (backward compatibility).
    
    Args:
        include_hidden: If True, include models marked as hidden
        
    Returns:
        List of model names (filtered)
    """
    client = get_ollama_client()
    if client:
        return client.get_filtered_models(include_hidden=include_hidden)
    return []

