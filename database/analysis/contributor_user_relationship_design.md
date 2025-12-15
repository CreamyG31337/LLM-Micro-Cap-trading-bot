# Contributor-User Relationship Design

## The Key Insight

**Contributors (Investors) ≠ Dashboard Users (Logins)**

A single contributor (investor) may have multiple dashboard users who can view their account:
- Personal login (lance.colton@gmail.com)
- Assistant login (assistant@lancecolton.com)
- Accountant login (accountant@lancecolton.com)
- Family member login (spouse@example.com)

All viewing the **same contributor's** investment data.

## Current Problem

The current schema conflates these concepts:
- `fund_contributions.contributor` = investor name (string)
- `fund_contributions.email` = could be investor email OR dashboard user email
- `user_profiles` = dashboard users (authentication)
- No clear link between contributors and users

## Proposed Schema

### 1. Contributors Table (The Investors)

```sql
CREATE TABLE contributors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),  -- Primary contact email (for statements, etc.)
    phone VARCHAR(50),
    address TEXT,
    tax_id VARCHAR(50),  -- SSN, SIN, etc. (encrypted)
    kyc_status VARCHAR(50) DEFAULT 'pending',  -- pending, verified, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email)  -- One contributor per email
);
```

**Purpose:** Represents the actual investor who put money into the fund.

### 2. User Profiles Table (Dashboard Logins)

```sql
CREATE TABLE user_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',  -- user, admin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);
```

**Purpose:** Represents dashboard login accounts (authentication).

### 3. Contributor Access Table (Many-to-Many)

```sql
CREATE TABLE contributor_access (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    contributor_id UUID REFERENCES contributors(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    access_level VARCHAR(50) DEFAULT 'viewer',  -- viewer, manager, owner
    granted_by UUID REFERENCES auth.users(id),  -- Who granted this access
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- Optional expiration
    notes TEXT,
    UNIQUE(contributor_id, user_id)  -- One access record per contributor-user pair
);
```

**Purpose:** Links dashboard users to contributors they can view/manage.

### 4. Updated Fund Contributions

```sql
CREATE TABLE fund_contributions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund_id INTEGER REFERENCES funds(id) ON DELETE CASCADE,
    contributor_id UUID REFERENCES contributors(id) ON DELETE RESTRICT,  -- Can't delete contributor with contributions
    amount DECIMAL(10, 2) NOT NULL,
    contribution_type VARCHAR(20) NOT NULL,  -- CONTRIBUTION, WITHDRAWAL
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Changes:**
- `contributor_id` FK to `contributors` table (not a string!)
- Removed `contributor` VARCHAR column
- Removed `email` column (use `contributors.email` instead)

## Access Control Logic

### Who Can View What?

```sql
-- User can view contributions if:
-- 1. They have contributor_access for that contributor, OR
-- 2. They are admin, OR
-- 3. The contributor's email matches their user email (auto-access)

CREATE POLICY "Users can view contributions for accessible contributors" 
ON fund_contributions FOR SELECT 
USING (
    -- Admin can see everything
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
    OR
    -- User has explicit access via contributor_access
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
    )
    OR
    -- User's email matches contributor's email (auto-access)
    contributor_id IN (
        SELECT c.id FROM contributors c
        JOIN auth.users au ON normalize_email(c.email) = normalize_email(au.email)
        WHERE au.id = auth.uid()
    )
);
```

### Auto-Grant Access

When a user signs up, automatically grant access if their email matches a contributor:

```sql
CREATE OR REPLACE FUNCTION auto_grant_contributor_access()
RETURNS TRIGGER AS $$
BEGIN
    -- If user's email matches a contributor's email, grant access
    INSERT INTO contributor_access (contributor_id, user_id, access_level)
    SELECT c.id, NEW.id, 'owner'
    FROM contributors c
    WHERE normalize_email(c.email) = normalize_email(NEW.email)
    ON CONFLICT (contributor_id, user_id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_user_created_auto_grant_access
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION auto_grant_contributor_access();
```

## Migration Strategy

### Phase 1: Create Contributors Table

```sql
-- Step 1: Create contributors table
CREATE TABLE contributors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email)
);

-- Step 2: Migrate unique contributors from fund_contributions
INSERT INTO contributors (name, email)
SELECT DISTINCT 
    contributor as name,
    email
FROM fund_contributions
WHERE contributor IS NOT NULL
ON CONFLICT (email) DO UPDATE 
SET name = EXCLUDED.name;  -- Update name if email exists

-- Step 3: Handle contributors with same email but different names
-- (This shouldn't happen, but handle it gracefully)
```

### Phase 2: Add Contributor ID to Fund Contributions

```sql
-- Step 1: Add contributor_id column
ALTER TABLE fund_contributions
    ADD COLUMN contributor_id UUID;

-- Step 2: Populate from contributors table
UPDATE fund_contributions fc
SET contributor_id = c.id
FROM contributors c
WHERE fc.contributor = c.name 
  AND (fc.email = c.email OR (fc.email IS NULL AND c.email IS NULL));

-- Step 3: Handle edge cases (contributors not yet in table)
-- Create missing contributors
INSERT INTO contributors (name, email)
SELECT DISTINCT contributor, email
FROM fund_contributions
WHERE contributor_id IS NULL
  AND contributor IS NOT NULL
ON CONFLICT (email) DO NOTHING;

-- Step 4: Retry population
UPDATE fund_contributions fc
SET contributor_id = c.id
FROM contributors c
WHERE fc.contributor_id IS NULL
  AND fc.contributor = c.name 
  AND (fc.email = c.email OR (fc.email IS NULL AND c.email IS NULL));

-- Step 5: Make NOT NULL and add FK
ALTER TABLE fund_contributions
    ALTER COLUMN contributor_id SET NOT NULL,
    ADD CONSTRAINT fund_contributions_contributor_id_fkey 
    FOREIGN KEY (contributor_id) REFERENCES contributors(id) ON DELETE RESTRICT;
```

### Phase 3: Create Contributor Access Table

```sql
-- Step 1: Create contributor_access table
CREATE TABLE contributor_access (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    contributor_id UUID REFERENCES contributors(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    access_level VARCHAR(50) DEFAULT 'viewer',
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(contributor_id, user_id)
);

-- Step 2: Auto-grant access for matching emails
INSERT INTO contributor_access (contributor_id, user_id, access_level)
SELECT DISTINCT
    c.id as contributor_id,
    au.id as user_id,
    'owner' as access_level
FROM contributors c
JOIN auth.users au ON normalize_email(c.email) = normalize_email(au.email)
ON CONFLICT (contributor_id, user_id) DO NOTHING;
```

### Phase 4: Update RLS Policies

```sql
-- Update fund_contributions RLS to use contributor_access
DROP POLICY IF EXISTS "Users can view contributions for their funds" ON fund_contributions;

CREATE POLICY "Users can view contributions for accessible contributors" 
ON fund_contributions FOR SELECT 
USING (
    -- Admin sees all
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
    OR
    -- User has access via contributor_access
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
    )
);
```

## Example Use Cases

### Use Case 1: Single Contributor, Multiple Users

```
Contributor: "Lance Colton" (lance.colton@gmail.com)
├── User: lance.colton@gmail.com (owner access)
├── User: assistant@lancecolton.com (viewer access)
└── User: accountant@example.com (viewer access)

All three users can view Lance's contributions, but only Lance has owner access.
```

### Use Case 2: Family Account

```
Contributor: "Smith Family Trust" (trust@smith.com)
├── User: john.smith@gmail.com (owner access)
├── User: jane.smith@gmail.com (owner access)
└── User: trustee@smith.com (manager access)

Multiple family members can manage the same contributor account.
```

### Use Case 3: Financial Advisor

```
Contributor: "John Doe" (john@example.com)
└── User: advisor@wealthfirm.com (manager access)

Financial advisor can view/manage client's account without being the contributor.
```

## Benefits

1. **Clear Separation:** Contributors (investors) vs Users (logins)
2. **Flexible Access:** Multiple users per contributor
3. **Audit Trail:** Track who granted access and when
4. **Security:** Can revoke access without affecting contributor data
5. **Scalability:** Easy to add new access levels or permissions

## Questions to Consider

1. **Should contributors have their own login?**
   - Option A: Contributor email automatically gets owner access
   - Option B: Contributors must be explicitly granted access
   - **Recommendation:** Option A (auto-grant) with Option B (explicit) for others

2. **What access levels are needed?**
   - `viewer`: Can view data
   - `manager`: Can view and manage (add contributions, etc.)
   - `owner`: Full control (can grant access to others)
   - **Recommendation:** Start with viewer/owner, add manager later if needed

3. **Should we keep old columns?**
   - Keep `fund_contributions.contributor` and `email` for backward compatibility?
   - **Recommendation:** Keep during migration, drop after code is updated

