# Cache Management Quick Reference

## Access Cache Management

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
from utils.cache_ui import show_cache_management_menu
show_cache_management_menu()
```

## Cache Management Menu Options

| Option | Action | When to Use |
|--------|--------|-------------|
| [1] View Cache Status | Display cache information | Monitor cache health |
| [2] Clear All Caches | Remove all cache data | Major issues, fresh start |
| [3] Clear Specific Cache | Clear targeted cache | Specific problems |
| [4] Update All Caches | Refresh cache data | Data freshness |

## Cache Types and Issues

### Price Cache
- **Contains**: Stock prices, market data
- **Symptoms of Issues**: Wrong stock prices, stale quotes
- **Clear When**: Price data seems incorrect or outdated

### Fundamentals Cache
- **Contains**: Company financial data, metrics
- **Symptoms of Issues**: Wrong company information, stale fundamentals
- **Clear When**: Company data appears stale or incorrect

### Exchange Rate Cache
- **Contains**: Currency conversion rates, historical rates
- **Symptoms of Issues**: Wrong CAD/USD conversions
- **Clear When**: Currency conversions seem incorrect

### Memory Caches
- **Contains**: Runtime data, temporary calculations
- **Symptoms of Issues**: Data inconsistencies, memory issues
- **Clear When**: Experiencing multiple data problems

## Troubleshooting Guide

### Stale Data Issues
1. **Check cache status** first (option 1)
2. **Clear price cache** (option 3 → Price Cache)
3. **Clear exchange rate cache** (option 3 → Exchange Rate Cache)
4. **Restart application** to rebuild caches

### Display Problems
1. **View cache status** (option 1)
2. **Clear all caches** (option 2) - requires confirmation
3. **Restart application**
4. **Check if problem persists**

### Performance Issues
1. **Monitor cache sizes** (option 1)
2. **Clear excessive caches** (option 3 → specific types)
3. **Clear all caches** if still slow (option 2)
4. **Restart application**

### Data Inconsistencies
1. **Backup first** (create backup from main menu)
2. **Clear all caches** (option 2)
3. **Restart and verify** data is correct
4. **Restore backup** if new issues appear

## Emergency Commands

### Quick Cache Status Check
```bash
python -c "
from utils.cache_manager import get_cache_manager
cache_mgr = get_cache_manager()
cache_mgr.initialize_components()
status = cache_mgr.get_cache_status()
print(f'Cache files: {status[\"total_cache_files\"]}')
print(f'Cache size: {status[\"total_cache_size_formatted\"]}')
"
```

### Clear All Caches (Emergency)
```bash
python -c "
from utils.cache_manager import get_cache_manager
cache_mgr = get_cache_manager()
cache_mgr.initialize_components()
results = cache_mgr.clear_all_caches()
print('Cache clearing completed')
"
```

### Clear Specific Cache
```python
from utils.cache_manager import get_cache_manager

cache_mgr = get_cache_manager()
cache_mgr.initialize_components()

# Clear price cache
cache_mgr.clear_specific_cache('price_cache')

# Clear exchange rate cache
cache_mgr.clear_specific_cache('exchange_rate_cache')

# Clear fundamentals cache
cache_mgr.clear_specific_cache('fundamentals_cache')
```

## Safety Tips

### Before Clearing Caches
1. **Check what will be cleared** (always view status first)
2. **Consider backing up** for important data
3. **Note current cache sizes** for comparison

### After Clearing Caches
1. **Verify system works** after cache operations
2. **Check cache rebuild** by viewing status again
3. **Monitor performance** for improvements

### Best Practices
- **Use selective clearing** when possible
- **Clear caches during market hours** for fresh data
- **Monitor cache sizes** regularly
- **Document issues** before clearing caches

## Cache Directory Structure

```
{data_dir}/.cache/
├── price_cache.pkl          # Price data
├── name_cache.json          # Company names
├── fundamentals_cache.json  # Company data
└── exchange_rates.csv      # Currency rates
```

## Integration with Other Tools

### With Backup Manager
```bash
# Clear caches before backup
python run.py  # Select 'k' -> Clear All Caches
python run.py  # Select 'b' -> Create Backup
```

### With Validation
```bash
# Validate after cache operations
python run.py  # Select 'k' -> View Cache Status
python run.py  # Run trading script
```

### Standard Troubleshooting Sequence
```bash
1. python run.py  # Select 'k' -> View Cache Status
2. python run.py  # Select 'k' -> Clear All Caches
3. python run.py  # Run trading script
4. python run.py  # Select 'k' -> View Cache Status
```

## Common Issues and Solutions

| Problem | Symptom | Solution |
|---------|---------|----------|
| Wrong prices | Stock prices show old values | Clear price cache |
| Wrong conversions | CAD/USD values incorrect | Clear exchange cache |
| Display issues | Table formatting problems | Clear all caches |
| Slow performance | System runs slowly | Clear all caches |
| Data errors | Portfolio values wrong | Clear all caches |
| Memory issues | High memory usage | Clear all caches |

## When to Call Cache Management

### Regular Maintenance
- **Weekly**: Check cache status and sizes
- **Monthly**: Clear caches for data freshness
- **After updates**: Clear caches after system changes

### Problem Resolution
- **First step**: When experiencing data issues
- **Before troubleshooting**: Eliminate cache as cause
- **After fixes**: Clear caches to apply changes

### Performance Optimization
- **When slow**: Monitor and clear excessive caches
- **Memory issues**: Clear caches to free memory
- **Space concerns**: Monitor cache directory sizes

## Quick Commands Reference

```bash
# View cache status
python run.py  # Option 'k' -> 1

# Clear all caches
python run.py  # Option 'k' -> 2

# Clear price cache
python run.py  # Option 'k' -> 3 -> 1

# Clear exchange cache
python run.py  # Option 'k' -> 3 -> 3

# Update all caches
python run.py  # Option 'k' -> 4
```

## Getting Help

For detailed documentation, see:
- [`docs/CACHE_MANAGEMENT.md`](docs/CACHE_MANAGEMENT.md) - Complete guide
- [`utils/README.md`](utils/README.md) - Technical details

## Support

If cache management doesn't resolve issues:
1. **Check system logs** for errors
2. **Try clearing all caches**
3. **Restart the application**
4. **Check for recent updates**
5. **Review troubleshooting guide** in main documentation
