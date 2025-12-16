#!/usr/bin/env python3
"""
Generate a build stamp file with git commit info and timestamp.
This should be run during deployment/build process.
"""

import subprocess
import json
from datetime import datetime, timezone

def get_git_info():
    """Get git commit hash and branch."""
    try:
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        return commit_hash, branch
    except Exception:
        return 'unknown', 'unknown'

def generate_build_stamp():
    """Generate build stamp file."""
    commit_hash, branch = get_git_info()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    build_info = {
        'commit': commit_hash,
        'branch': branch,
        'timestamp': timestamp,
        'build_date': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Write to file
    with open('build_stamp.json', 'w') as f:
        json.dump(build_info, f, indent=2)
    
    print(f"Build stamp generated:")
    print(f"   Commit: {commit_hash}")
    print(f"   Branch: {branch}")
    print(f"   Date: {build_info['build_date']}")

if __name__ == '__main__':
    generate_build_stamp()
