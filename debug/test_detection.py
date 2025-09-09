#!/usr/bin/env python3
"""Test the environment detection system"""

import platform
import os

def detect_environment():
    """Detect OS and terminal environment."""
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

if __name__ == "__main__":
    env = detect_environment()
    print("Environment Detection Results:")
    print(f"OS: {env['os']}")
    print(f"Version: {env['os_version']}")
    print(f"Is Windows: {env['is_windows']}")
    print(f"Is Windows 11: {env['is_windows_11']}")
    print(f"Is conhost: {env['is_conhost']}")
    print(f"Is Windows Terminal: {env['is_windows_terminal']}")
    print(f"Terminal Name: {env['terminal_name']}")
    
    # Test the version parsing
    version_parts = platform.version().split('.')
    print(f"\nVersion parts: {version_parts}")
    if len(version_parts) >= 3:
        build_number = int(version_parts[2])
        print(f"Build number: {build_number}")
        print(f"Build >= 22000: {build_number >= 22000}")
