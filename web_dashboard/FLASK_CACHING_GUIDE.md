# Flask Caching Guide

## Overview

This guide explains how to use Flask caching for data-heavy pages, providing functionality similar to Streamlit's `@st.cache_data` and `@st.cache_resource` decorators.

## Installation

Flask-Caching is already included in `requirements.txt`. Install it with:

```bash
pip install Flask-Caching
```

## Quick Start

### Basic Usage

```python
from flask_cache_utils import cache_data, cache_resource

# Cache function results with TTL (like @st.cache_data)
@cache_data(ttl=300)  # Cache for 5 minutes
def get_expensive_data(param1, param2):
    # Expensive database query or API call
    return expensive_operation()

# Cache resources (like @st.cache_resource)
@cache_resource
def get_database_client():
    return DatabaseClient()
```

## Migration from Streamlit

### Before (Streamlit)

```python
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_statistics(_repo, refresh_key: int):
    return _repo.get_article_statistics(days=90)
```

### After (Flask)

```python
from flask_cache_utils import cache_data

@cache_data(ttl=60)  # show_spinner not needed in Flask
def get_cached_statistics(repo, refresh_key: int):
    return repo.get_article_statistics(days=90)
```

**Key Differences:**
- Remove `_repo` prefix (no need to mark parameters for cache key exclusion)
- Remove `show_spinner` parameter (Flask doesn't have UI spinners)
- Function signature stays the same otherwise

## Cache Version Support

The caching system integrates with `cache_version.py` for manual cache invalidation, just like Streamlit:

```python
from flask_cache_utils import cache_data
from cache_version import get_cache_version

@cache_data(ttl=300)
def get_portfolio_data(fund: str, _cache_version: str = None):
    if _cache_version is None:
        from cache_version import get_cache_version
        _cache_version = get_cache_version()
    # ... fetch data ...
    return data
```

When `bump_cache_version()` is called (e.g., after portfolio updates), all cached functions will automatically re-fetch data.

## Common Patterns

### 1. Database Queries

```python
@cache_data(ttl=60)  # Cache for 1 minute
def get_recent_articles(repo, days: int = 30):
    return repo.get_articles_by_date_range(days=days)
```

### 2. API Calls

```python
@cache_data(ttl=3600)  # Cache for 1 hour
def get_exchange_rates(currencies: List[str]):
    # Expensive API call
    return fetch_rates_from_api(currencies)
```

### 3. Resource Caching (DB Connections, Clients)

```python
@cache_resource
def get_supabase_client():
    from supabase_client import SupabaseClient
    return SupabaseClient()
```

### 4. User-Specific Caching

```python
@cache_data(ttl=300)
def get_user_portfolio(user_id: str, fund: str):
    # Cache is automatically keyed by user_id and fund
    return fetch_portfolio(user_id, fund)
```

## Cache Management

### Clear Specific Cache

```python
# Clear cache for specific function call
get_cached_statistics.clear_cache(repo, refresh_key=1)

# Clear all caches for a function
get_cached_statistics.clear_all_cache()
```

### Clear All Caches

```python
from flask_cache_utils import clear_all_caches

clear_all_caches()  # Clears everything
```

### Get Cache Statistics

```python
from flask_cache_utils import get_cache_stats

stats = get_cache_stats()
print(f"Total cached keys: {stats['total_keys']}")
```

## TTL Guidelines

Based on your Streamlit usage patterns:

- **Very short (5-30s)**: Frequently changing data, active user interactions
- **Short (60-300s)**: Dashboard data, recent statistics
- **Medium (300-1800s)**: Portfolio data, article lists
- **Long (3600s+)**: Historical data, exchange rates, static content
- **None (forever)**: Historical trades, immutable data

## Backend Options

### Current: SimpleCache (In-Memory)

Default configuration uses in-memory caching. Fast but:
- Lost on server restart
- Not shared across multiple workers
- Limited by server memory

### Upgrade to Redis (Recommended for Production)

```python
# In app.py
cache = Cache(config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'CACHE_DEFAULT_TIMEOUT': 300,
})
```

Benefits:
- Persistent across restarts
- Shared across workers
- Can handle large datasets
- Better for production deployments

### Upgrade to Memcached

```python
cache = Cache(config={
    'CACHE_TYPE': 'MemcachedCache',
    'CACHE_MEMCACHED_SERVERS': ['127.0.0.1:11211'],
    'CACHE_DEFAULT_TIMEOUT': 300,
})
```

## Examples from Your Codebase

### Research Page Caching

```python
# Before (Streamlit)
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_statistics(_repo, refresh_key: int):
    return _repo.get_article_statistics(days=90)

# After (Flask)
from flask_cache_utils import cache_data

@cache_data(ttl=60)
def get_cached_statistics(repo, refresh_key: int):
    return repo.get_article_statistics(days=90)
```

### Portfolio Data Caching

```python
# Before (Streamlit)
@st.cache_data(ttl=300)
def get_current_positions(fund: Optional[str] = None, _cache_version: str = CACHE_VERSION):
    # ... fetch positions ...

# After (Flask)
from flask_cache_utils import cache_data
from cache_version import get_cache_version

@cache_data(ttl=300)
def get_current_positions(fund: Optional[str] = None, _cache_version: str = None):
    if _cache_version is None:
        _cache_version = get_cache_version()
    # ... fetch positions ...
```

## Best Practices

1. **Use appropriate TTLs**: Match your Streamlit TTL values for consistency
2. **Include cache_version**: For data that changes when portfolio updates occur
3. **Cache expensive operations**: Database queries, API calls, data transformations
4. **Don't cache user-specific mutable data**: Unless you want stale data
5. **Monitor cache hit rates**: Use `get_cache_stats()` to see cache effectiveness
6. **Clear caches after updates**: Call `bump_cache_version()` after data changes

## Troubleshooting

### Cache not working?

1. Check Flask-Caching is installed: `pip install Flask-Caching`
2. Verify cache is initialized in `app.py`
3. Check logs for cache hit/miss messages (debug level)

### Cache too large?

1. Reduce TTL values
2. Use Redis backend for better memory management
3. Implement cache size limits

### Need to invalidate cache?

1. Use `bump_cache_version()` for automatic invalidation
2. Call `clear_all_caches()` for manual clearing
3. Use function-specific `clear_cache()` methods

## Migration Checklist

When migrating a Streamlit page to Flask:

- [ ] Replace `@st.cache_data` with `@cache_data`
- [ ] Replace `@st.cache_resource` with `@cache_resource`
- [ ] Remove `show_spinner` parameter
- [ ] Remove `_repo` prefix (if used for cache exclusion)
- [ ] Update imports to use `flask_cache_utils`
- [ ] Test cache invalidation with `bump_cache_version()`
- [ ] Verify TTL values match original Streamlit implementation
- [ ] Check cache statistics to ensure caching is working
