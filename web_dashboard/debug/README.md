# Debug Scripts

This directory contains debugging and utility scripts for the Postgres database.

## Security

**IMPORTANT**: These scripts are command-line utilities and are NOT accessible via web interface.

- ✅ **Safe**: These are Python scripts that must be run from the server command line
- ✅ **Protected**: No web routes expose these scripts
- ✅ **No Remote Execution**: Cannot be executed remotely via HTTP
- ✅ **Admin Only**: Any related web features (like `/dev/sql`) require admin authentication

## Available Scripts

### `postgres_utils.py`
Command-line utilities for Postgres operations:
```bash
python web_dashboard/debug/postgres_utils.py --test
python web_dashboard/debug/postgres_utils.py --info
python web_dashboard/debug/postgres_utils.py --stats
```

### `postgres_shell.py`
Interactive SQL shell:
```bash
python web_dashboard/debug/postgres_shell.py
```

### `test_postgres_connection.py`
Test which hostname works from your environment:
```bash
python web_dashboard/debug/test_postgres_connection.py
```

### `verify_postgres_production.py`
Comprehensive production verification:
```bash
python web_dashboard/debug/verify_postgres_production.py
```

### Portfolio Performance Debug Scripts

Debug scripts to investigate Portfolio Performance graph issues:

#### `debug_portfolio_performance_simple.py`
Simplified test - just calls the calculation function and shows results:
```bash
cd web_dashboard
.\venv\Scripts\activate  # Windows
python debug/debug_portfolio_performance_simple.py
```

#### `debug_portfolio_performance.py`
Comprehensive debug - tests data queries, calculations, and step-by-step analysis:
```bash
cd web_dashboard
.\venv\Scripts\activate  # Windows
python debug/debug_portfolio_performance.py
```

#### `debug_flask_route_context.py`
Tests Flask route context and caching behavior:
```bash
cd web_dashboard
.\venv\Scripts\activate  # Windows
python debug/debug_flask_route_context.py
```

**Note**: Edit the `test_fund` variable in each script to test with your specific fund name.

## Usage

All scripts must be run from the server command line with proper authentication to the server itself. They are not accessible via web browser or HTTP requests.

**For Portfolio Performance Debug Scripts**: Activate the web_dashboard venv first, then run from the web_dashboard directory.
