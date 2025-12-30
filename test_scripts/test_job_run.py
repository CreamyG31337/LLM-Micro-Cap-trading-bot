#!/usr/bin/env python3
"""
Test script to run a job and check if it writes to job_executions
"""
import subprocess
import sys
import os

def main():
    # Run the job in a completely separate Python process
    print('Running exchange rates job in subprocess...')
    result = subprocess.run([
        sys.executable, '-c', '''
import sys
sys.path.insert(0, r"c:\\Users\\cream\\OneDrive\\Documents\\LLM-Micro-Cap-trading-bot\\web_dashboard")
from scheduler.jobs import refresh_exchange_rates_job
import logging
logging.basicConfig(level=logging.INFO)
try:
    refresh_exchange_rates_job()
    print("Job completed successfully")
except Exception as e:
    print("Job failed:", str(e))
    import traceback
    traceback.print_exc()
'''
    ], capture_output=True, text=True, cwd=r"c:\Users\cream\OneDrive\Documents\LLM-Micro-Cap-trading-bot")
    
    print('STDOUT:', result.stdout)
    print('STDERR:', result.stderr)
    print('Return code:', result.returncode)

    # Now check if it wrote to the database
    print('\nChecking job_executions table...')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))
    from supabase_client import SupabaseClient
    client = SupabaseClient(use_service_role=True)
    try:
        result = client.supabase.table('job_executions').select('*').order('started_at', desc=True).limit(5).execute()
        if result.data:
            print('✅ Found recent job execution records:')
            for record in result.data:
                print('  Job: {}, Status: {}, Started: {}'.format(
                    record.get('job_name'), 
                    record.get('status'), 
                    record.get('started_at')
                ))
        else:
            print('❌ No job execution records found')
    except Exception as e:
        print('❌ Error checking job_executions:', str(e))

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()