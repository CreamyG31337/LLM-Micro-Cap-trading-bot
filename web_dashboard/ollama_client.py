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
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """List all available models in Ollama.
        
        Returns:
            List of model names
        """
        if not self.enabled:
            return []
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]
            return [m for m in models if m]  # Filter out empty strings
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    def query_ollama(
        self,
        prompt: str,
        context: str = "",
        model: str = "llama3",
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Query Ollama API with a prompt and optional context.
        
        Args:
            prompt: User prompt/question
            context: Additional context data (formatted portfolio data, etc.)
            model: Model name to use
            stream: Whether to stream the response
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt to set model behavior
            
        Yields:
            Response chunks as strings (streaming) or full response (non-streaming)
        """
        if not self.enabled:
            yield "AI assistant is currently disabled."
            return
        
        # Combine context and prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\nUser question: {prompt}"
        
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
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
            logger.error("Ollama request timed out")
            yield "Request timed out. Please try again with a shorter prompt or context."
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama API")
            yield "Cannot connect to AI assistant. Please check if Ollama is running."
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            yield f"AI assistant error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama: {e}")
            yield f"An error occurred: {str(e)}"
    
    def query_ollama_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3",
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[str, None, None]:
        """Query Ollama using chat API format.
        
        Args:
            messages: List of message dicts with "role" and "content" keys
            model: Model name to use
            stream: Whether to stream the response
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            
        Yields:
            Response chunks as strings
        """
        if not self.enabled:
            yield "AI assistant is currently disabled."
            return
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
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

