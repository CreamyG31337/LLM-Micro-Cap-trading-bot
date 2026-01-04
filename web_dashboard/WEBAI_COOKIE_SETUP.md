# Web AI Service Cookie Setup

## Overview

This system allows programmatic access to web-based AI services using browser cookies for authentication.

## Quick Start

### Step 1: Extract Your Cookies

**Recommended Method: Use Separate Browser Session**

1. Open a private/incognito browser window
2. Navigate to the web AI service interface
3. Log in with your account
4. Open Developer Tools (F12)
5. Go to **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
6. In the left sidebar, expand **Cookies**
7. Click on the service domain
8. Find and copy these cookies:
   - `__Secure-1PSID` (required)
   - `__Secure-1PSIDTS` (recommended)
   - Any other cookies with "Secure" or "PSID" in the name

9. Create a JSON file `webai_cookies.json` in the **project root**:
```json
{
  "__Secure-1PSID": "your-cookie-value-here",
  "__Secure-1PSIDTS": "your-cookie-value-here"
}
```

**Why use a separate browser session?**
- Prevents conflicts with your main browser session
- Allows automatic cookie refresh without affecting your regular browsing
- Isolates API usage from personal browsing

### Step 2: Test Your Cookies

```bash
# Test authentication
python web_dashboard/webai_wrapper.py --query "Test query"

# Or use the helper
python ai_service_helper.py "Test query"
```

### Step 3: Use in Your Code

```python
from ai_service_helper import query_ai_service

# Simple usage
response = query_ai_service("Your query here")
print(response)

# With auto-refresh enabled (for long-running scripts)
response = query_ai_service("Your query", auto_refresh=True)
```

## Important Notes

### Cookie Expiration
- Cookies expire after some time (varies by service)
- If authentication fails, extract fresh cookies
- The `__Secure-1PSID` cookie is the most important one

### Security
- **Never commit cookies to git!** Add `webai_cookies.json` to `.gitignore`
- Cookies give access to your account
- Keep cookies file secure and private
- Use separate browser sessions for API access

### Auto-Refresh
- **Disabled by default** to avoid conflicts with browser sessions
- Enable with `auto_refresh=True` for long-running scripts
- When enabled, cookies refresh automatically in the background
- Using a separate browser session prevents conflicts

## Troubleshooting

### "Authentication failed"
- Cookies may have expired - extract fresh ones
- Make sure you're logged into the service in your browser
- Check that cookie names are correct (case-sensitive)

### "Access forbidden" (403)
- Your account may not have access
- Check if your account is active
- Try extracting fresh cookies

### Cookie extraction fails
- Make sure you're logged into the service in your browser
- Try manual extraction method
- Check that the browser is not in incognito/private mode (for automatic extraction)

## Integration Details

The system uses obfuscated service endpoints and maintains privacy through:
- XOR-encrypted URL storage
- Generic naming conventions
- Cookie-based authentication (no API keys required)
