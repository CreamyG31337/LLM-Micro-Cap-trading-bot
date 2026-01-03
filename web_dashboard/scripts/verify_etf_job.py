#!/usr/bin/env python3
"""
ETF Watchtower Verification Script
===================================
Test that ETF holdings tracking is working correctly.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("ETFVerify")

def verify_etf_job():
    """Test ETF Watchtower end-to-end."""
    logger.info("="*60)
    logger.info("ETF WATCHTOWER VERIFICATION")
    logger.info("="*60)
    
    try:
        # 1. Test Schema Exists
        logger.info("\n>>> Testing Database Schema...")
        from postgres_client import PostgresClient
        db = PostgresClient()
        
        result = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'etf_holdings_log'
        """)
        
        if result and result[0]['count'] > 0:
            logger.info("✅ etf_holdings_log table exists")
        else:
            logger.error("❌ etf_holdings_log table NOT FOUND")
            return False
        
        # 2. Test Job Import
        logger.info("\n>>> Testing Job Import...")
        from scheduler.jobs_etf_watchtower import etf_watchtower_job
        logger.info("✅ jobs_etf_watchtower.py imports successfully")
        
        # 3. Run Job (First-time snapshot)
        logger.info("\n>>> Running ETF Watchtower Job...")
        etf_watchtower_job()
        
        # 4. Verify Data Was Inserted
        logger.info("\n>>> Verifying Database Inserts...")
        result = db.execute_query("SELECT COUNT(*) as count FROM etf_holdings_log")
        
        if result and result[0]['count'] > 0:
            logger.info(f"✅ Database contains {result[0]['count']} holding records")
            
            # Show sample from today
            sample = db.execute_query("""
                SELECT etf_ticker, COUNT(*) as holdings_count 
                FROM etf_holdings_log 
                WHERE date = CURRENT_DATE
                GROUP BY etf_ticker
            """)
            logger.info(f"\nETF Snapshots (Today: {datetime.now().strftime('%Y-%m-%d')}):")
            for row in sample:
                logger.info(f"  - {row['etf_ticker']}: {row['holdings_count']} holdings")
                
            # Check securities metadata
            sec_count = db.execute_query("SELECT COUNT(*) as count FROM securities")
            if sec_count and sec_count[0]['count'] > 0:
                 logger.info(f"✅ Securities table populated: {sec_count[0]['count']} records")
            else:
                 logger.error("❌ Securities table is empty!")
                 
        else:
            logger.warning("⚠️  No holdings data inserted (ARK CSVs may be unavailable)")
        
        logger.info("\n" + "="*60)
        logger.info("✅ ETF WATCHTOWER VERIFICATION COMPLETE")
        logger.info("="*60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification Failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = verify_etf_job()
    sys.exit(0 if success else 1)
