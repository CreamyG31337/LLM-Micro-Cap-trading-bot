#!/bin/bash
# Unix shell script to run the LLM Micro-Cap Trading Bot
# This script automatically activates the virtual environment and runs the master menu

echo
echo "========================================"
echo "LLM Micro-Cap Trading Bot - Launcher"
echo "========================================"
echo

# Check if virtual environment exists
if [ ! -f "venv/bin/python" ]; then
    echo "ERROR: Virtual environment not found!"
    echo
    echo "Please create the virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo
    exit 1
fi

# Run the master script using the virtual environment
while true; do
    echo "Starting the trading bot menu system..."
    echo
    venv/bin/python run.py
    exit_code=$?
    
    echo
    if [ $exit_code -eq 42 ]; then
        echo "Trading bot requested restart..."
        echo "Restarting in 2 seconds..."
        sleep 2
        continue
    else
        echo "Trading bot session ended."
        break
    fi
done
