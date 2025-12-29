
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postgres_client import PostgresClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wipe_and_reset():
    pg = PostgresClient()
    
    logger.info("Deleting from congress_trades_analysis...")
    pg.execute_update("DELETE FROM congress_trades_analysis WHERE id != 0")
    
    logger.info("Resetting congress_trade_sessions...")
    pg.execute_update("""
        UPDATE congress_trade_sessions 
        SET conflict_score = NULL, confidence_score = NULL, ai_summary = NULL 
        WHERE id != 0
    """)
    
    logger.info("Done.")

if __name__ == "__main__":
    wipe_and_reset()
