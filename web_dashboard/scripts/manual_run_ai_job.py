
import sys
import os
import logging
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from scheduler.jobs_social import social_sentiment_ai_job

def main():
    logger.info("🚀 Starting manual social sentiment AI Analysis run...")
    
    try:
        social_sentiment_ai_job()
        logger.info("✅ social_sentiment_ai_job completed.")
    except Exception as e:
        logger.error(f"❌ social_sentiment_ai_job failed: {e}")

    logger.info("🏁 Manual run finished.")

if __name__ == "__main__":
    main()
