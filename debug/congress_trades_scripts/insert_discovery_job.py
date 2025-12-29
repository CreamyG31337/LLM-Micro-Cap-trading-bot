#!/usr/bin/env python3
"""
Helper script to insert the opportunity_discovery_job into jobs.py
"""

import sys
from pathlib import Path

# Paths
jobs_file = Path("c:/Users/cream/OneDrive/Documents/LLM-Micro-Cap-trading-bot/web_dashboard/scheduler/jobs.py")
opportunity_file = Path("c:/Users/cream/OneDrive/Documents/LLM-Micro-Cap-trading-bot/web_dashboard/scheduler/jobs_opportunity.py")

# Read the opportunity job function
with open(opportunity_file, 'r', encoding='utf-8') as f:
    opportunity_code = f.read()

# Read the jobs.py file
with open(jobs_file, 'r', encoding='utf-8') as f:
    jobs_content = f.read()

# Find the insertion point (after ticker_research_job)
insertion_marker = '        logger.error(f"❌ Ticker research job failed: {e}", exc_info=True)\n'

if insertion_marker in jobs_content:
    # Insert the opportunity job after ticker_research_job
    parts = jobs_content.split(insertion_marker)
    new_content = parts[0] + insertion_marker + opportunity_code + parts[1]
    
    # Also add the scheduler registration
    scheduler_marker = '        logger.info("Registered job: ticker_research_job (every 6 hours)")\n'
    
    if scheduler_marker in new_content:
        registration_code = '''
        # Opportunity Discovery: Every 12 hours
        scheduler.add_job(
            opportunity_discovery_job,
            trigger=CronTrigger(
                hour='*/12',
                minute=30,
                timezone='America/New_York'
            ),
            id='opportunity_discovery_job',
            name='Opportunity Discovery',
            replace_existing=True
        )
        logger.info("Registered job: opportunity_discovery_job (every 12 hours)")
'''
        parts = new_content.split(scheduler_marker)
        new_content = parts[0] + scheduler_marker + registration_code + parts[1]
    
    # Write back
    with open(jobs_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully inserted opportunity_discovery_job into jobs.py")
    print("✅ Registered job with scheduler (every 12 hours)")
else:
    print("❌ Could not find insertion marker in jobs.py")
    sys.exit(1)
