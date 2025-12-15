# Contributor-User Separation: Key Design Decision

## The Insight

**One Contributor (Investor) → Multiple Dashboard Users (Logins)**

A single contributor who invested money may have multiple people who need to view their account:
- The contributor themselves (owner)
- Their assistant (viewer)
- Their accountant (viewer)
- Their spouse (viewer/manager)

All viewing the **same contributor's** investment data from different logins.

## The Problem with Current Schema

Current design conflates:
- **Contributors** = People who invested money
- **Users** = People who can log in to dashboard

These are **different concepts** that need separate tables with a many-to-many relationship.

## The Solution

### Three Tables

1. **`contributors`** - The actual investors
   - One row per investor
   - Stores: name, email, contact info, KYC status

2. **`user_profiles`** - Dashboard login accounts
   - One row per login
   - Stores: email, name, role (user/admin)

3. **`contributor_access`** - Junction table (many-to-many)
   - Links users to contributors they can view
   - Stores: access_level (viewer/manager/owner), granted_by, granted_at

### Relationships

```
contributors (1) ←→ (many) contributor_access (many) ←→ (1) user_profiles
```

One contributor can have many users who can view their account.
One user can view many contributors (if they manage multiple accounts).

## Example Scenarios

### Scenario 1: Personal Account
```
Contributor: "Lance Colton" (lance.colton@gmail.com)
├── User: lance.colton@gmail.com → owner access
├── User: assistant@lancecolton.com → viewer access  
└── User: accountant@example.com → viewer access
```

### Scenario 2: Family Trust
```
Contributor: "Smith Family Trust" (trust@smith.com)
├── User: john.smith@gmail.com → owner access
├── User: jane.smith@gmail.com → owner access
└── User: trustee@smith.com → manager access
```

### Scenario 3: Financial Advisor
```
Contributor: "John Doe" (john@example.com)
└── User: advisor@wealthfirm.com → manager access
    (Advisor can view/manage client's account)
```

## Migration Files

1. **`DF_008_link_fund_contributions_to_funds.sql`**
   - Links fund_contributions to funds table
   - Adds fund_id foreign keys

2. **`DF_009_create_contributors_and_access.sql`**
   - Creates contributors table
   - Creates contributor_access table
   - Migrates existing data
   - Auto-grants access for matching emails

## Benefits

✅ **Clear separation** of investors vs logins  
✅ **Flexible access** - multiple users per contributor  
✅ **Audit trail** - track who granted access  
✅ **Security** - revoke access without affecting contributor data  
✅ **Scalability** - easy to add new access levels  

## Next Steps

1. Run `DF_008` to link funds
2. Run `DF_009` to create contributors and access
3. Review unmatched contributions
4. Update application code to use `contributor_id`
5. Update RLS policies to use `contributor_access`

See `contributor_user_relationship_design.md` for full details.

