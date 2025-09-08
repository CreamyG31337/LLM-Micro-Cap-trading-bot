# LLM Micro-Cap Trading Bot - Master Script System

## 🚀 Quick Start

The easiest way to run the trading bot is now through the master script system:

### Windows
```bash
# Double-click run.bat, or from command line:
run.bat
```

### Mac/Linux
```bash
# From terminal:
./run.sh
```

### Python Direct
```bash
python run.py
```

## 📋 What's New

### ✅ Master Menu System
- Interactive menu with all available scripts
- Automatic virtual environment handling
- Color-coded output for better visibility
- Configuration and status checking

### ✅ Simplified File Handling
- **Default Data Directory**: `my trading/` (private, git-ignored)
- **Standard Filenames**: 
  - `llm_portfolio_update.csv` (your portfolio)
  - `llm_trade_log.csv` (trade history)
  - `cash_balances.json` (dual currency support)
- **No More File Path Confusion**: Just run scripts, they find your data automatically

### ✅ Privacy Protection
- All personal trading data stays in `my trading/` folder
- This folder is automatically git-ignored
- Your real trading data never gets committed to version control

## 🎯 Available Options

When you run the master script, you'll see these options:

| Option | Script | Description |
|--------|--------|-------------|
| **1** | Main Trading Script | Portfolio management with interactive trading |
| **2** | Simple Automation | LLM-powered automated trading (requires API key) |
| **3** | Generate Performance Graph | Create charts from your trading data |
| **4-7** | Legacy Scripts | Scripts using older folder structures |
| **8** | Debug Instructions | Troubleshooting information |
| **9** | Show Prompt | Display LLM prompt templates |
| **c** | Configure | System configuration and status |
| **q** | Quit | Exit the application |

## 🔧 Configuration Options

Press `c` in the main menu to access:

1. **Virtual Environment Status** - Check if venv is properly set up
2. **Project Structure** - Verify all directories exist
3. **Data Directory Status** - Check for your trading files

## 📁 File Structure

```
LLM-Micro-Cap-trading-bot/
├── run.py                 # Master menu script ⭐
├── run.bat               # Windows launcher
├── run.sh                # Unix launcher
├── trading_script.py     # Main trading logic
├── simple_automation.py  # Automated trading
├── my trading/           # 🔒 Your private data (git-ignored)
│   ├── llm_portfolio_update.csv
│   ├── llm_trade_log.csv
│   └── cash_balances.json
├── venv/                 # Virtual environment
└── requirements.txt      # Dependencies
```

## 🛠️ Setup Instructions

### First Time Setup

1. **Clone the repository** (if you haven't already)
2. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the master script**:
   ```bash
   python run.py
   ```

### Daily Usage

Just run the launcher for your system:
- Windows: Double-click `run.bat`
- Mac/Linux: Run `./run.sh`
- Any system: `python run.py`

## 🔄 Migration from Old System

If you were using the old system with manual file paths:

### Your Data is Safe
- Old CSV files in other directories will still work
- The system can still read from custom locations if needed
- Use menu option `c` to check your data directory status

### Recommended Migration
1. Copy your existing portfolio CSV to `my trading/llm_portfolio_update.csv`
2. Copy your trade log to `my trading/llm_trade_log.csv`
3. Run the master script - it will automatically use the new defaults

## 🎨 Features

### Color-Coded Output
- 🟢 **Green**: Success messages and confirmations
- 🔵 **Blue**: Information and headers
- 🟡 **Yellow**: Warnings and user prompts
- 🔴 **Red**: Errors and critical messages
- 🟦 **Cyan**: Commands and technical details

### Smart Defaults
- Automatically detects and uses your virtual environment
- Creates `my trading/` directory if it doesn't exist
- Uses standard filenames so you don't have to remember paths
- Falls back gracefully if files don't exist

### Cross-Platform Support
- Works on Windows, Mac, and Linux
- Handles different virtual environment structures
- Platform-specific launcher scripts included

## 🆘 Troubleshooting

### "Virtual environment not found"
```bash
python -m venv venv
# Then activate and install requirements
```

### "No portfolio CSV found"
- The script will prompt you to create a new portfolio
- Or copy your existing CSV to `my trading/llm_portfolio_update.csv`

### "Permission denied" (Unix systems)
```bash
chmod +x run.sh
```

### Menu doesn't show colors
- Your terminal may not support ANSI colors
- The functionality still works, just without colors

## 🔐 Security Notes

- The `my trading/` folder is automatically git-ignored
- Your real trading data stays private and local
- API keys are prompted for, not stored in files
- All sensitive data remains on your machine

## 💡 Tips

1. **Use the master script** - It handles all the complexity for you
2. **Let it create defaults** - Don't specify file paths unless you need to
3. **Check configuration** - Use option `c` to verify your setup
4. **Keep backups** - Your trading data is valuable, back it up separately

---

## 🚀 Ready to Trade?

Just run your platform's launcher and select option 1 to start trading!

- Windows: `run.bat`
- Mac/Linux: `./run.sh`
- Any platform: `python run.py`

The system will guide you through the rest! 🎯
