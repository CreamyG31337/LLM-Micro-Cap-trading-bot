# Cookie Refresher Testing Guide

## Pre-Deployment Checklist

### 1. Woodpecker Secrets
Ensure these secrets are set in Woodpecker:
- ✅ `webai_cookies_json` - Initial cookies (JSON format: `{"__Secure-1PSID":"...","__Secure-1PSIDTS":"..."}`)
- ✅ `ai_service_web_url` - Optional, obfuscated web URL (e.g., `https://gemini.google.com/app`)

### 2. Local Testing (Optional)
Test the cookie refresher script locally before deploying:

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install playwright (if not already installed)
pip install playwright
playwright install chromium

# Test with existing cookies
# Make sure webai_cookies.json exists in project root
python web_dashboard/cookie_refresher.py
```

## Deployment Testing

### Step 1: Deploy
Push to `main` or `master` branch to trigger Woodpecker deployment.

### Step 2: Verify Sidecar Container
SSH into your server and check:

```bash
# Check if cookie-refresher container is running
docker ps | grep cookie-refresher

# Check container logs
docker logs cookie-refresher

# Check if cookies file exists
cat /shared/cookies/webai_cookies.json
```

### Step 3: Verify Main App Can Read Cookies
Check main app logs:

```bash
# Check main app container logs
docker logs trading-dashboard | grep -i cookie

# Or check if WebAI is working in the dashboard
# Navigate to AI Assistant page and try using "Gemini Pro" model
```

### Step 4: Test Cookie Refresh
Wait for refresh interval (default: 1 hour) or manually trigger:

```bash
# Check when last refresh happened
docker logs cookie-refresher | tail -20

# Force a refresh by restarting the container (if needed)
docker restart cookie-refresher
```

## Troubleshooting

### Sidecar Container Not Starting
- Check Woodpecker build logs for errors
- Verify Dockerfile builds successfully: `docker build -f web_dashboard/Dockerfile.cookie-refresher -t cookie-refresher:latest .`
- Check if `/shared/cookies` directory exists and has correct permissions

### Cookies Not Refreshing
- Check sidecar logs: `docker logs cookie-refresher`
- Verify `AI_SERVICE_WEB_URL` is set correctly (obfuscated URL)
- Check if initial cookies are valid
- Verify Playwright can access the web service

### Main App Can't Read Cookies
- Verify shared volume is mounted: `docker inspect trading-dashboard | grep -A 5 Mounts`
- Check if cookies file exists: `ls -la /shared/cookies/webai_cookies.json`
- Verify file permissions: `chmod 644 /shared/cookies/webai_cookies.json`

### Container Persistence
- Verify sidecar survives main app redeploy: `docker ps -a | grep cookie-refresher`
- Check restart policy: `docker inspect cookie-refresher | grep RestartPolicy`

## Expected Behavior

1. **First Deployment:**
   - Sidecar container starts
   - Initializes cookie file from `webai_cookies_json` secret
   - Performs initial cookie refresh
   - Writes cookies to `/shared/cookies/webai_cookies.json`

2. **Subsequent Deployments:**
   - Main app container restarts
   - Sidecar container **stays running** (different name)
   - Cookies remain available in shared volume
   - Main app reads cookies from shared volume

3. **Continuous Operation:**
   - Sidecar refreshes cookies every hour (configurable)
   - Main app always has fresh cookies available
   - No manual intervention needed

