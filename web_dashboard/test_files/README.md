# Test Files

This directory contains test scripts for the web dashboard.

## URL Obfuscation

Test URLs are obfuscated using base64 encoding and stored in `../test_urls.keys.json` (gitignored).

To use obfuscated URLs in test files:

```python
from test_url_loader import get_test_url

# Get a test URL
url = get_test_url("FT_ARTICLE_1")
```

## Available Test URL Keys

See `../test_urls.keys.json` for available keys. Common keys:
- `FT_ARTICLE_1` - Financial Times test article
- `SITE_A_ARTICLE_1` - Test article from Site A (obfuscated)
- `SITE_B_ARTICLE_1` - Test article from Site B (obfuscated)

## Domain Keys

Domain names are also obfuscated:
- `DOMAIN_SITE_A` - Obfuscated domain for Site A
- `DOMAIN_SITE_B` - Obfuscated domain for Site B

## Adding New Test URLs

1. Encode the URL:
   ```python
   import base64
   encoded = base64.b64encode("https://example.com/article".encode()).decode()
   ```

2. Add to `../test_urls.keys.json`:
   ```json
   {
     "MY_TEST_URL": "aHR0cHM6Ly9leGFtcGxlLmNvbS9hcnRpY2xl",
     "_MY_TEST_URL_DECODED": "https://example.com/article"
   }
   ```

3. Use in test files:
   ```python
   url = get_test_url("MY_TEST_URL")
   ```

