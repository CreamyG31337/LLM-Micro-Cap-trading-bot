-- =====================================================
-- Migration: Link fund_contributions to funds table
-- =====================================================
-- This migration:
-- 1. Adds fund_id column to fund_contributions (FK to funds)
-- 2. Populates fund_id from existing fund names
-- 3. Adds fund_id to user_funds (FK to funds)
-- 4. Populates fund_id from existing fund_name values
-- 
-- This fixes the missing foreign key relationships identified
-- in the contributor schema analysis.
-- =====================================================

-- Step 1: Ensure funds table exists (from DF_005)
CREATE TABLE IF NOT EXISTS funds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    currency VARCHAR(10) NOT NULL DEFAULT 'CAD',
    fund_type VARCHAR(50) NOT NULL DEFAULT 'investment',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 2: Insert any missing fund names from fund_contributions
INSERT INTO funds (name, description, fund_type)
SELECT DISTINCT 
    fund as name,
    'Fund from contributions' as description,
    'investment' as fund_type
FROM fund_contributions
WHERE fund IS NOT NULL 
  AND fund NOT IN (SELECT name FROM funds)
ON CONFLICT (name) DO NOTHING;

-- Step 3: Add fund_id column to fund_contributions
ALTER TABLE fund_contributions
    ADD COLUMN IF NOT EXISTS fund_id INTEGER;

-- Step 4: Populate fund_id from fund name
UPDATE fund_contributions fc
SET fund_id = f.id
FROM funds f
WHERE fc.fund = f.name
  AND fc.fund_id IS NULL;

-- Step 5: Check for any orphaned records (fund names not in funds table)
-- Display orphaned records if any (Supabase-compatible)
SELECT 
    '⚠️ Orphaned Records' as section,
    'Orphaned count' as metric,
    COUNT(*)::text as value,
    string_agg(DISTINCT fund, ', ') as detail
FROM fund_contributions
WHERE fund_id IS NULL AND fund IS NOT NULL;

-- Step 6: Make fund_id NOT NULL (only if all rows have values)
-- Commented out for safety - uncomment after verifying all rows have fund_id
-- ALTER TABLE fund_contributions
--     ALTER COLUMN fund_id SET NOT NULL;

-- Step 7: Add foreign key constraint
ALTER TABLE fund_contributions
    DROP CONSTRAINT IF EXISTS fund_contributions_fund_id_fkey;

ALTER TABLE fund_contributions
    ADD CONSTRAINT fund_contributions_fund_id_fkey 
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE CASCADE;

-- Step 8: Add index for performance
CREATE INDEX IF NOT EXISTS idx_fund_contributions_fund_id 
    ON fund_contributions(fund_id);

-- Step 9: Insert any missing fund names from user_funds
INSERT INTO funds (name, description, fund_type)
SELECT DISTINCT 
    fund_name as name,
    'Fund from user assignments' as description,
    'investment' as fund_type
FROM user_funds
WHERE fund_name IS NOT NULL 
  AND fund_name NOT IN (SELECT name FROM funds)
ON CONFLICT (name) DO NOTHING;

-- Step 10: Add fund_id column to user_funds
ALTER TABLE user_funds
    ADD COLUMN IF NOT EXISTS fund_id INTEGER;

-- Step 11: Populate fund_id from fund_name
UPDATE user_funds uf
SET fund_id = f.id
FROM funds f
WHERE uf.fund_name = f.name
  AND uf.fund_id IS NULL;

-- Step 12: Add foreign key constraint for user_funds
ALTER TABLE user_funds
    DROP CONSTRAINT IF EXISTS user_funds_fund_id_fkey;

ALTER TABLE user_funds
    ADD CONSTRAINT user_funds_fund_id_fkey 
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE CASCADE;

-- Step 13: Add index for performance
CREATE INDEX IF NOT EXISTS idx_user_funds_fund_id 
    ON user_funds(fund_id);

-- Step 14: Update views to use fund_id (optional, for future)
-- Views currently use fund/fund_name, which is fine for now
-- Can be updated later when application code is migrated

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check fund_contributions linkage
SELECT 
    'fund_contributions' as table_name,
    COUNT(*) as total_rows,
    COUNT(fund_id) as rows_with_fund_id,
    COUNT(*) - COUNT(fund_id) as rows_missing_fund_id
FROM fund_contributions;

-- Check user_funds linkage
SELECT 
    'user_funds' as table_name,
    COUNT(*) as total_rows,
    COUNT(fund_id) as rows_with_fund_id,
    COUNT(*) - COUNT(fund_id) as rows_missing_fund_id
FROM user_funds;

-- List all funds
SELECT id, name, fund_type, created_at 
FROM funds 
ORDER BY name;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

-- Display success message and next steps (all in one query)
SELECT 
    '✅ Migration Complete' as section,
    'Contributions linked' as metric,
    (SELECT COUNT(*) FROM fund_contributions WHERE fund_id IS NOT NULL)::text as value,
    'fund_contributions.fund_id' as detail

UNION ALL

SELECT 
    '✅ Migration Complete' as section,
    'User funds linked' as metric,
    (SELECT COUNT(*) FROM user_funds WHERE fund_id IS NOT NULL)::text as value,
    'user_funds.fund_id' as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Note 1' as metric,
    'Old fund/fund_name columns kept for backward compatibility' as value,
    NULL::text as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Note 2' as metric,
    'Update application code to use fund_id instead of fund/fund_name' as value,
    NULL::text as detail;

