
import sys
import os
import logging
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from supabase_client import SupabaseClient

def main():
    logger.info("🔧 Fixing Ollama settings (via Service Role)...")
    
    client = SupabaseClient(use_service_role=True)
    
    key = "model_granite3.3:8b_num_ctx"
    value = 8192
    
    data = {
        "key": key,
        "value": value,
        "description": "Increased context to prevent truncation (8k)"
    }
    
    try:
        # Upsert with service role
        result = client.supabase.table("system_settings").upsert(data).execute()
        if result.data:
            logger.info(f"✅ Successfully set {key} to {value}")
        else:
            logger.error("❌ Update returned no data")
            
    except Exception as e:
        logger.error(f"❌ Error updating setting: {e}")

if __name__ == "__main__":
    main()
