"""Terminal utilities module for environment detection and optimization.

This module provides terminal detection, width calculation, and environment-specific
optimization functions. It's designed to work across different operating systems
and terminal environments, with future web-based display compatibility in mind.
"""

import os
import platform
from typing import Dict, Any, Optional


def detect_terminal_width() -> int:
    """Detect the current terminal width in characters.
    
    Returns:
        Terminal width in characters, defaults to 80 if detection fails
    """
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        # Fallback to a reasonable default
        return 80


def detect_environment() -> Dict[str, Any]:
    """Detect OS and terminal environment.
    
    Returns:
        Dictionary containing environment information including:
        - os: Operating system name
        - os_version: OS version string
        - is_windows: Boolean indicating if running on Windows
        - is_windows_11: Boolean indicating if running on Windows 11
        - is_conhost: Boolean indicating if using Command Prompt
        - is_windows_terminal: Boolean indicating if using Windows Terminal
        - terminal_name: String name of the detected terminal
    """
    env = {
        'os': platform.system(),
        'os_version': platform.version(),
        'is_windows': platform.system() == 'Windows',
        'is_windows_11': False,
        'is_conhost': False,
        'is_windows_terminal': False,
        'terminal_name': 'Unknown'
    }
    
    if env['is_windows']:
        # Check if it's Windows 11 (build 22000+)
        try:
            version_parts = platform.version().split('.')
            if len(version_parts) >= 3:
                build_number = int(version_parts[2])
                env['is_windows_11'] = build_number >= 22000
        except (ValueError, IndexError):
            pass
        
        # Detect terminal type
        try:
            # Check for Windows Terminal environment variables
            if os.environ.get('WT_SESSION'):
                env['is_windows_terminal'] = True
                env['terminal_name'] = 'Windows Terminal'
            elif os.environ.get('ConEmuANSI'):
                env['terminal_name'] = 'ConEmu'
            else:
                env['is_conhost'] = True
                env['terminal_name'] = 'Command Prompt (conhost)'
        except Exception:
            env['terminal_name'] = 'Unknown Windows Terminal'
    
    return env


def get_optimal_table_width(data_dir: Optional[str] = None) -> int:
    """Get the optimal table width based on environment and data source.
    
    Args:
        data_dir: Optional data directory path to check for test data usage
        
    Returns:
        Optimal table width in characters
    """
    terminal_width = detect_terminal_width()
    
    # Check if using test_data
    using_test_data = False
    if data_dir:
        using_test_data = "test_data" in str(data_dir).lower()
    
    # If using test_data or terminal is narrow, force a wider minimum
    if using_test_data or terminal_width < 140:
        return max(terminal_width, 140)  # Force minimum 140 chars for test data
    
    return terminal_width


def is_using_test_data(data_dir: Optional[str] = None) -> bool:
    """Check if the script is currently using the test_data folder.
    
    Args:
        data_dir: Optional data directory path to check
        
    Returns:
        True if using test data directory
    """
    if data_dir:
        return "test_data" in str(data_dir).lower()
    return False


def check_table_display_issues(data_dir: Optional[str] = None) -> None:
    """Check if tables might be cut off and provide helpful suggestions.
    
    This function analyzes the current terminal environment and provides
    specific guidance for improving table display based on the detected
    terminal type and operating system.
    
    Args:
        data_dir: Optional data directory path for test data detection
    """
    # Import here to avoid circular imports
    from .console_output import print_warning, print_info
    
    terminal_width = detect_terminal_width()
    optimal_width = get_optimal_table_width(data_dir)
    using_test_data = is_using_test_data(data_dir)
    env = detect_environment()
    
    if terminal_width < 120:
        print_warning("⚠️  Terminal width may be too narrow for optimal table display")
        print_warning(f"   Current width: {terminal_width} characters")
        print_warning("   Recommended: 130+ characters for best experience")
        print_warning("")
        
        # Provide environment-specific suggestions
        if env['is_windows']:
            if env['is_windows_terminal']:
                print_warning("💡 Windows Terminal detected - To fix this:")
                print_warning("   1. Open Windows Terminal Settings (Ctrl+,)")
                print_warning("   2. Click 'Startup' in the left sidebar")
                print_warning("   3. Under 'Launch size', set 'Columns' to 130 or higher")
                print_warning("   4. Click 'Save'")
                print_warning("   5. Or maximize this window (click maximize button)")
                print_warning("   6. Or press F11 for full screen mode")
                print_warning("")
                print_warning("   Note: This setting is buried deep in the settings!")
                print_warning("   Microsoft keeps reorganizing the UI, so look for 'Startup' → 'Launch size'")
            elif env['is_conhost']:
                print_warning("💡 Command Prompt detected - To fix this:")
                print_warning("   1. Right-click title bar → Properties → Layout")
                print_warning("   2. Set 'Window Size Width' to 130 or higher")
                print_warning("   3. Or maximize this window (click maximize button)")
                print_warning("   4. Or press F11 for full screen mode")
                print_warning("   5. Consider upgrading to Windows Terminal for better experience")
            else:
                print_warning("💡 To fix this, try:")
                print_warning("   1. Maximize this window (click maximize button)")
                print_warning("   2. Press F11 for full screen mode")
                print_warning("   3. Right-click title bar → Properties → Font → Choose smaller font")
        else:
            print_warning("💡 To fix this, try:")
            print_warning("   1. Maximize this window")
            print_warning("   2. Increase terminal width in your terminal settings")
            print_warning("   3. Use a smaller font size")
        
        print_warning("")
    
    if using_test_data:
        print_info("🧪 Test Data Mode: Forcing wider table display for better visibility")
        if optimal_width > terminal_width:
            print_info(f"   Table will be optimized for {optimal_width} characters (current: {terminal_width})")
        print_info("")


def get_terminal_capabilities() -> Dict[str, bool]:
    """Get terminal capabilities for display optimization.
    
    Returns:
        Dictionary containing terminal capability flags:
        - supports_color: Whether terminal supports color output
        - supports_unicode: Whether terminal supports Unicode characters
        - supports_rich: Whether Rich formatting is recommended
        - is_web_compatible: Whether output should be web-compatible (future use)
    """
    env = detect_environment()
    
    capabilities = {
        'supports_color': True,  # Most modern terminals support color
        'supports_unicode': True,  # Most modern terminals support Unicode
        'supports_rich': True,  # Rich works on most terminals
        'is_web_compatible': False  # Future use for web dashboard
    }
    
    # Adjust capabilities based on environment
    if env['is_windows'] and env['is_conhost']:
        # Command Prompt has limited Unicode support
        capabilities['supports_unicode'] = False
    
    # Check for CI/CD environments that might not support interactive features
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        capabilities['supports_rich'] = False
    
    return capabilities


def optimize_for_web_display() -> Dict[str, Any]:
    """Get optimization settings for web-based display compatibility.
    
    This function prepares settings that will be useful when the system
    is extended to support a web-based dashboard.
    
    Returns:
        Dictionary containing web optimization settings:
        - use_html_colors: Whether to use HTML color codes
        - max_table_width: Maximum table width for web display
        - use_json_output: Whether to prefer JSON output format
        - responsive_breakpoints: Breakpoints for responsive design
    """
    return {
        'use_html_colors': True,
        'max_table_width': 1200,  # Reasonable max width for web
        'use_json_output': True,
        'responsive_breakpoints': {
            'mobile': 480,
            'tablet': 768,
            'desktop': 1024,
            'wide': 1200
        }
    }


def get_display_config(data_dir: Optional[str] = None, 
                      web_mode: bool = False) -> Dict[str, Any]:
    """Get comprehensive display configuration based on environment.
    
    Args:
        data_dir: Optional data directory path for context
        web_mode: Whether to optimize for web display
        
    Returns:
        Dictionary containing complete display configuration
    """
    config = {
        'terminal_width': detect_terminal_width(),
        'optimal_width': get_optimal_table_width(data_dir),
        'environment': detect_environment(),
        'capabilities': get_terminal_capabilities(),
        'using_test_data': is_using_test_data(data_dir)
    }
    
    if web_mode:
        config['web_optimization'] = optimize_for_web_display()
    
    return config