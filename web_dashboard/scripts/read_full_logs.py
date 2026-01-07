#!/usr/bin/env python3
"""
Read Full Server Logs
=====================

Read and display full application logs from the server.
Can read from local log files or output to a file for analysis.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add web_dashboard to path
web_dashboard_path = Path(__file__).resolve().parent.parent
if str(web_dashboard_path) not in sys.path:
    sys.path.insert(0, str(web_dashboard_path))


def read_full_logs(
    log_file_path: Optional[str] = None,
    output_file: Optional[str] = None,
    search: Optional[str] = None,
    level: Optional[str] = None,
    max_lines: Optional[int] = None,
    tail: Optional[int] = None
) -> List[Dict]:
    """Read full logs from the server.
    
    Args:
        log_file_path: Path to log file (defaults to web_dashboard/logs/app.log)
        output_file: Optional file to write logs to
        search: Filter by search term
        level: Filter by log level (INFO, ERROR, WARNING, DEBUG)
        max_lines: Maximum number of lines to read (None = all)
        tail: Read only last N lines (like tail -n)
        
    Returns:
        List of log entries
    """
    # Default log file path
    if log_file_path is None:
        log_file_path = web_dashboard_path / 'logs' / 'app.log'
    else:
        log_file_path = Path(log_file_path)
    
    if not log_file_path.exists():
        print(f"ERROR: Log file not found: {log_file_path}")
        return []
    
    print(f"Reading logs from: {log_file_path}")
    file_size = log_file_path.stat().st_size
    print(f"   File size: {file_size / (1024*1024):.2f} MB")
    
    logs = []
    
    try:
        # Read file
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if tail:
                # Read last N lines efficiently
                lines = []
                # Read in chunks from end
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                chunk_size = min(8192, file_size)
                data = ''
                position = file_size
                
                while position > 0 and len(lines) < tail:
                    position = max(0, position - chunk_size)
                    f.seek(position)
                    chunk = f.read(chunk_size)
                    data = chunk + data
                    
                    # Count lines
                    lines = data.split('\n')
                    if len(lines) > tail:
                        lines = lines[-tail:]
                        break
                
                all_lines = lines
            else:
                # Read all lines
                all_lines = f.readlines()
            
            # Apply max_lines limit
            if max_lines and len(all_lines) > max_lines:
                print(f"WARNING: Limiting to {max_lines} lines (file has {len(all_lines)} lines)")
                all_lines = all_lines[-max_lines:]
            
            print(f"   Reading {len(all_lines)} lines...")
            
            # Parse lines
            for line_num, line in enumerate(all_lines, 1):
                line = line.rstrip('\n\r')
                if not line.strip():
                    continue
                
                # Try to parse log format: YYYY-MM-DD HH:MM:SS | LEVEL | module | message
                try:
                    parts = line.split(' | ', 3)
                    if len(parts) == 4:
                        timestamp_str, level_str, module, message = parts
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        
                        log_entry = {
                            'line_num': line_num,
                            'timestamp': timestamp,
                            'level': level_str.strip(),
                            'module': module.strip(),
                            'message': message.strip(),
                            'formatted': line
                        }
                        
                        # Apply filters
                        if level and log_entry['level'] != level:
                            continue
                        
                        if search and search.lower() not in log_entry['message'].lower():
                            continue
                        
                        logs.append(log_entry)
                    else:
                        # Unparsed line - include it anyway
                        logs.append({
                            'line_num': line_num,
                            'timestamp': None,
                            'level': 'UNKNOWN',
                            'module': '',
                            'message': line,
                            'formatted': line
                        })
                except Exception:
                    # Malformed line - include as-is
                    logs.append({
                        'line_num': line_num,
                        'timestamp': None,
                        'level': 'UNKNOWN',
                        'module': '',
                        'message': line,
                        'formatted': line
                    })
        
        print(f"SUCCESS: Parsed {len(logs)} log entries")
        
        # Write to output file if specified
        if output_file:
            output_path = Path(output_file)
            print(f"Writing to: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                for log in logs:
                    f.write(log['formatted'] + '\n')
            print(f"SUCCESS: Wrote {len(logs)} lines to {output_path}")
        
        return logs
        
    except Exception as e:
        print(f"ERROR: Error reading log file: {e}")
        import traceback
        traceback.print_exc()
        return []


def display_logs(logs: List[Dict], limit: Optional[int] = None):
    """Display logs to console.
    
    Args:
        logs: List of log entries
        limit: Maximum number of logs to display (None = all)
    """
    if not logs:
        print("No logs to display.")
        return
    
    display_logs = logs[-limit:] if limit else logs
    
    print(f"\n{'='*80}")
    print(f"LOG ENTRIES ({len(display_logs)} of {len(logs)} total)")
    print(f"{'='*80}\n")
    
    for log in display_logs:
        if log['timestamp']:
            timestamp_str = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = 'N/A'
        
        level = log['level']
        module = log['module']
        message = log['message']
        
        # Level prefix (no emojis for Windows compatibility)
        if level == 'ERROR':
            prefix = '[ERROR]'
        elif level == 'WARNING':
            prefix = '[WARN]'
        elif level == 'INFO':
            prefix = '[INFO]'
        elif level == 'DEBUG':
            prefix = '[DEBUG]'
        else:
            prefix = '[LOG]'
        
        print(f"{prefix} [{timestamp_str}] [{level:7}] [{module:20}] {message}")
    
    if limit and len(logs) > limit:
        print(f"\n... ({len(logs) - limit} more entries, use --limit to see more)")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Read full server logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read all logs
  python read_full_logs.py
  
  # Read last 1000 lines
  python read_full_logs.py --tail 1000
  
  # Search for errors
  python read_full_logs.py --search "error" --level ERROR
  
  # Save to file
  python read_full_logs.py --output logs_export.txt
  
  # Read specific log file
  python read_full_logs.py --log-file logs/app.log.1
        """
    )
    parser.add_argument('--log-file', '-f', help='Path to log file (default: logs/app.log)')
    parser.add_argument('--output', '-o', help='Output file to write logs to')
    parser.add_argument('--search', '-s', help='Search term to filter logs')
    parser.add_argument('--level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Filter by log level')
    parser.add_argument('--max-lines', '-m', type=int,
                       help='Maximum number of lines to read')
    parser.add_argument('--tail', '-t', type=int,
                       help='Read only last N lines (like tail -n)')
    parser.add_argument('--display-limit', '-d', type=int, default=100,
                       help='Maximum number of logs to display (default: 100)')
    parser.add_argument('--no-display', action='store_true',
                       help='Don\'t display logs, only write to file')
    
    args = parser.parse_args()
    
    logs = read_full_logs(
        log_file_path=args.log_file,
        output_file=args.output,
        search=args.search,
        level=args.level,
        max_lines=args.max_lines,
        tail=args.tail
    )
    
    if not args.no_display:
        display_logs(logs, limit=args.display_limit)
    elif args.output:
        print(f"\nSUCCESS: Logs written to {args.output}")
    else:
        print(f"\nSUCCESS: Read {len(logs)} log entries (use --output to save)")


if __name__ == "__main__":
    main()

