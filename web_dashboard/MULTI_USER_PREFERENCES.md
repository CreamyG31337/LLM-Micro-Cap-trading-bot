# Multi-User Preferences: How It Works

## The Question

When multiple dashboard users can view the same contributor's account, how are preferences handled?

## The Answer

**Preferences are per dashboard user (login), not per contributor (investor).**

## Architecture

### Tables Involved

1. **`user_profiles`** - Dashboard login accounts
   - One row per login
   - Contains `preferences JSONB` column
   - Linked to `auth.users(id)` via `user_id` FK

2. **`contributors`** - Actual investors
   - One row per investor
   - No preferences column (preferences are for dashboard users, not investors)

3. **`contributor_access`** - Many-to-many relationship
   - Links users to contributors they can view
   - Controls **data access**, not preferences

### Example Scenario

```
Contributor: "Lance Colton" (investor who put money in)
├── User: lance.colton@gmail.com
│   ├── Access: owner (via contributor_access)
│   └── Preferences: {timezone: "America/Los_Angeles", theme: "dark"}
│
├── User: assistant@lancecolton.com
│   ├── Access: viewer (via contributor_access)
│   └── Preferences: {timezone: "America/New_York", theme: "light"}
│
└── User: accountant@example.com
    ├── Access: viewer (via contributor_access)
    └── Preferences: {timezone: "UTC", theme: "light"}
```

All three users can view Lance's investment data, but each has their own preferences.

## How Preferences Are Stored

### Database Structure

```sql
-- user_profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),  -- Dashboard user
    preferences JSONB DEFAULT '{}',            -- Per-user preferences
    ...
);
```

### RLS Policies

The RLS policies ensure users can only access their own preferences:

```sql
-- Users can view their own profile (including preferences)
CREATE POLICY "Users can view their own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

-- Users can update their own profile (including preferences)
CREATE POLICY "Users can update their own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);
```

### SQL Functions

The preference functions use `auth.uid()` to identify the current dashboard user:

```sql
CREATE OR REPLACE FUNCTION get_user_preference(pref_key TEXT)
RETURNS JSONB AS $$
DECLARE
    user_uuid UUID;
BEGIN
    user_uuid := auth.uid();  -- Current dashboard user
    
    SELECT preferences->pref_key
    FROM user_profiles
    WHERE user_id = user_uuid;  -- Get preferences for current user
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## Why This Design?

### ✅ Correct Approach

1. **Personal Preferences**: Each user has their own timezone, theme, etc.
2. **Security**: Users can't see or modify other users' preferences
3. **Flexibility**: Different users viewing same data can have different UI settings
4. **Scalability**: Easy to add new preference types without schema changes

### ❌ Wrong Approach (Don't Do This)

**Storing preferences per contributor would be wrong because:**
- Multiple users viewing same contributor would share preferences
- User in New York and user in Los Angeles would see same timezone
- Can't have personal UI settings

## Code Example

```python
from user_preferences import get_user_timezone, set_user_timezone

# Get current user's timezone preference
# This uses auth.uid() internally, so each user gets their own value
timezone = get_user_timezone()  # Returns current dashboard user's timezone

# Set current user's timezone preference
# Only affects the current dashboard user, not other users viewing same contributor
set_user_timezone('America/Los_Angeles')
```

## Summary

- ✅ Preferences are stored in `user_profiles.preferences` (per dashboard user)
- ✅ Each user has their own preferences, even if viewing same contributor
- ✅ RLS policies ensure users can only access their own preferences
- ✅ SQL functions use `auth.uid()` to identify current dashboard user
- ✅ Data access (via `contributor_access`) is separate from preferences

