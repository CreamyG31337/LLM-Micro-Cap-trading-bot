# Fund Contributors Schema - Current Issues Summary

## The Problem: 3 Tables, No Proper Links

### Current State

1. **`funds` table** (exists but unused!)
   - Created in `DF_005_clean_trade_log_add_fk.sql`
   - Has `id` (SERIAL) and `name` (VARCHAR)
   - **NOT linked to fund_contributions or user_funds**

2. **`fund_contributions` table**
   - Uses `fund VARCHAR(50)` - **NO FK to funds table**
   - Uses `contributor VARCHAR(255)` - **NO FK to any table**
   - Uses `email VARCHAR(255)` - **NO FK to user_profiles**

3. **`user_funds` table**
   - Uses `fund_name VARCHAR(50)` - **NO FK to funds table**
   - Links `user_id` → `auth.users` ✅ (this one works)

## The Issues

### ❌ Missing Foreign Keys

```sql
-- fund_contributions should have:
fund_id INTEGER REFERENCES funds(id)  -- MISSING!
contributor_id UUID REFERENCES contributors(id)  -- MISSING! (no contributors table)

-- user_funds should have:
fund_id INTEGER REFERENCES funds(id)  -- MISSING!
```

### ❌ Data Integrity Problems

1. **Fund names are strings everywhere**
   - Typos create orphaned records
   - No referential integrity
   - Can't cascade deletes/updates

2. **Contributors are just strings**
   - "Lance Colton" vs "Lance Colton " (trailing space) = different contributors
   - No way to link to dashboard users properly
   - Email matching is fragile

3. **No contributors table**
   - Can't track contributor metadata
   - Can't enforce uniqueness
   - Can't link contributors to dashboard users

## Quick Fix: Link fund_contributions to funds table

The `funds` table already exists! We just need to link it:

```sql
-- Step 1: Add fund_id column to fund_contributions
ALTER TABLE fund_contributions
    ADD COLUMN fund_id INTEGER REFERENCES funds(id) ON DELETE CASCADE;

-- Step 2: Populate fund_id from fund name
UPDATE fund_contributions fc
SET fund_id = f.id
FROM funds f
WHERE fc.fund = f.name;

-- Step 3: Make fund_id NOT NULL (after all rows have values)
ALTER TABLE fund_contributions
    ALTER COLUMN fund_id SET NOT NULL;

-- Step 4: Add index
CREATE INDEX idx_fund_contributions_fund_id ON fund_contributions(fund_id);

-- Step 5: Do the same for user_funds
ALTER TABLE user_funds
    ADD COLUMN fund_id INTEGER REFERENCES funds(id) ON DELETE CASCADE;

UPDATE user_funds uf
SET fund_id = f.id
FROM funds f
WHERE uf.fund_name = f.name;

ALTER TABLE user_funds
    ALTER COLUMN fund_id SET NOT NULL;

CREATE INDEX idx_user_funds_fund_id ON user_funds(fund_id);
```

## Full Solution: Add Contributors Table

For proper normalization, create a contributors table:

```sql
-- Create contributors table
CREATE TABLE contributors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email)
);

-- Add contributor_id to fund_contributions
ALTER TABLE fund_contributions
    ADD COLUMN contributor_id UUID REFERENCES contributors(id) ON DELETE RESTRICT;

-- Migrate existing contributors
INSERT INTO contributors (name, email)
SELECT DISTINCT contributor, email
FROM fund_contributions
WHERE contributor IS NOT NULL
ON CONFLICT (email) DO NOTHING;

-- Populate contributor_id
UPDATE fund_contributions fc
SET contributor_id = c.id
FROM contributors c
WHERE fc.contributor = c.name 
  AND (fc.email = c.email OR (fc.email IS NULL AND c.email IS NULL));
```

## Recommendation

**Phase 1 (Quick Win):** Link `fund_contributions` and `user_funds` to existing `funds` table
- Low risk
- Improves data integrity
- Non-breaking (keep old columns for now)

**Phase 2 (Future):** Create `contributors` table
- More complex migration
- Better long-term structure
- Requires application code updates

See `contributor_schema_analysis.md` for detailed migration strategy.

