
import sys
import os
import logging
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from settings import get_system_setting
from web_dashboard.ollama_client import OllamaClient

def main():
    try:
        client = OllamaClient()
        models = client.list_available_models()
        print(f"Available models: {models}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
