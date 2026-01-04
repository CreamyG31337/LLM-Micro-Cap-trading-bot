#!/usr/bin/env python3
"""
Test script to run the archive retry job manually.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run the archive retry job."""
    try:
        from scheduler.jobs_research import archive_retry_job
        
        logger.info("=" * 80)
        logger.info("Running archive retry job...")
        logger.info("=" * 80)
        
        archive_retry_job()
        
        logger.info("=" * 80)
        logger.info("Archive retry job completed!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error running archive retry job: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

