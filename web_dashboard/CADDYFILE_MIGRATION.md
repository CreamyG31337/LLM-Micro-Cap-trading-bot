# Caddyfile Migration Guide

This document shows how to update your Caddyfile to route migrated pages to Flask.

## Current Setup

Your Caddyfile currently routes everything to Streamlit (port 8501).

## Adding Flask Routes

For each page migrated to Flask, add a `handle` block **before** the general Streamlit reverse_proxy.

### Example: Settings Page Migration

Add this block **before** the `reverse_proxy localhost:8501` line:

```caddy
# Settings page - route to Flask (migrated from Streamlit)
handle /settings {
    reverse_proxy localhost:5000 {
        trusted_proxies private_ranges
        trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
    }
}

# API endpoints - route to Flask
handle /api/* {
    reverse_proxy localhost:5000 {
        trusted_proxies private_ranges
        trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
    }
}
```

### Complete Example Caddyfile

```caddy
ai-trading.drifting.space, aitrading.drifting.space {
    bind 192.168.100.69
    
    # Serve auth callback HTML (handles magic links & password resets)
    handle /auth_callback.html {
        root * /ai-trading/frontend
        file_server
    }
    
    # Serve set_cookie.html (sets auth cookie and redirects back)
    handle /set_cookie.html {
        root * /ai-trading/frontend
        file_server
    }
    
    # Serve login.html (simple HTML login form for browser automation)
    handle /login.html {
        root * /ai-trading/frontend
        file_server
    }
    
    # Serve Research PDF files (static file server)
    handle_path /research/* {
        root * /ai-trading/research
        file_server browse
        header Cache-Control "public, max-age=3600"
    }
    
    # Settings page - route to Trading Dashboard Flask (port 5001)
    # Note: Port 5000 is used by NFT calculator app
    handle /settings {
        reverse_proxy localhost:5001 {
            trusted_proxies private_ranges
            trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
        }
    }
    
    # Trading Dashboard API endpoints - route to Flask (port 5001)
    # Note: Only /api/settings/* routes here, other /api/* may go to NFT calc (port 5000)
    handle /api/settings/* {
        reverse_proxy localhost:5001 {
            trusted_proxies private_ranges
            trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
        }
    }
    
    # WebSocket endpoint - must be before general reverse_proxy
    handle /_stcore/stream {
        reverse_proxy localhost:8501 {
            transport http {
                versions 1.1 2
            }
        }
    }
    
    # Health check endpoint
    handle /health {
        reverse_proxy localhost:8501
    }
    
    # Serve logs directory (for AI access)
    handle_path /logs/* {
        root * /srv/logs
        file_server browse
    }
    
    # Reverse proxy to Streamlit (everything else)
    reverse_proxy localhost:8501 {
        # WebSocket support for Streamlit
        transport http {
            versions 1.1 2
        }
        trusted_proxies private_ranges
        trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
    }
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
2. Test Settings page: Navigate to `https://ai-trading.drifting.space/settings`
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
        trusted_proxies 173.245.48.0/20 ...
    }
}
```
