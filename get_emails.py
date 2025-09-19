#!/usr/bin/env python3
"""
Get Contributor Emails - Simple Utility Script
==============================================

This script quickly outputs all contributor email addresses separated by
semicolons, ready to copy into your mail program.

Usage:
    python get_emails.py
    
Or with custom data directory:
    python get_emails.py --data-dir "C:/path/to/your/data"

Features:
- Outputs emails in semicolon-separated format
- Filters out empty or invalid emails
- Works with your existing fund contributions data
- Cross-platform compatibility
"""

if __name__ == "__main__":
    from menu_actions import get_contributor_emails_main
    get_contributor_emails_main()