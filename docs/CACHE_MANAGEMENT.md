# Cache Management System

## Overview

The cache management system provides comprehensive control over all cached data in the trading bot. It manages multiple cache types, provides status monitoring, and offers both automated and manual cache operations.

## Cache Types

### 1. Price Cache
- **Location**: `{data_dir}/.cache/price_cache.pkl`, `{data_dir}/.cache/name_cache.json`
- **Contains**: Market price data, company names, ticker corrections
- **Size**: Typically 10-50KB per fund
- **When to clear**: Stock prices seem incorrect or outdated

### 2. Fundamentals Cache
- **Location**: `{data_dir}/.cache/fundamentals_cache.json`
- **Contains**: Company financial data and metrics
- **Size**: Typically 5-20KB per fund
- **When to clear**: Company data appears stale or incorrect

### 3. Exchange Rate Cache
- **Location**: `{data_dir}/.cache/exchange_rates.csv`
- **Contains**: Currency conversion rates and historical rates
- **Size**: Typically 1-5KB per fund
- **When to clear**: Currency conversions seem wrong

### 4. Memory Caches
- **Location**: In-memory only
- **Contains**: Runtime data for PriceCache, CurrencyHandler, MarketDataFetcher
- **Size**: Varies based on usage
- **When to clear**: Data inconsistencies or memory issues

## Cache Management Access

### From Main Menu
```bash
python run.py
# Select option 'k' - Manage Cache
```

### From Trading Script
```bash
python trading_script.py --data-dir "your_fund"
# Select 'cache' from trading menu
```

### Direct Access
```python
from utils.cache_manager import get_cache_manager
from utils.cache_ui import show_cache_management_menu

# Direct cache management
cache_mgr = get_cache_manager()
cache_mgr.initialize_components()

# Show cache menu
show_cache_management_menu()
```

## Cache Operations

### View Cache Status
Displays comprehensive cache information:
- Total cache files and size
- Status of each cache type
- File counts and sizes
- Cache enablement status

### Clear All Caches
**⚠️ Destructive Operation**

Removes all cache data with confirmation:
- Clears all cache directories
- Resets in-memory caches
- Rebuilds cache structure

### Clear Specific Cache
**Targeted Operation**

Selectively clear cache types:
- Price cache (market data)
- Fundamentals cache (company data)
- Exchange rate cache (currency data)

### Update All Caches
**Refresh Operation**

Refreshes cache data:
- Clears existing cache data
- Triggers rebuild with current market data
- Updates exchange rates and fundamentals

## When to Use Cache Management

### Troubleshooting Scenarios

#### Stale Data
**Symptoms**: Stock prices show old values, portfolio values seem incorrect
**Solution**: Clear price cache and exchange rate cache
```bash
# From main menu, select 'k' -> Clear Specific Cache -> Price Cache
```

#### Display Issues
**Symptoms**: Tables show incorrect data, formatting problems
**Solution**: Clear all caches and restart
```bash
# From main menu, select 'k' -> Clear All Caches
```

#### Currency Conversion Problems
**Symptoms**: CAD/USD conversions show wrong values
**Solution**: Clear exchange rate cache
```bash
# From main menu, select 'k' -> Clear Specific Cache -> Exchange Rate Cache
```

#### Memory Issues
**Symptoms**: System slow, high memory usage, data inconsistencies
**Solution**: Clear all caches
```bash
# From main menu, select 'k' -> Clear All Caches
```

### Maintenance Schedule

#### Weekly
- Check cache status
- Monitor cache sizes
- Clear if approaching 100MB

#### Monthly
- Clear all caches for data freshness
- Verify cache functionality
- Check for orphaned cache files

#### After Updates
- Clear all caches after system updates
- Verify cache compatibility
- Test cache operations

## Cache Management Commands

### Quick Cache Status
```bash
python -c "
from utils.cache_manager import get_cache_manager
cache_mgr = get_cache_manager()
cache_mgr.initialize_components()
status = cache_mgr.get_cache_status()
print(f'Total cache size: {status[\"total_cache_size_formatted\"]}')
print(f'Total files: {status[\"total_cache_files\"]}')
"
```

### Clear Specific Cache Type
```python
from utils.cache_manager import get_cache_manager

cache_mgr = get_cache_manager()
cache_mgr.initialize_components()

# Clear price cache
results = cache_mgr.clear_specific_cache('price_cache')
print(f"Price cache clear: {results['success']}")

# Clear exchange rate cache
results = cache_mgr.clear_specific_cache('exchange_rate_cache')
print(f"Exchange rate cache clear: {results['success']}")
```

### Clear All Caches
```python
from utils.cache_manager import get_cache_manager

cache_mgr = get_cache_manager()
cache_mgr.initialize_components()

results = cache_mgr.clear_all_caches()
success_count = sum(1 for r in results.values() if r['success'])
print(f"Cleared {success_count}/{len(results)} cache types")
```

## Safety Features

### Confirmation Prompts
All destructive operations require confirmation:
```bash
⚠️ This will clear ALL cache files and data!
Total files to be removed: 4
Total size: 112.3 KB

Are you sure you want to clear ALL caches? (yes/NO):
```

### Graceful Error Handling
- Missing components handled gracefully
- Partial failures don't break entire operation
- Clear error messages with recovery suggestions

### Component Isolation
- Each cache type can be managed independently
- Cache clearing doesn't affect trading data
- Safe to use during trading operations

## Performance Impact

### Cache Clearing Impact
- **Immediate**: Temporary loss of cached data
- **Short-term**: System rebuilds caches as needed
- **Long-term**: Fresh data improves accuracy

### Memory Usage
- Cache clearing frees memory
- Rebuilt caches may use different amounts
- Monitor system resources after operations

### Data Freshness
- Clearing caches ensures fresh data
- Rebuilding caches pulls current market data
- Improved accuracy for portfolio calculations

## Integration with Other Systems

### Backup Manager
```bash
# Clear caches before creating backup
python run.py  # Select 'k' -> Clear All Caches
# Then create backup
python run.py  # Select 'b' -> Create Backup
```

### Validation System
```bash
# Validate data after cache operations
python run.py  # Select 'k' -> View Cache Status
# Then validate portfolio
python run.py  # Run main script with --validate-only
```

### Troubleshooting Workflow
```bash
# Standard troubleshooting sequence:
1. python run.py  # Select 'k' -> View Cache Status
2. python run.py  # Select 'k' -> Clear All Caches
3. python run.py  # Run main trading script
4. python run.py  # Select 'k' -> View Cache Status (verify rebuild)
```

## Cache Directory Structure

```
{data_dir}/.cache/
├── price_cache.pkl          # Price data cache
├── name_cache.json          # Company names cache
├── fundamentals_cache.json  # Company data cache
└── exchange_rates.csv      # Currency conversion cache
```

### Cache File Details

#### price_cache.pkl
- **Format**: Python pickle
- **Contains**: Price data DataFrames, company names, ticker corrections
- **Size**: Largest cache file, grows with more tickers
- **Persistence**: Survives system restarts

#### name_cache.json
- **Format**: JSON
- **Contains**: Ticker symbol to company name mappings
- **Size**: Small, grows slowly
- **Persistence**: Human-readable format

#### fundamentals_cache.json
- **Format**: JSON
- **Contains**: Company financial metrics and data
- **Size**: Moderate, depends on number of companies
- **Persistence**: Survives system restarts

#### exchange_rates.csv
- **Format**: CSV
- **Contains**: Currency conversion rates with timestamps
- **Size**: Small, historical rate data
- **Persistence**: Human-readable format

## Best Practices

### Safe Cache Management
1. **Check status first** - Always view cache status before operations
2. **Use selective clearing** - Clear only problematic caches when possible
3. **Backup before major operations** - Consider backup before clearing all caches
4. **Monitor after operations** - Verify system works correctly after cache operations

### Performance Optimization
- **Regular monitoring** - Check cache sizes weekly
- **Proactive clearing** - Clear caches before they become too large
- **Selective operations** - Only clear caches causing issues
- **Update timing** - Update caches during market hours for fresh data

### Troubleshooting Integration
- **First step** - Cache management as first troubleshooting step
- **Systematic approach** - Use standard troubleshooting workflow
- **Documentation** - Document cache operations for future reference
- **Testing** - Test cache operations in test environment first

## Error Handling

### Common Issues

#### Cache Directory Not Found
**Error**: Cache directory doesn't exist
**Solution**: Cache manager creates directory automatically
**Impact**: No data loss, caches rebuild normally

#### Component Initialization Failure
**Error**: Unable to initialize cache components
**Solution**: Cache UI handles gracefully, shows error message
**Impact**: Limited functionality, manual cache management available

#### Cache Clearing Failure
**Error**: Unable to clear specific cache
**Solution**: Retry operation or clear all caches
**Impact**: Partial cache data may remain

### Recovery Procedures

#### Partial Cache Clearing
1. Retry the operation
2. Clear all caches if specific clearing fails
3. Restart the application
4. Check disk permissions

#### Corrupted Cache Files
1. Clear all caches
2. Restart application
3. Verify cache rebuild
4. Check system logs

#### Memory Issues After Clearing
1. Monitor system resources
2. Restart application if needed
3. Check for memory leaks
4. Consider selective cache clearing

## Future Enhancements

### Planned Features
- **Cache size limits** - Automatic cache size management
- **Cache expiration** - Time-based cache invalidation
- **Cache compression** - Compressed cache storage
- **Cache warming** - Pre-populate critical caches
- **Cache analytics** - Detailed cache usage statistics
- **Cache migration** - Seamless cache format upgrades

### Integration Opportunities
- **Database integration** - Cache management for database backends
- **Cloud storage** - Remote cache management
- **Multi-user support** - Shared cache management
- **Backup integration** - Automatic cache backup/restore

## Support

### Getting Help
- **Documentation**: This comprehensive guide
- **Menu access**: Available from main menu option 'k'
- **Direct access**: Import cache management modules directly
- **Error reporting**: Check system logs for detailed errors

### Reporting Issues
- **Cache status**: Include cache status output
- **Error messages**: Include full error messages
- **System information**: Include system and version information
- **Steps to reproduce**: Document steps leading to issue

## Quick Reference

### Cache Management Menu Options
| Option | Description | Use Case |
|--------|-------------|----------|
| 1 | View Cache Status | Monitor cache health |
| 2 | Clear All Caches | Major cache issues |
| 3 | Clear Specific Cache | Targeted cache problems |
| 4 | Update All Caches | Data freshness |

### Common Cache Issues and Solutions
| Issue | Symptom | Solution |
|-------|---------|----------|
| Stale prices | Old stock prices | Clear price cache |
| Wrong conversions | Incorrect CAD/USD | Clear exchange cache |
| Display problems | Table formatting issues | Clear all caches |
| Memory issues | Slow performance | Clear all caches |
| Data inconsistencies | Portfolio value errors | Clear all caches |

### Emergency Cache Commands
```bash
# Quick cache status
python run.py  # Select 'k' -> View Cache Status

# Clear all caches (emergency)
python run.py  # Select 'k' -> Clear All Caches

# Clear specific cache
python run.py  # Select 'k' -> Clear Specific Cache
```
