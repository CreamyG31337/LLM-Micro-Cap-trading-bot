#!/usr/bin/env python3
"""
Test script to check job_executions table
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from supabase_client import SupabaseClient

def main():
    client = SupabaseClient()
    try:
        result = client.supabase.table('job_executions').select('*').limit(5).execute()
        print('Found', len(result.data), 'job execution records')
        if result.data:
            for record in result.data:
                job_name = record.get('job_name', 'unknown')
                status = record.get('status', 'unknown')
                completed_at = record.get('completed_at', 'unknown')
                print(' ', job_name + ':', status, 'at', completed_at)
        else:
            print('No job execution records found')
    except Exception as e:
        print('Error querying job_executions:', str(e))

if __name__ == '__main__':
    main()