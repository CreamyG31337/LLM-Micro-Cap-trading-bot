# Authentication Implementation Summary

## Changes Made

### 1. Authentication System
- **`auth_utils.py`** - New file for user authentication
  - `login_user()` - Authenticate with Supabase
  - `register_user()` - Register new users
  - `is_authenticated()` - Check if user is logged in
  - `get_user_token()` - Get user's JWT token
  - Session management functions

### 2. Updated Supabase Client
- **`supabase_client.py`** - Now supports three modes:
  - User token mode (respects RLS) - for authenticated users
  - Publishable key mode (limited access) - fallback
  - Service role mode (bypasses RLS) - admin only

### 3. Updated Streamlit App
- **`streamlit_app.py`** - Added authentication:
  - Login/Register page shown when not authenticated
  - User session stored in Streamlit session state
  - All data queries use user's JWT token
  - Logout functionality

### 4. Admin Utilities
- **`admin_utils.py`** - New file for admin operations
  - `get_admin_supabase_client()` - Uses service role key
  - For debug scripts and SQL operations only

### 5. Updated Utilities
- **`streamlit_utils.py`** - Now accepts user token
  - Automatically gets token from session if available
  - All data fetching respects RLS when user is authenticated

### 6. Updated Configuration Files
- **`.woodpecker.yml`** - Added `SUPABASE_SECRET_KEY` to deploy step
- **`env.example`** - Updated with both keys
- **Documentation** - Updated all docs with new authentication info

## Environment Variables

### Required in Woodpecker:
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` (for user authentication)
- `SUPABASE_SECRET_KEY` (for admin scripts)

### Required in Portainer Container:
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`
- `STREAMLIT_SERVER_HEADLESS=true`
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`

## Security Model

1. **User Operations** (Dashboard):
   - Users log in → Get JWT token
   - All queries use user's token
   - RLS filters data by user's assigned funds
   - Secure: Users only see their data

2. **Admin Operations** (Debug Scripts):
   - Use `admin_utils.get_admin_supabase_client()`
   - Uses service role key
   - Bypasses RLS for admin operations
   - Only for server-side scripts

## Next Steps

1. Add secrets to Woodpecker dashboard
2. Test authentication locally
3. Deploy and test in production
4. Assign funds to users via `admin_assign_funds.py`

