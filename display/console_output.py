"""Console output module for colored messages and formatting.

This module provides colored console output functions that work with both Rich and colorama,
with graceful fallback to plain text. The functions are designed to work with data from
any repository type and provide consistent messaging across the trading system.
"""

import os
import sys
from typing import Optional


def _can_handle_unicode() -> bool:
    """Check if the current environment can handle Unicode characters."""
    try:
        # Test encoding a common emoji and box drawing character
        test_emoji = "📊"
        test_box = "┌"
        test_emoji.encode(sys.stdout.encoding or 'utf-8')
        test_box.encode(sys.stdout.encoding or 'utf-8')
        
        # Additional check for Windows Terminal vs Command Prompt
        import os
        if os.name == 'nt':  # Windows
            # Check if we're in Windows Terminal (which supports Unicode better)
            wt_session = os.environ.get('WT_SESSION')
            if wt_session:
                return True
            # Check for modern Windows 10+ with UTF-8 support
            try:
                import locale
                encoding = locale.getpreferredencoding()
                if 'utf' in encoding.lower():
                    return True
            except:
                pass
        
        return True
    except (UnicodeEncodeError, LookupError):
        return False


# Color and formatting imports with fallback handling
try:
    from colorama import init, Fore, Back, Style
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    init(autoreset=True)  # Initialize colorama
    _HAS_RICH = True
    # Try to create Rich console, but be more permissive
    try:
        console = Console()
        # Test if Rich can actually render without crashing
        test_output = console.render_str("test")
    except Exception:
        # Only disable Rich if it completely fails
        _HAS_RICH = False
        console = None
except ImportError:
    _HAS_RICH = False
    console = None
    # Create dummy classes for fallback
    class DummyColor:
        def __getattr__(self, name):
            return ""
    
    Fore = Back = Style = DummyColor()

# Force fallback mode for testing (set via environment variable or function call)
_FORCE_FALLBACK = os.environ.get("FORCE_FALLBACK", "").lower() in ("true", "1", "yes", "on")
_FORCE_COLORAMA_ONLY = os.environ.get("FORCE_COLORAMA_ONLY", "").lower() in ("true", "1", "yes", "on")


def set_force_fallback(force_fallback: bool = True, colorama_only: bool = False) -> None:
    """Force fallback mode for testing purposes.
    
    Args:
        force_fallback: If True, disable Rich and use colorama/plain text
        colorama_only: If True, disable Rich but keep colorama (only works if force_fallback=True)
    """
    global _HAS_RICH, _FORCE_FALLBACK, _FORCE_COLORAMA_ONLY
    
    _FORCE_FALLBACK = force_fallback
    _FORCE_COLORAMA_ONLY = colorama_only
    
    if force_fallback:
        _HAS_RICH = False
        if not colorama_only:
            # Also disable colorama for plain text testing
            global Fore, Back, Style
            class DummyColor:
                def __getattr__(self, name):
                    return ""
            
            Fore = Back = Style = DummyColor()


def print_success(message: str, emoji: str = "✅") -> None:
    """Print a success message with green color and emoji.
    
    Args:
        message: The success message to display
        emoji: The emoji to display with the message (default: ✅)
    """
    safe_emoji = _safe_emoji(emoji)
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        try:
            console.print(f"{safe_emoji} {message}", style="bold green")
        except UnicodeEncodeError:
            print(f"SUCCESS: {message}")
    else:
        print(f"{Fore.GREEN}{safe_emoji} {message}{Style.RESET_ALL}")


def print_error(message: str, emoji: str = "❌") -> None:
    """Print an error message with red color and emoji.
    
    Args:
        message: The error message to display
        emoji: The emoji to display with the message (default: ❌)
    """
    safe_emoji = _safe_emoji(emoji)
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        try:
            console.print(f"{safe_emoji} {message}", style="bold red")
        except UnicodeEncodeError:
            print(f"ERROR: {message}")
    else:
        print(f"{Fore.RED}{safe_emoji} {message}{Style.RESET_ALL}")


def print_warning(message: str, emoji: str = "⚠️") -> None:
    """Print a warning message with yellow color and emoji.
    
    Args:
        message: The warning message to display
        emoji: The emoji to display with the message (default: ⚠️)
    """
    safe_emoji = _safe_emoji(emoji)
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        try:
            console.print(f"{safe_emoji} {message}", style="bold yellow")
        except UnicodeEncodeError:
            print(f"WARNING: {message}")
    else:
        print(f"{Fore.YELLOW}{safe_emoji} {message}{Style.RESET_ALL}")


def print_info(message: str, emoji: str = "ℹ️") -> None:
    """Print an info message with blue color and emoji.
    
    Args:
        message: The info message to display
        emoji: The emoji to display with the message (default: ℹ️)
    """
    safe_emoji = _safe_emoji(emoji)
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        try:
            console.print(f"{safe_emoji} {message}", style="bold blue")
        except UnicodeEncodeError:
            print(f"INFO: {message}")
    else:
        print(f"{Fore.BLUE}{safe_emoji} {message}{Style.RESET_ALL}")


def _safe_emoji(emoji: str) -> str:
    """Return emoji if supported, otherwise return a safe alternative."""
    try:
        # Test if we can encode the emoji
        emoji.encode(sys.stdout.encoding or 'utf-8')
        return emoji
    except (UnicodeEncodeError, LookupError):
        # Return safe alternatives for common emojis
        emoji_map = {
            "🔥": "*",
            "🚀": ">>",
            "💼": "[P]",
            "⚡": "!",
            "📊": "[S]",
            "💰": "$",
            "🛒": "[B]",
            "📤": "[S]",
            "💵": "$",
            "💸": "-$",
            "🔄": "~",
            "🔗": "&",
            "💾": "[B]",
            "❌": "X",
            "📋": "[L]",
            "🔷": "◆",
            "✅": "OK",
            "⚠️": "!",
            "ℹ️": "i",
            "🎯": "[T]",
            "🏢": "[C]",
            "📅": "[D]",
            "📈": "[^]",
            "🍕": "[W]",
            "🛑": "[!]",
            "💹": "[P]",
            "👥": "[O]",
            "🏦": "[E]"
        }
        return emoji_map.get(emoji, "*")


def print_header(title: str, emoji: str = "🔷", width: int = 60) -> None:
    """Print a formatted header with emoji and cyan color.
    
    Args:
        title: The header title to display
        emoji: The emoji to display with the title (default: 🔷)
        width: The width of the header line (default: 60)
    """
    safe_emoji = _safe_emoji(emoji)
    header_text = f"{safe_emoji} {title} {safe_emoji}"
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        try:
            console.print(f"{'='*width}", style="cyan")
            console.print(f"{header_text:^{width}}", style="bold cyan")
            console.print(f"{'='*width}", style="cyan")
        except UnicodeEncodeError:
            # Fallback to plain text if Rich has encoding issues
            print(f"{'='*width}")
            print(f"{header_text:^{width}}")
            print(f"{'='*width}")
    else:
        print(f"{Fore.CYAN}{'='*width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{header_text:^{width}}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*width}{Style.RESET_ALL}")


def print_separator(width: int = 60, char: str = "─") -> None:
    """Print a separator line with cyan color.
    
    Args:
        width: The width of the separator line (default: 60)
        char: The character to use for the separator (default: ─)
    """
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{char*width}", style="cyan")
    else:
        print(f"{Fore.CYAN}{char*width}{Style.RESET_ALL}")


def display_market_time_header(market_time_info: dict) -> None:
    """Display market time information in a formatted header.
    
    Args:
        market_time_info: Dictionary containing market time information
                         Expected keys: 'current_time', 'market_status', 'next_open', etc.
    """
    if not market_time_info:
        return
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        # Rich formatting with table
        from rich.table import Table
        from rich.text import Text
        
        time_table = Table(show_header=False, show_edge=False, pad_edge=False)
        time_table.add_column("Time", style="bold cyan", width=15)
        time_table.add_column("Value", style="bold white", width=20)
        
        for key, value in market_time_info.items():
            time_table.add_row(f"{key}:", str(value))
        
        console.print(time_table)
    else:
        # Colorama fallback
        for key, value in market_time_info.items():
            print(f"{Fore.CYAN}{key}:{Style.RESET_ALL} {Fore.WHITE}{value}{Style.RESET_ALL}")


def format_money_display(amount: float, currency: str = "CAD", 
                        color: Optional[str] = None, emoji: str = "") -> str:
    """Format money amount for display with color and emoji.
    
    Args:
        amount: The monetary amount to format
        currency: The currency code (default: CAD)
        color: The color to use (green, red, yellow, etc.)
        emoji: The emoji to display with the amount
        
    Returns:
        Formatted money string with color and emoji
    """
    formatted = f"{amount:,.2f} {currency}"
    
    if color and not _FORCE_FALLBACK:
        if _HAS_RICH and console:
            # Rich formatting
            return f"{emoji} {formatted}" if emoji else formatted
        else:
            # Colorama formatting
            color_map = {
                'green': Fore.GREEN,
                'red': Fore.RED,
                'yellow': Fore.YELLOW,
                'blue': Fore.BLUE,
                'cyan': Fore.CYAN,
                'magenta': Fore.MAGENTA,
                'white': Fore.WHITE
            }
            color_code = color_map.get(color.lower(), Fore.WHITE)
            return f"{color_code}{emoji} {formatted}{Style.RESET_ALL}"
    
    return f"{emoji} {formatted}" if emoji else formatted


def get_console():
    """Get the Rich console instance if available.
    
    Returns:
        Rich Console instance or None if not available
    """
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        return console
    return None


def has_rich_support() -> bool:
    """Check if Rich formatting is available and enabled.
    
    Returns:
        True if Rich is available and not in fallback mode
    """
    return _HAS_RICH and console and not _FORCE_FALLBACK


def has_color_support() -> bool:
    """Check if any color formatting is available.
    
    Returns:
        True if either Rich or colorama is available
    """
    return (_HAS_RICH and console and not _FORCE_FALLBACK) or not _FORCE_COLORAMA_ONLY