# Development Guide

This guide explains how to develop and debug the trading bot with improved reliability and stricter checking.

## Development Mode

Run the bot in development mode for stricter checking and better error reporting:

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run in development mode
python dev_run.py --data-dir "my trading"
```

Development mode enables:
- Detailed error logging to `trading_bot_dev.log`
- Variable scoping checks
- Stricter type checking
- Better exception handling

## Code Quality Tools

### Type Checking with MyPy
```bash
# Install development tools
pip install -r requirements.txt

# Run type checking
mypy trading_script.py
```

### Code Linting with Ruff
```bash
# Check code style and quality
ruff check trading_script.py

# Auto-fix issues
ruff check --fix trading_script.py
```

### Running Tests
```bash
# Run tests (when available)
pytest tests/
```

## Error Handling Improvements

The code now includes:

1. **Specific Exception Handling**: Different error types are handled separately
2. **Detailed Logging**: All errors are logged with context
3. **Variable Scoping Checks**: Development mode warns about potential scoping issues
4. **Type Hints**: Better type safety and IDE support

## Common Issues to Watch For

1. **Variable Scoping**: Avoid local imports that shadow global variables
2. **Silent Failures**: All exceptions are now logged
3. **Type Safety**: Use type hints for better error detection

## Debugging Tips

1. Check `trading_bot_dev.log` for detailed error information
2. Use development mode to catch scoping issues early
3. Run type checking before committing changes
4. Use specific exception types instead of generic `Exception`
