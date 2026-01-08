# Caddyfile Migration Guide

This document shows how to update your Caddyfile to route migrated pages to Flask.

## Current Setup

Your Caddyfile currently routes everything to Streamlit (port 8501).

## Adding Flask Routes

For each page migrated to Flask, add a `handle` block **before** the general Streamlit reverse_proxy.

### Example: Settings Page Migration

Add this block **before** the `reverse_proxy localhost:8501` line:

```caddy
# Settings page - route to Trading Dashboard Flask (port 5001)
handle /settings {
    reverse_proxy localhost:5001 {
        trusted_proxies private_ranges
        # Add your Cloudflare IP ranges here if using Cloudflare
    }
}

# Trading Dashboard API endpoints - route to Flask (port 5001)
# Note: Only /api/settings/* routes here, other /api/* may go to other services
handle /api/settings/* {
    reverse_proxy localhost:5001 {
        trusted_proxies private_ranges
        # Add your Cloudflare IP ranges here if using Cloudflare
    }
}
```

### Complete Example Caddyfile

```caddy
your-domain.com {
    # Your existing bind and configuration...
    # bind 192.168.x.x  # Your actual bind IP
    
    # Your existing static file handlers...
    # handle /auth_callback.html { ... }
    # handle /set_cookie.html { ... }
    # handle /login.html { ... }
    # handle_path /research/* { ... }
    
    # Settings page - route to Trading Dashboard Flask (port 5001)
    # Add this BEFORE your general Streamlit reverse_proxy
    handle /settings {
        reverse_proxy localhost:5001 {
            trusted_proxies private_ranges
            # Add your Cloudflare IP ranges here if using Cloudflare
        }
    }
    
    # Trading Dashboard API endpoints - route to Flask (port 5001)
    handle /api/settings/* {
        reverse_proxy localhost:5001 {
            trusted_proxies private_ranges
            # Add your Cloudflare IP ranges here if using Cloudflare
        }
    }
    
    # Your existing WebSocket and health check handlers...
    # handle /_stcore/stream { ... }
    # handle /health { ... }
    
    # Your existing Streamlit reverse_proxy (everything else)
    # reverse_proxy localhost:8501 { ... }
}
```

## Important Notes

1. **Order matters**: Specific routes (like `/settings`) must come **before** the general `reverse_proxy` to Streamlit
2. **Port 5001 for Trading Dashboard**: The trading dashboard Flask app runs on port 5001 to avoid conflict with NFT calculator on port 5000
3. **Flask must be running**: Ensure Trading Dashboard Flask is running on port 5001 before updating Caddy
4. **Test locally first**: Test the Flask route locally before deploying to production
5. **Multiple Flask instances**: Both Flask apps run simultaneously:
   - NFT Calculator: Port 5000 (existing)
   - Trading Dashboard: Port 5001 (new)
   - Streamlit: Port 8501 (existing)

## Testing

After updating Caddyfile:

1. Reload Caddy: `caddy reload` or restart Caddy service
2. Test Settings page: Navigate to `https://your-domain.com/settings`
3. Verify it loads from Flask (check browser dev tools Network tab)
4. Test navigation from Streamlit pages to Flask Settings
5. Test navigation back from Flask Settings to Streamlit pages

## Future Migrations

When migrating additional pages, add a new `handle` block for each page:

```caddy
# Research page - route to Trading Dashboard Flask (port 5001)
handle /research {
    reverse_proxy localhost:5001 {
        trusted_proxies private_ranges
        # Add your Cloudflare IP ranges here if using Cloudflare
    }
}
```
