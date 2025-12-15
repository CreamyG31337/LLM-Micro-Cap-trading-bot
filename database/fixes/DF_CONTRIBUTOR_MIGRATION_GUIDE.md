# Contributor-User Separation Migration Guide

## Overview

This migration implements proper separation between **Contributors** (investors) and **Users** (dashboard logins), allowing multiple users to view/manage a single contributor's account.

## Migration Order

Run these SQL scripts **in order** in Supabase SQL Editor:

1. **DF_008** - Link fund_contributions to funds table
2. **DF_009** - Create contributors table and contributor_access table
3. **DF_010** - Update RLS policies for new structure
4. **Update 02_auth.sql** - Auto-grant contributor access on signup (already updated)

## What Changes

### New Tables

1. **`contributors`** - The actual investors
   - One row per investor
   - Stores: name, email, contact info, KYC status

2. **`contributor_access`** - Many-to-many junction table
   - Links users to contributors they can view
   - Stores: access_level (viewer/manager/owner), granted_by, granted_at

### Updated Tables

1. **`fund_contributions`**
   - Adds `contributor_id` FK to `contributors` table
   - Keeps old `contributor` and `email` columns for backward compatibility

2. **`user_funds`**
   - Adds `fund_id` FK to `funds` table
   - Keeps old `fund_name` column for backward compatibility

### Updated RLS Policies

- `fund_contributions`: Now uses `contributor_access` table instead of email matching
- `contributors`: Users can only view contributors they have access to
- `contributor_access`: Users can view their own access records

## Admin Panel Updates

### New Tab: "🔐 Contributor Access"

Located in Admin Dashboard → Contributor Access tab:

- **Grant Access**: Link users to contributors with access levels (viewer/manager/owner)
- **View Current Access**: See all contributor-user relationships
- **Revoke Access**: Remove user access to contributors

### Updated Tab: "💰 Contributions"

- Now works with `contributors` table
- Can create/edit contributors
- Links contributions to contributor records

## Application Code Updates Needed

### 1. Update Queries to Use contributor_id

**Before:**
```python
result = client.supabase.table("fund_contributions").select("*").eq("contributor", "Lance Colton").execute()
```

**After:**
```python
# Get contributor ID first
contributor = client.supabase.table("contributors").select("id").eq("name", "Lance Colton").single().execute()
contributor_id = contributor.data['id']

# Then query by contributor_id
result = client.supabase.table("fund_contributions").select("*").eq("contributor_id", contributor_id).execute()
```

### 2. Update Contribution Inserts

**Before:**
```python
client.supabase.table("fund_contributions").insert({
    "fund": "Project Chimera",
    "contributor": "Lance Colton",
    "email": "lance@example.com",
    "amount": 1000.0,
    ...
}).execute()
```

**After:**
```python
# Get or create contributor
contributor = client.supabase.table("contributors").select("id").eq("email", "lance@example.com").maybe_single().execute()
if not contributor.data:
    # Create contributor
    contributor = client.supabase.table("contributors").insert({
        "name": "Lance Colton",
        "email": "lance@example.com"
    }).execute()

contributor_id = contributor.data['id']

# Insert contribution with contributor_id
client.supabase.table("fund_contributions").insert({
    "fund_id": fund_id,  # Also use fund_id instead of fund
    "contributor_id": contributor_id,
    "amount": 1000.0,
    ...
}).execute()
```

### 3. Update RLS-Aware Queries

The RLS policies now automatically filter based on `contributor_access`, so queries should work automatically. However, make sure to:

- Use `contributor_id` in WHERE clauses when filtering by contributor
- Don't rely on email matching for access control (RLS handles this)

## Testing Checklist

- [ ] Run all migration scripts in order
- [ ] Verify contributors table is populated
- [ ] Verify contributor_access table has auto-granted records for matching emails
- [ ] Test admin panel: Grant access to a user
- [ ] Test admin panel: Revoke access from a user
- [ ] Test RLS: User can only see contributors they have access to
- [ ] Test login: New user with matching email gets auto-granted access
- [ ] Test contributions tab: Can create/edit contributors
- [ ] Test contributions tab: Can add contributions linked to contributors

## Rollback Plan

If you need to rollback:

1. **Keep old columns**: The migration keeps `fund_contributions.contributor` and `email` columns, so old code still works
2. **Drop new tables**: 
   ```sql
   DROP TABLE IF EXISTS contributor_access CASCADE;
   DROP TABLE IF EXISTS contributors CASCADE;
   ```
3. **Restore old RLS policies**: See `database/setup/05_contributions.sql` for original policies

## Benefits

✅ **Clear separation** of investors vs logins  
✅ **Flexible access** - multiple users per contributor  
✅ **Audit trail** - track who granted access  
✅ **Security** - revoke access without affecting contributor data  
✅ **Scalability** - easy to add new access levels  

## Support

See these files for more details:
- `database/analysis/contributor_user_relationship_design.md` - Full design document
- `database/analysis/contributor_user_separation_summary.md` - Quick reference
- `database/fixes/DF_009_create_contributors_and_access.sql` - Migration script

