# Bug Prevention Guide

This guide documents common bugs we've encountered and how to prevent them in the future.

## 🐛 Common Bugs and Prevention Patterns

### 1. Emoji Syntax Errors

**Problem**: `SyntaxError: invalid character '✅' (U+2705)` when using emojis in f-strings.

**Root Cause**: Calling `_safe_emoji()` as a string literal instead of a function.

**❌ WRONG**:
```python
print(f"{_safe_emoji('_safe_emoji('✅')')} Message")
```

**✅ CORRECT**:
```python
print(f"{_safe_emoji('✅')} Message")
```

**Prevention**: Always call `_safe_emoji()` as a function, not as a string literal.

### 2. Unicode Encoding Errors

**Problem**: `UnicodeEncodeError: 'charmap' codec can't encode character` in console output.

**Root Cause**: Terminal encoding issues with Unicode characters (especially on Windows).

**✅ SOLUTION**:
```python
# In display/console_output.py
def _safe_emoji(emoji):
    """Safely handle emojis with fallback for different terminal encodings."""
    try:
        # Test if emoji can be encoded
        emoji.encode('cp1252')
        return emoji
    except UnicodeEncodeError:
        # Return safe ASCII fallback
        return EMOJI_FALLBACKS.get(emoji, "?")
```

**Prevention**: Always use `_safe_emoji()` for emojis in console output.

### 3. Cache-Related Issues

**Problem**: Stale data, incorrect prices, or display problems due to corrupted or outdated cache files.

**Root Cause**: Cache files can become corrupted, outdated, or excessively large over time.

**✅ PREVENTION & SOLUTION**:

#### Cache Management System
The system includes comprehensive cache management accessible from both main menus:

**From Main Menu**:
```bash
python run.py  # Select option 'k' - Manage Cache
```

**From Trading Script**:
```bash
python trading_script.py --data-dir "your_fund"  # Select 'cache' from menu
```

#### Cache Types and Issues

| Cache Type | Contains | Common Issues | When to Clear |
|------------|----------|---------------|---------------|
| **Price Cache** | Stock prices, market data | Wrong prices, stale quotes | Price data incorrect |
| **Fundamentals Cache** | Company financial data | Wrong company info | Company data stale |
| **Exchange Rate Cache** | Currency conversions | Wrong CAD/USD values | Conversion errors |
| **Memory Caches** | Runtime data | Data inconsistencies | Multiple problems |

#### Cache Management Commands

**View Cache Status** (Always do this first):
```bash
python run.py  # Option 'k' -> 1 (View Cache Status)
```

**Clear Specific Cache**:
```bash
python run.py  # Option 'k' -> 3 (Clear Specific Cache)
# Then select cache type to clear
```

**Clear All Caches** (Emergency):
```bash
python run.py  # Option 'k' -> 2 (Clear All Caches)
# Requires confirmation
```

#### Troubleshooting Workflow

**Standard Cache Troubleshooting**:
1. **View cache status** first to understand current state
2. **Clear specific cache** causing issues (if identifiable)
3. **Clear all caches** if problems persist
4. **Restart application** after cache operations
5. **Verify cache rebuild** by checking status again

**Cache Management Best Practices**:
- **Weekly**: Check cache status and sizes
- **Monthly**: Clear caches for data freshness
- **Before troubleshooting**: Always check cache status first
- **After system updates**: Clear caches to rebuild with new logic
- **When experiencing issues**: Cache management as first troubleshooting step

**Prevention**: Monitor cache sizes regularly and clear caches proactively rather than waiting for issues.

### 4. Pandas Unicode Character Issues

**Problem**: Pandas generates problematic Unicode characters like `à` that cause encoding errors.

**✅ SOLUTION**:
```python
# In display/table_formatter.py
import pandas as pd

# Set options to prevent problematic Unicode characters
pd.set_option('display.unicode.ambiguous_as_wide', False)
pd.set_option('display.unicode.east_asian_width', False)
```

**Prevention**: Always set these pandas options when creating tables.

### 4. P&L Calculation N/A Values

**Problem**: P&L calculations show "N/A" when `unrealized_pnl` or `cost_basis` are `None`.

**✅ SOLUTION**:
```python
# Always handle None values
unrealized_pnl = row.get('unrealized_pnl') or 0
cost_basis = row.get('cost_basis') or 0

# Calculate P&L percentage
if cost_basis > 0:
    pnl_pct = (unrealized_pnl / cost_basis) * 100
else:
    pnl_pct = 0
```

**Prevention**: Always use `or 0` when retrieving numeric values that might be `None`.

### 5. Field Name Mismatches

**Problem**: `KeyError` when accessing fields in data structures due to inconsistent naming.

**✅ SOLUTION**:
```python
# Use consistent field names across all data structures
position_data = {
    'ticker': position.ticker,
    'company': position.company,  # Not 'company_name'
    'avg_price': position.avg_price,  # Not 'buy_price'
    'shares': position.shares,
    'unrealized_pnl': position.unrealized_pnl,
    'cost_basis': position.cost_basis
}
```

**Prevention**: Maintain a consistent field naming convention across all data structures.

### 6. Daily P&L Calculation Issues

**Problem**: Daily P&L showing as zero or incorrect values.

**✅ SOLUTION**:
```python
# Calculate daily P&L change correctly
if prev_position and prev_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
    daily_pnl_change = position.unrealized_pnl - prev_position.unrealized_pnl
    daily_pnl_str = f"${daily_pnl_change:.2f}"
else:
    daily_pnl_str = "$0.00"
```

**Prevention**: Always check for `None` values before calculating differences.

### 7. Table Display Issues

**Problem**: Tables not displaying or showing incorrect data.

**✅ SOLUTION**:
```python
# Ensure table formatter uses correct field names
def create_portfolio_table(self, portfolio_data):
    for position in portfolio_data:
        # Use the correct field names from the data structure
        ticker = position.get('ticker', 'N/A')
        company = position.get('company', 'N/A')
        # ... etc
```

**Prevention**: Always verify field names match between data creation and table formatting.

### 8. Console Output Fallback Issues

**Problem**: `NameError: name '_FORCE_FALLBACK' is not defined`.

**✅ SOLUTION**:
```python
# In display/console_output.py
# Define variables at module level, not inside try-except blocks
_FORCE_FALLBACK = False
_FORCE_COLORAMA_ONLY = os.environ.get("FORCE_COLORAMA_ONLY", "").lower() in ("true", "1", "yes", "on")

try:
    from colorama import init, Fore, Back, Style
    # ... rest of imports
except ImportError:
    # ... fallback handling
```

**Prevention**: Define global variables before try-except blocks.

## 🧪 Testing Patterns

### 1. Test P&L Calculations
```python
def test_pnl_calculations_with_real_data(self):
    """Test that P&L calculations work correctly with real position data."""
    position = Position(
        ticker="AAPL",
        shares=Decimal("10.0"),
        avg_price=Decimal("150.00"),
        cost_basis=Decimal("1500.00"),
        current_price=Decimal("155.00"),
        market_value=Decimal("1550.00"),
        unrealized_pnl=Decimal("50.00"),
        company="Apple Inc."
    )
    
    expected_pnl_pct = (position.unrealized_pnl / position.cost_basis) * 100
    assert expected_pnl_pct == Decimal("3.333333333333333333333333333")
```

### 2. Test Emoji Handling
```python
def test_emoji_handling_in_console_output(self):
    """Test that emoji handling works correctly in console output."""
    try:
        print_header("Test Header", "🚀")
    except UnicodeEncodeError:
        pytest.fail("print_header should handle emojis gracefully")
```

### 3. Test Unicode Handling
```python
def test_pandas_unicode_settings_prevent_issues(self):
    """Test that pandas Unicode settings prevent problematic character generation."""
    pd.set_option('display.unicode.ambiguous_as_wide', False)
    pd.set_option('display.unicode.east_asian_width', False)
    
    df = pd.DataFrame([{'A': 'Test', 'B': 'Value', 'C': 'P&L: +5.0%'}])
    result = df.to_string()
    
    # Check that no problematic Unicode characters are present
    problematic_chars = ['à', 'é', 'è', 'ç', 'ñ', 'ü', 'ö', 'ä']
    for char in problematic_chars:
        assert char not in result, f"Pandas generated problematic character: {char}"
```

## 🚀 Running Tests

Use the test runner script to run tests:

```bash
# Run all tests
python run_tests.py all

# Run specific test categories
python run_tests.py portfolio_display
python run_tests.py emoji_unicode
python run_tests.py financial
python run_tests.py integration

# Quick test run (stops on first failure)
python run_tests.py quick
```

## 📝 Code Review Checklist

Before submitting code, check:

- [ ] All emojis use `_safe_emoji()` function
- [ ] P&L calculations handle `None` values with `or 0`
- [ ] Field names are consistent across data structures
- [ ] Pandas Unicode options are set for table display
- [ ] Console output functions handle Unicode gracefully
- [ ] Tests cover the new functionality
- [ ] No hardcoded values that should be configurable

## 🔧 Debugging Tips

1. **Check console encoding**: `print(sys.stdout.encoding)`
2. **Test emoji display**: `print(_safe_emoji("✅"))`
3. **Verify field names**: Print the keys of your data structures
4. **Test pandas output**: Check if `df.to_string()` contains problematic characters
5. **Run tests frequently**: Use `python run_tests.py quick` during development

## 📚 Related Files

- `tests/test_portfolio_display_bugs.py` - Portfolio display bug tests
- `tests/test_emoji_unicode_bugs.py` - Emoji and Unicode bug tests
- `run_tests.py` - Test runner script
- `display/console_output.py` - Console output utilities
- `display/table_formatter.py` - Table formatting utilities
