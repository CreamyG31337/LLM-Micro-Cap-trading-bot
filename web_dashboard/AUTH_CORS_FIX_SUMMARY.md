# Authentication & CORS Fix for Vercel Deployment

## 🔍 Problem Identified

Your web dashboard was showing 401/403 errors on Vercel despite being logged in because:

1. **Missing `credentials: 'include'`** in JavaScript fetch() calls
2. **No CORS configuration** to allow cross-origin cookie sharing
3. **Incorrect cookie settings** - not configured for HTTPS/cross-origin

## ✅ Fixes Applied

### 1. Frontend: Added `credentials: 'include'` to All Fetch Requests

**Files Modified:**
- `templates/index.html` - 6 fetch calls fixed
- `templates/admin.html` - 5 fetch calls fixed
- `templates/dev_dashboard.html` - 4 fetch calls fixed  
- `templates/auth.html` - 2 fetch calls fixed

**What it does:**
- Tells the browser to include cookies (session_token) in cross-origin API requests
- Without this, cookies are NOT sent automatically when making API calls

**Example:**
```javascript
// Before (broken on Vercel):
const response = await fetch('/api/portfolio');

// After (works on Vercel):
const response = await fetch('/api/portfolio', { credentials: 'include' });
```

---

### 2. Backend: Added CORS Support

**File Modified:** `web_dashboard/app.py`

**Changes:**
```python
from flask_cors import CORS

# Configure CORS to allow credentials from Vercel deployment
CORS(app, 
     supports_credentials=True,
     origins=["https://webdashboard-hazel.vercel.app", "http://localhost:5000"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"])
```

**What it does:**
- Allows the Vercel-deployed frontend to make authenticated requests to the backend
- Enables cookie sharing between different origins (cross-origin requests)
- `supports_credentials=True` is CRITICAL for cookies to work

---

### 3. Backend: Fixed Cookie Settings for Cross-Origin

**File Modified:** `web_dashboard/app.py`

**Changes to login endpoint (line 501):**
```python
# Before (broken on Vercel):
response.set_cookie('session_token', session_token, max_age=86400, httponly=True, secure=False)

# After (works on Vercel):
is_production = request.host != 'localhost:5000' and not request.host.startswith('127.0.0.1')
response.set_cookie(
    'session_token', 
    session_token, 
    max_age=86400, 
    httponly=True, 
    secure=is_production,  # True for HTTPS (Vercel), False for localhost
    samesite='None' if is_production else 'Lax'  # None required for cross-origin cookies
)
```

**Why these settings matter:**
- `secure=True`: Required for HTTPS (Vercel deployment)
- `samesite='None'`: Required for cross-origin cookie access
- `httponly=True`: Security - prevents JavaScript from accessing cookie
- Auto-detects production vs local environment

---

### 4. Dependencies: Added Flask-CORS

**File Modified:** `web_dashboard/requirements.txt`

**Added:**
```
Flask-CORS>=4.0.0
```

**You need to install this:**
```powershell
cd web_dashboard
pip install Flask-CORS
```

---

## 🚀 Deployment Steps

### For Local Testing:
1. Install the new dependency:
   ```powershell
   cd web_dashboard
   pip install Flask-CORS
   ```

2. Restart your local Flask server:
   ```powershell
   python app.py
   ```

3. Test at `http://localhost:5000`

### For Vercel Deployment:
1. **Commit and push all changes** to your Git repository
2. Vercel will auto-deploy with the new `requirements.txt`
3. **Important:** You may need to trigger a fresh deployment in Vercel dashboard

---

## 🔒 Security Notes

### What Makes This Secure:
- ✅ Cookies are `httponly` - JavaScript cannot access them (XSS protection)
- ✅ Cookies are `secure` in production - only sent over HTTPS
- ✅ CORS is restrictive - only allows specific origins
- ✅ Session tokens expire after 24 hours

### Origins Configuration:
Currently configured for:
- `https://webdashboard-hazel.vercel.app` (production)
- `http://localhost:5000` (local development)

**If your Vercel URL changes**, update line 48 in `app.py`:
```python
origins=["https://your-new-vercel-url.vercel.app", "http://localhost:5000"]
```

---

## 🧪 Testing Checklist

### After deploying, verify:

1. **Login works on Vercel:**
   - Go to `https://webdashboard-hazel.vercel.app/auth`
   - Log in with your credentials
   - Should redirect to dashboard without errors

2. **Check browser console:**
   - Press F12 to open developer tools
   - Look for Network tab
   - Verify API calls return 200 (not 401/403)
   - Check if cookies are set (Application tab → Cookies)

3. **Test API endpoints:**
   - `/api/funds` - should return fund list
   - `/api/portfolio?fund=XXX` - should return portfolio data
   - `/api/performance-chart?fund=XXX` - should return chart
   - `/api/recent-trades?fund=XXX` - should return trades

4. **Admin functionality (if admin user):**
   - `/api/admin/users` should return 200 (not 401)
   - Admin dashboard should load properly

---

## 🐛 Troubleshooting

### Still getting 401/403 errors?

1. **Clear browser cookies and cache:**
   - Press Ctrl+Shift+Delete
   - Clear all cookies and cached data
   - Try logging in again

2. **Check Vercel environment variables:**
   - Go to Vercel dashboard → Your Project → Settings → Environment Variables
   - Verify these are set:
     - `SUPABASE_URL`
     - `SUPABASE_ANON_KEY`
     - `JWT_SECRET`
     - `FLASK_SECRET_KEY`

3. **Check browser console for CORS errors:**
   - If you see "CORS policy" errors, the origin might not be whitelisted
   - Update the `origins` list in `app.py` line 48

4. **Verify session token is being set:**
   - Open browser DevTools → Application → Cookies
   - Look for `session_token` cookie
   - Should be present after logging in
   - Check its properties: Secure, HttpOnly, SameSite

### Cookie not being set?

**Possible causes:**
- Browser blocking third-party cookies (check browser settings)
- HTTPS/HTTP mismatch (verify Vercel uses HTTPS)
- Domain mismatch (origin not in CORS whitelist)

---

## 📊 Technical Details

### How Cross-Origin Cookie Authentication Works:

1. **User logs in** → `/api/auth/login` endpoint
2. **Backend creates JWT session token**
3. **Backend sets cookie** with:
   - `secure=True` (HTTPS only)
   - `samesite='None'` (allow cross-origin)
   - `httponly=True` (JavaScript can't access)
4. **Frontend makes API request** with `credentials: 'include'`
5. **Browser automatically sends cookie** with request
6. **Backend validates cookie** via `@require_auth` decorator
7. **API returns data** if valid

### CORS Headers Sent:
```
Access-Control-Allow-Origin: https://webdashboard-hazel.vercel.app
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## 🔄 Before vs After

### Before (Broken on Vercel):
```
User → Login → Cookie Set (local only)
     → API Call (no cookie sent) → ❌ 401 Unauthorized
```

### After (Working on Vercel):
```
User → Login → Cookie Set (secure, cross-origin enabled)
     → API Call (cookie sent with credentials: 'include') → ✅ 200 OK
```

---

## 📝 Files Changed Summary

1. **Frontend Changes (credentials added):**
   - `templates/index.html`
   - `templates/admin.html`
   - `templates/dev_dashboard.html`
   - `templates/auth.html`

2. **Backend Changes:**
   - `app.py` - Added CORS, fixed cookie settings
   - `requirements.txt` - Added Flask-CORS dependency

3. **Documentation:**
   - `AUTH_CORS_FIX_SUMMARY.md` (this file)

---

## ✨ Result

Your web dashboard should now work correctly on Vercel with:
- ✅ Proper authentication via cookies
- ✅ Cross-origin requests working
- ✅ Secure cookie handling (HTTPS)
- ✅ Both local and production environments supported

**Test it:** Visit `https://webdashboard-hazel.vercel.app/auth` and log in!
