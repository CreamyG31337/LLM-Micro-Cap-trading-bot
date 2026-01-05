
"""
Example usage of AI Service
===========================

This script demonstrates how to use the AI service helper in your code.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_service_helper import query_ai_service

def main():
    print("Querying AI Service...")
    try:
        # Simple query
        response = query_ai_service("Summarize the current market sentiment in 3 bullet points")
        print("\nResponse:")
        print(response)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
