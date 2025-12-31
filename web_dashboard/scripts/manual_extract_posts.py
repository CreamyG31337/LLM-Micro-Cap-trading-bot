
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

sys.path.insert(0, str(project_root / 'web_dashboard'))

from social_service import SocialSentimentService

def main():
    logger.info("🔧 Starting manual post extraction...")
    try:
        service = SocialSentimentService()
        result = service.extract_posts_from_raw_data()
        logger.info(f"✅ Extraction result: {result}")
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")

if __name__ == "__main__":
    main()
