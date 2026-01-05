# Package Recommendation

## Overview

This system uses a third-party package for web-based AI service access. The package handles the complexity of web interface communication.

## Recommended Package

**Package:** `gemini-webapi`  
**Maintainer:** HanaokaYuzu

**Why this package:**
- ✅ Actively maintained
- ✅ Handles cookie refresh automatically
- ✅ Async support for efficient operations
- ✅ Full feature set
- ✅ Well documented
- ✅ Works with browser cookies (no API key needed)

**Installation:**
```bash
pip install gemini-webapi
```

## Our Integration

We've created a wrapper (`webai_wrapper.py`) that:
- ✅ Uses the package under the hood
- ✅ Loads cookies from `webai_cookies.json` automatically
- ✅ Maintains obfuscation system
- ✅ Provides simple synchronous interface
- ✅ **TESTED AND WORKING** ✅

## Usage

**From command line:**
```bash
python web_dashboard/webai_wrapper.py --query "Your question"
python ai_service_helper.py "Your question"
```

**From Python code:**
```python
from ai_service_helper import query_ai_service

response = query_ai_service("Your trading analysis prompt")
print(response)
```

The system automatically:
- Loads cookies from `webai_cookies.json`
- Uses obfuscated URLs (XOR encrypted)
- Handles cookie refresh (configurable)
- Works without API keys

## Best Practices

1. **Use separate browser session** for cookie extraction
2. **Keep auto-refresh disabled** for normal use (prevents browser conflicts)
3. **Enable auto-refresh** for long-running scripts
4. **Extract fresh cookies** when authentication fails
