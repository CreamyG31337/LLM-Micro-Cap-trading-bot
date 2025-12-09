# Authentication Guide

## Overview

The Streamlit dashboard uses a two-tier authentication system:

1. **User Authentication** - For standard dashboard operations (viewing data, making trades)
   - Uses Supabase Auth with JWT tokens
   - Respects Row Level Security (RLS) policies
   - Users only see data for their assigned funds

2. **Admin Access** - For debug scripts and SQL operations
   - Uses service role key (`SUPABASE_SECRET_KEY`)
   - Bypasses RLS for admin operations
   - Only for server-side scripts, never exposed to users

## User Authentication Flow

1. User visits dashboard → Login page shown
2. User logs in with email/password → Supabase Auth validates
3. Supabase returns JWT access token → Stored in Streamlit session
4. All data queries use user's JWT token → RLS filters data by user's assigned funds
5. User logs out → Session cleared

## Environment Variables

### Required for Dashboard:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY` - Used for authentication API calls

### Required for Admin Scripts:
- `SUPABASE_SECRET_KEY` - Service role key (bypasses RLS)

## Using Admin Utilities

For debug scripts and SQL operations, use `admin_utils.py`:

```python
from admin_utils import get_admin_supabase_client

# Get admin client (bypasses RLS)
client = get_admin_supabase_client()
if client:
    # Can access all data regardless of RLS
    result = client.supabase.table("portfolio_positions").select("*").execute()
```

## Security Notes

- **Never expose `SUPABASE_SECRET_KEY`** to the frontend or user-facing code
- **User tokens** are stored in Streamlit session state (server-side only)
- **RLS policies** ensure users only see their assigned funds
- **Admin scripts** should be run server-side only, never in user-facing code

## User Registration

New users can register through the dashboard, but they need to:
1. Register with email/password
2. Confirm email (check Supabase email confirmation)
3. Have funds assigned via admin tools (`admin_assign_funds.py`)

## Troubleshooting

### "No data available" after login
- Check that user has funds assigned in `user_funds` table
- Verify RLS policies are correctly configured
- Check user's JWT token is valid

### Admin scripts can't access data
- Verify `SUPABASE_SECRET_KEY` is set
- Check that admin client is using `use_service_role=True`

### Authentication fails
- Verify `SUPABASE_PUBLISHABLE_KEY` is correct
- Check Supabase project URL is correct
- Ensure user exists in Supabase Auth

