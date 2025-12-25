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

## Usage

All scripts must be run from the server command line with proper authentication to the server itself. They are not accessible via web browser or HTTP requests.

