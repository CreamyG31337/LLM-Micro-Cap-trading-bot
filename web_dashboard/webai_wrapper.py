#!/usr/bin/env python3
"""
WebAI Service Wrapper
=====================

Wrapper for web-based AI service access using cookie authentication.
Integrates with obfuscated system and maintains privacy.
"""

import sys
import json
import asyncio
import os
import time
from pathlib import Path
from typing import Optional, Tuple, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

try:
    # Import third-party package for web interface access
    from gemini_webapi import GeminiClient as WebAPIClient, set_log_level
    HAS_WEBAPI_PACKAGE = True
except ImportError:
    HAS_WEBAPI_PACKAGE = False
    WebAPIClient = None


def _load_cookies() -> Tuple[Optional[str], Optional[str]]:
    """
    Load cookies from environment variables (Woodpecker secrets) or files.
    
    Priority:
    1. Environment variables (WEBAI_COOKIES_JSON or individual vars)
    2. Cookie files (webai_cookies.json, ai_service_cookies.json)
    
    Returns:
        Tuple of (secure_1psid, secure_1psidts) or (None, None) if not found
    """
    # Try environment variables first (for Woodpecker secrets/production)
    # Option 1: JSON string in single env var
    cookies_json = os.getenv("WEBAI_COOKIES_JSON")
    if cookies_json:
        try:
            cookies = json.loads(cookies_json)
            secure_1psid = cookies.get("__Secure-1PSID")
            secure_1psidts = cookies.get("__Secure-1PSIDTS")
            if secure_1psid:
                return (secure_1psid, secure_1psidts)
        except Exception:
            pass
    
    # Option 2: Individual environment variables
    secure_1psid = os.getenv("WEBAI_SECURE_1PSID")
    secure_1psidts = os.getenv("WEBAI_SECURE_1PSIDTS")
    if secure_1psid:
        return (secure_1psid, secure_1psidts)
    
    # Fallback: Try cookie files (for local development)
    cookie_names = ["webai_cookies.json", "ai_service_cookies.json"]
    
    for name in cookie_names:
        root_cookie = project_root / name
        web_cookie = project_root / "web_dashboard" / name
        
        for cookie_file in [root_cookie, web_cookie]:
            if cookie_file.exists():
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                    
                    secure_1psid = cookies.get("__Secure-1PSID")
                    secure_1psidts = cookies.get("__Secure-1PSIDTS")
                    
                    if secure_1psid:
                        return (secure_1psid, secure_1psidts)
                except Exception as e:
                    continue
    
    return (None, None)


class WebAIClient:
    """
    Wrapper for web-based AI service access using cookie authentication.
    
    Maintains obfuscation layer while using third-party package for communication.
    """
    
    def __init__(self, cookies_file: Optional[str] = None, auto_refresh: bool = False):
        """
        Initialize the WebAI client.
        
        Args:
            cookies_file: Optional path to cookie file (auto-detected if not provided)
            auto_refresh: Whether to automatically refresh cookies (default: False)
                         Note: Enabling this may cause browser sessions to be invalidated
        """
        if not HAS_WEBAPI_PACKAGE:
            raise ImportError(
                "Required package not installed. Install with: pip install gemini-webapi  # Package name required for installation"
            )
        
        self.cookies_file = cookies_file
        self.auto_refresh = auto_refresh
        self._client: Optional[WebAPIClient] = None
        self._chat_session = None  # For conversation continuity
        self._initialized = False
    
    async def _init_client(self) -> None:
        """Initialize the web AI client with cookies."""
        if self._initialized:
            return
        
        # Load cookies
        if self.cookies_file:
            # Load from specified file
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            secure_1psid = cookies.get("__Secure-1PSID")
            secure_1psidts = cookies.get("__Secure-1PSIDTS")
        else:
            # Auto-detect cookie file
            secure_1psid, secure_1psidts = _load_cookies()
        
        if not secure_1psid:
            raise ValueError(
                "No cookies found. Please extract cookies first:\n"
                "  python web_dashboard/extract_ai_cookies.py --browser manual"
            )
        
        # Initialize client with cookies
        # Note: secure_1psidts is optional but recommended for better stability
        if secure_1psidts:
            self._client = WebAPIClient(
                secure_1psid=secure_1psid,
                secure_1psidts=secure_1psidts
            )
        else:
            # Try with just __Secure-1PSID (may work but less stable)
            print("WARNING: Only __Secure-1PSID found. __Secure-1PSIDTS recommended for better stability.")
            self._client = WebAPIClient(
                secure_1psid=secure_1psid
            )
        
        # Initialize the client (this handles cookie refresh, etc.)
        # Note: auto_refresh=False by default to avoid invalidating browser sessions
        await self._client.init(
            timeout=30,
            auto_close=False,
            close_delay=300,
            auto_refresh=self.auto_refresh  # Configurable - disabled by default
        )
        
        self._initialized = True
    
    async def query(self, prompt: str, continue_conversation: bool = False) -> str:
        """
        Send a query to the AI service.
        
        Args:
            prompt: The query/prompt to send
            continue_conversation: If True, maintains conversation history across queries
            
        Returns:
            Response text
        """
        await self._init_client()
        
        if continue_conversation:
            # Use chat session for conversation continuity
            if self._chat_session is None:
                self._chat_session = self._client.start_chat()
            response = await self._chat_session.send_message(prompt)
        else:
            # Single query without conversation history
            response = await self._client.generate_content(prompt)
        
        return response.text
    
    def start_chat(self):
        """
        Start a new chat session for conversation continuity.
        Returns a chat session object that maintains conversation history.
        
        Usage:
            client = WebAIClient()
            chat = await client.start_chat()
            response1 = await chat.send_message("Hello")
            response2 = await chat.send_message("What did I just say?")  # Remembers previous message
        """
        async def _start():
            await self._init_client()
            if self._chat_session is None:
                self._chat_session = self._client.start_chat()
            return self._chat_session
        
        return asyncio.run(_start())
    
    def reset_chat(self):
        """Reset the conversation history by starting a new chat session."""
        self._chat_session = None
    
    async def close(self) -> None:
        """Close the client and cleanup."""
        self._chat_session = None
        if self._client:
            await self._client.close()
            self._initialized = False


# Synchronous wrapper for easier use
def query_webai(prompt: str, cookies_file: Optional[str] = None, auto_refresh: bool = False, 
                 continue_conversation: bool = False) -> str:
    """
    Synchronous wrapper for querying the AI service.
    
    Args:
        prompt: The query/prompt to send
        cookies_file: Optional path to cookie file
        auto_refresh: Whether to automatically refresh cookies (default: False)
                     Note: Enabling this may cause browser sessions to be invalidated
        continue_conversation: If True, maintains conversation history (default: False)
        
    Returns:
        Response text
    """
    async def _query():
        client = WebAIClient(cookies_file=cookies_file, auto_refresh=auto_refresh)
        try:
            return await client.query(prompt, continue_conversation=continue_conversation)
        finally:
            await client.close()
    
    return asyncio.run(_query())


# Conversation helper class for maintaining chat sessions
class ConversationSession:
    """
    Helper class for maintaining conversation continuity across multiple queries.
    
    Usage:
        session = ConversationSession()
        response1 = session.send("Hello")
        response2 = session.send("What did I just say?")  # Remembers context
        session.reset()  # Start fresh conversation
        session.close()  # Clean up
    """
    
    def __init__(self, cookies_file: Optional[str] = None, auto_refresh: bool = False):
        self._client = WebAIClient(cookies_file=cookies_file, auto_refresh=auto_refresh)
        self._chat_session = None
        self._initialized = False
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop for this session."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    async def _ensure_chat(self):
        """Ensure chat session is initialized."""
        if not self._initialized:
            await self._client._init_client()
            self._chat_session = self._client._client.start_chat()
            self._initialized = True
    
    async def send(self, prompt: str) -> str:
        """
        Send a message in the conversation.
        
        Args:
            prompt: The message to send
            
        Returns:
            Response text
        """
        await self._ensure_chat()
        response = await self._chat_session.send_message(prompt)
        return response.text
    
    def send_sync(self, prompt: str) -> str:
        """Synchronous version of send()."""
        loop = self._get_loop()
        if loop.is_running():
            # If loop is already running, we need to use a different approach
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.send(prompt))
        else:
            return loop.run_until_complete(self.send(prompt))
    
    async def reset(self):
        """Reset the conversation and start fresh."""
        self._chat_session = None
        self._initialized = False
    
    def reset_sync(self):
        """Synchronous version of reset()."""
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self.reset())
    
    async def close(self):
        """Close the session."""
        self._chat_session = None
        self._initialized = False
        await self._client.close()
        # Don't close the loop - it may be shared or still running
        self._loop = None
    
    def close_sync(self):
        """Synchronous version of close()."""
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self.close())


# Persistent conversation session for production use
class PersistentConversationSession:
    """
    Production-ready conversation session that persists across restarts.
    
    Saves conversation metadata to disk and automatically restores it.
    Each user gets one persistent conversation identified by user_id.
    
    Usage:
        # First time - creates new session
        session = PersistentConversationSession("user_123")
        response1 = session.send_sync("Hello")
        
        # Later - resumes existing session
        session = PersistentConversationSession("user_123")
        response2 = session.send_sync("What did I say before?")  # Remembers!
    """
    
    def __init__(
        self, 
        session_id: str = "default",
        cookies_file: Optional[str] = None,
        auto_refresh: bool = False,
        storage_dir: Optional[str] = None
    ):
        """
        Initialize persistent conversation session.
        
        Args:
            session_id: Unique identifier for this conversation (used as filename, typically user_id)
            cookies_file: Optional path to cookie file
            auto_refresh: Whether to automatically refresh cookies
            storage_dir: Directory to store session files (default: project_root/data/conversations)
        """
        self.session_id = session_id
        self._client = WebAIClient(cookies_file=cookies_file, auto_refresh=auto_refresh)
        self._chat_session = None
        self._initialized = False
        self._loop = None
        
        # Set up storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = project_root / "data" / "conversations"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.storage_dir / f"{session_id}.json"
        self._saved_metadata = None
    
    def _get_loop(self):
        """Get or create event loop for this session."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _load_metadata(self) -> Optional[dict]:
        """Load saved conversation metadata from disk."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('metadata')
            except Exception as e:
                # Silently fail - will start fresh
                pass
        return None
    
    def _save_metadata(self, metadata: dict):
        """Save conversation metadata to disk."""
        try:
            data = {
                'session_id': self.session_id,
                'metadata': metadata,
                'last_updated': time.time()
            }
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._saved_metadata = metadata
        except Exception as e:
            # Silently fail - conversation continues but won't persist
            pass
    
    async def _ensure_chat(self):
        """Ensure chat session is initialized, loading from saved state if available."""
        if not self._initialized:
            await self._client._init_client()
            
            # Try to load saved metadata
            saved_metadata = self._load_metadata()
            
            if saved_metadata:
                # Resume existing conversation
                self._chat_session = self._client._client.start_chat(metadata=saved_metadata)
            else:
                # Start new conversation
                self._chat_session = self._client._client.start_chat()
            
            self._initialized = True
    
    async def send(self, prompt: str) -> str:
        """
        Send a message in the conversation and auto-save state.
        
        Args:
            prompt: The message to send
            
        Returns:
            Response text
        """
        await self._ensure_chat()
        response = await self._chat_session.send_message(prompt)
        
        # Auto-save conversation metadata after each message
        try:
            if hasattr(self._chat_session, 'metadata'):
                self._save_metadata(self._chat_session.metadata)
        except Exception:
            pass  # Continue even if save fails
        
        return response.text
    
    def send_sync(self, prompt: str) -> str:
        """Synchronous version of send()."""
        loop = self._get_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.send(prompt))
        else:
            return loop.run_until_complete(self.send(prompt))
    
    async def reset(self):
        """Reset the conversation and delete saved state."""
        self._chat_session = None
        self._initialized = False
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception:
                pass
    
    def reset_sync(self):
        """Synchronous version of reset()."""
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self.reset())
    
    def get_history(self) -> List[dict]:
        """
        Get conversation history (if available from metadata).
        
        Returns:
            List of message dicts with 'role' and 'content'
        """
        saved_metadata = self._load_metadata()
        if saved_metadata and 'history' in saved_metadata:
            return saved_metadata['history']
        return []
    
    async def close(self):
        """Close the session and save final state."""
        # Save one last time before closing
        if self._chat_session and hasattr(self._chat_session, 'metadata'):
            try:
                self._save_metadata(self._chat_session.metadata)
            except:
                pass
        
        self._chat_session = None
        self._initialized = False
        await self._client.close()
        self._loop = None
    
    def close_sync(self):
        """Synchronous version of close()."""
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self.close())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Query WebAI using cookies")
    parser.add_argument(
        "--cookies",
        help="Path to cookie file (auto-detected if not provided)"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Query to send"
    )
    parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Enable automatic cookie refresh (may cause browser logout)"
    )
    
    args = parser.parse_args()
    
    if not HAS_WEBAPI_PACKAGE:
        print("ERROR: Required package not installed")
        print("Install with: pip install gemini-webapi  # Package name required for installation")
        sys.exit(1)
    
    try:
        response = query_webai(
            args.query, 
            cookies_file=args.cookies, 
            auto_refresh=args.auto_refresh
        )
        print("\n" + "=" * 60)
        print("RESPONSE:")
        print("=" * 60)
        print(response)
        print("=" * 60)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
