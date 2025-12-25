
import sys
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path.cwd()))

# Load env
load_dotenv("web_dashboard/.env")

from web_dashboard.streamlit_utils import get_current_positions

def check_structure():
    print("Fetching positions...")
    try:
        # We need to handle potential connection issues or missing env vars
        df = get_current_positions(None)
    except Exception as e:
        print(f"Error: {e}")
        return

    if df.empty:
        print("No positions found.")
        return

    print(f"\nDataFrame Columns: {df.columns.tolist()}")
    if not df.empty:
        print(f"\nFirst Row Data:\n{df.iloc[0]}")
    
    if 'securities' in df.columns:
        sec_val = df.iloc[0]['securities']
        print(f"\nSecurities column type: {type(sec_val)}")
        print(f"Securities column value: {sec_val}")

if __name__ == "__main__":
    check_structure()
