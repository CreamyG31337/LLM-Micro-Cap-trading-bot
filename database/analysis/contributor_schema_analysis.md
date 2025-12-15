# Fund Contributors Schema Analysis

## Current State

### Tables Related to Contributors

1. **`fund_contributions`** (Main table)
   - Stores individual contribution/withdrawal transactions
   - Fields: `id`, `fund` (VARCHAR), `contributor` (VARCHAR), `email` (VARCHAR), `amount`, `contribution_type`, `timestamp`, `notes`
   - **Issues:**
     - `fund` is VARCHAR(50) - **NO FOREIGN KEY** to a funds table
     - `contributor` is VARCHAR(255) - **NO FOREIGN KEY** to a contributors/users table
     - `email` is VARCHAR(255) - **NO FOREIGN KEY** to user_profiles (only linked via application logic)

2. **`user_profiles`** (Dashboard users)
   - Stores dashboard user accounts (authentication)
   - Fields: `id`, `user_id` (FK to auth.users), `email`, `full_name`, `role`
   - **Note:** This is for dashboard access, NOT necessarily contributors

3. **`user_funds`** (User-Fund assignments)
   - Links dashboard users to funds they can view
   - Fields: `id`, `user_id` (FK to auth.users), `fund_name` (VARCHAR)
   - **Issues:**
     - `fund_name` is VARCHAR(50) - **NO FOREIGN KEY** to a funds table
     - Links users to funds, but contributors are separate

### Views

1. **`contributor_ownership`** - Aggregates contributions by contributor
2. **`fund_contributor_summary`** - Aggregates contributions by fund

## Problems Identified

### 1. No Funds Table
- Funds are stored as **strings** (`VARCHAR(50)`) throughout the database
- No centralized `funds` table with proper IDs
- No way to enforce fund name consistency
- No way to store fund metadata (currency, type, description, etc.)

### 2. No Contributors Table
- Contributors are stored as **strings** (`VARCHAR(255)`) in `fund_contributions`
- No way to link contributors to dashboard users properly
- Email matching is done via application logic, not database constraints
- No way to track contributor metadata (contact info, KYC status, etc.)

### 3. Missing Foreign Keys
- `fund_contributions.fund` → Should FK to `funds.id` (but funds table doesn't exist)
- `fund_contributions.contributor` → Should FK to `contributors.id` (but contributors table doesn't exist)
- `fund_contributions.email` → Could FK to `user_profiles.email` (but email isn't unique in user_profiles)
- `user_funds.fund_name` → Should FK to `funds.id` (but funds table doesn't exist)

### 4. Data Integrity Issues
- Typos in fund names create orphaned records
- Typos in contributor names create duplicate "contributors"
- No referential integrity - can delete/rename funds without cascade
- Email matching is fragile (case sensitivity, Gmail dots, etc.)

## Recommended Solution

### Option 1: Full Normalization (Ideal)

Create proper tables with foreign keys:

```sql
-- 1. Create funds table
CREATE TABLE funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    currency VARCHAR(10) NOT NULL DEFAULT 'CAD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create contributors table (separate from dashboard users)
CREATE TABLE contributors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Optional link to dashboard user
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email) -- Email should be unique per contributor
);

-- 3. Update fund_contributions with FKs
ALTER TABLE fund_contributions
    ADD COLUMN fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    ADD COLUMN contributor_id UUID REFERENCES contributors(id) ON DELETE RESTRICT,
    -- Keep old columns for migration, then drop them
    DROP COLUMN fund,  -- After migration
    DROP COLUMN contributor;  -- After migration

-- 4. Update user_funds with FK
ALTER TABLE user_funds
    ADD COLUMN fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    DROP COLUMN fund_name;  -- After migration
```

### Option 2: Minimal Fix (Pragmatic)

Keep existing structure but add constraints and indexes:

```sql
-- 1. Create funds lookup table (optional, for validation)
CREATE TABLE funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Add CHECK constraints to enforce fund names
ALTER TABLE fund_contributions
    ADD CONSTRAINT check_fund_exists 
    CHECK (fund IN (SELECT name FROM funds));

-- 3. Create unique index on (contributor, email) to prevent duplicates
CREATE UNIQUE INDEX idx_contributor_email 
    ON fund_contributions(contributor, email) 
    WHERE email IS NOT NULL AND email != '';

-- 4. Add index for email lookups
CREATE INDEX idx_fund_contributions_email 
    ON fund_contributions(email) 
    WHERE email IS NOT NULL;
```

### Option 3: Hybrid Approach (Recommended)

Create funds table, keep contributors as strings but add validation:

```sql
-- 1. Create funds table
CREATE TABLE funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    currency VARCHAR(10) NOT NULL DEFAULT 'CAD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Migrate existing fund names to funds table
INSERT INTO funds (name)
SELECT DISTINCT fund FROM fund_contributions
ON CONFLICT (name) DO NOTHING;

-- 3. Add fund_id to fund_contributions (keep fund for now)
ALTER TABLE fund_contributions
    ADD COLUMN fund_id UUID REFERENCES funds(id) ON DELETE CASCADE;

-- 4. Populate fund_id from fund name
UPDATE fund_contributions fc
SET fund_id = f.id
FROM funds f
WHERE fc.fund = f.name;

-- 5. Make fund_id NOT NULL and add index
ALTER TABLE fund_contributions
    ALTER COLUMN fund_id SET NOT NULL;

CREATE INDEX idx_fund_contributions_fund_id ON fund_contributions(fund_id);

-- 6. Update user_funds similarly
ALTER TABLE user_funds
    ADD COLUMN fund_id UUID REFERENCES funds(id) ON DELETE CASCADE;

UPDATE user_funds uf
SET fund_id = f.id
FROM funds f
WHERE uf.fund_name = f.name;

-- 7. Keep both fund and fund_id for backward compatibility
-- Eventually drop fund column after all code is updated
```

## Migration Strategy

1. **Phase 1: Add funds table** (non-breaking)
   - Create `funds` table
   - Populate from existing fund names
   - Add `fund_id` columns (nullable initially)

2. **Phase 2: Populate foreign keys** (non-breaking)
   - Update all `fund_id` values from `fund` names
   - Add indexes

3. **Phase 3: Update application code** (breaking)
   - Update all queries to use `fund_id` instead of `fund`
   - Update all inserts to use `fund_id`

4. **Phase 4: Enforce constraints** (breaking)
   - Make `fund_id` NOT NULL
   - Add foreign key constraints
   - Optionally drop `fund` column

## Questions to Answer

1. **Should contributors be a separate table?**
   - Pro: Better data integrity, can track contributor metadata
   - Con: More complex, requires migration of contributor names
   - **Recommendation:** Start with funds table, add contributors table later if needed

2. **Should contributors link to dashboard users?**
   - Current: Linked via email matching in application code
   - Better: Add `user_id` FK to `user_profiles` or `auth.users`
   - **Recommendation:** Add optional `user_id` column to link contributors to dashboard users

3. **Should we keep fund names as strings?**
   - Current: All tables use VARCHAR for fund names
   - Better: Use UUID foreign keys
   - **Recommendation:** Migrate to fund_id FKs, keep fund name for display/backward compatibility

## Immediate Actions

1. ✅ **Create funds table** - Centralize fund definitions
2. ✅ **Add fund_id to fund_contributions** - Link to funds table
3. ✅ **Add fund_id to user_funds** - Link to funds table
4. ⚠️ **Update application code** - Use fund_id in queries
5. 🔄 **Consider contributors table** - If contributor metadata needed

