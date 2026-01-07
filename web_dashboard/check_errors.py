#!/usr/bin/env python3
"""Quick error checker - can be run by AI to check for recent errors."""
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).resolve().parent.parent
web_dashboard = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(web_dashboard))

from utils.log_reader import check_recent_errors, get_recent_job_errors, search_logs

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check for recent errors')
    parser.add_argument('--job', help='Check errors for specific job')
    parser.add_argument('--search', help='Search for specific term')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    
    args = parser.parse_args()
    
    if args.job:
        errors = get_recent_job_errors(args.job, hours=args.hours)
        from utils.log_reader import format_errors_for_display
        print(format_errors_for_display(errors))
    elif args.search:
        errors = search_logs(args.search, hours=args.hours)
        from utils.log_reader import format_errors_for_display
        print(format_errors_for_display(errors))
    else:
        print(check_recent_errors(hours=args.hours))

