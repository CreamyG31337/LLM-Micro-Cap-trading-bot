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
from typing import Generator, Optional, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Default configuration from environment variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
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
            logger.debug("Ollama health check skipped: disabled")
            return False
        
        try:
            logger.debug(f"Checking Ollama health at {self.base_url}...")
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                logger.info(f"✅ Ollama health check successful: {self.base_url}")
                return True
            else:
                logger.warning(f"Ollama health check failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"❌ Ollama health check failed: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """List all available models in Ollama.
        
        Returns:
            List of model names
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


def list_available_models() -> List[str]:
    """List available Ollama models.
    
    Returns:
        List of model names
    """
    client = get_ollama_client()
    return client.list_available_models() if client else []

