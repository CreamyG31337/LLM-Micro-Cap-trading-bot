
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

from ollama_client import OllamaClient
from settings import get_summarizing_model

def main():
    logger.info("🧪 Testing Ollama connectivity...")
    client = OllamaClient()
    
    if not client.check_health():
        logger.error("❌ Ollama not reachable!")
        return
        
    logger.info("✅ Ollama is reachable")
    
    model = get_summarizing_model()
    logger.info(f"Target model: {model}")
    
    logger.info("Sending test query...")
    try:
        response = client.generate_completion(
            prompt="Say hello!",
            model=model,
            json_mode=False
        )
        if response:
            logger.info(f"✅ Response received: {response}")
        else:
            logger.error("❌ No response received")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
