"""Console output module for colored messages and formatting.

This module provides colored console output functions that work with both Rich and colorama,
with graceful fallback to plain text. The functions are designed to work with data from
any repository type and provide consistent messaging across the trading system.
"""

import os
from typing import Optional

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
    console = Console()
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
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold green")
    else:
        print(f"{Fore.GREEN}{emoji} {message}{Style.RESET_ALL}")


def print_error(message: str, emoji: str = "❌") -> None:
    """Print an error message with red color and emoji.
    
    Args:
        message: The error message to display
        emoji: The emoji to display with the message (default: ❌)
    """
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold red")
    else:
        print(f"{Fore.RED}{emoji} {message}{Style.RESET_ALL}")


def print_warning(message: str, emoji: str = "⚠️") -> None:
    """Print a warning message with yellow color and emoji.
    
    Args:
        message: The warning message to display
        emoji: The emoji to display with the message (default: ⚠️)
    """
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold yellow")
    else:
        print(f"{Fore.YELLOW}{emoji} {message}{Style.RESET_ALL}")


def print_info(message: str, emoji: str = "ℹ️") -> None:
    """Print an info message with blue color and emoji.
    
    Args:
        message: The info message to display
        emoji: The emoji to display with the message (default: ℹ️)
    """
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{emoji} {message}", style="bold blue")
    else:
        print(f"{Fore.BLUE}{emoji} {message}{Style.RESET_ALL}")


def print_header(title: str, emoji: str = "🔷", width: int = 60) -> None:
    """Print a formatted header with emoji and cyan color.
    
    Args:
        title: The header title to display
        emoji: The emoji to display with the title (default: 🔷)
        width: The width of the header line (default: 60)
    """
    header_text = f"{emoji} {title} {emoji}"
    
    if _HAS_RICH and console and not _FORCE_FALLBACK:
        console.print(f"{'='*width}", style="cyan")
        console.print(f"{header_text:^{width}}", style="bold cyan")
        console.print(f"{'='*width}", style="cyan")
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