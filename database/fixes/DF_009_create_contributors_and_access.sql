-- =====================================================
-- Migration: Create Contributors Table and Access Control
-- =====================================================
-- This migration:
-- 1. Creates contributors table (the actual investors)
-- 2. Creates contributor_access table (many-to-many: users can view contributors)
-- 3. Migrates existing contributor data
-- 4. Links fund_contributions to contributors
-- 5. Auto-grants access to users whose email matches contributor email
--
-- Key Design: Contributors (investors) are separate from Users (dashboard logins)
-- One contributor can have multiple users who can view their account
-- =====================================================

-- =====================================================
-- STEP 1: CREATE CONTRIBUTORS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS contributors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    kyc_status VARCHAR(50) DEFAULT 'pending',  -- pending, verified, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email)  -- One contributor per email
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_contributors_email ON contributors(email);
CREATE INDEX IF NOT EXISTS idx_contributors_name ON contributors(name);

-- =====================================================
-- STEP 2: MIGRATE EXISTING CONTRIBUTORS
-- =====================================================

-- Migrate unique contributors from fund_contributions
-- Use the most common email for each contributor name
INSERT INTO contributors (name, email)
SELECT DISTINCT ON (contributor)
    contributor as name,
    -- Use the most common email for this contributor (if multiple exist)
    (SELECT email 
     FROM fund_contributions fc2 
     WHERE fc2.contributor = fc.contributor 
       AND fc2.email IS NOT NULL 
       AND fc2.email != ''
     GROUP BY email 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) as email
FROM fund_contributions fc
WHERE contributor IS NOT NULL
  AND contributor != ''
ON CONFLICT (email) DO UPDATE 
SET name = EXCLUDED.name;  -- Update name if email already exists

-- Handle contributors with NULL or empty email
-- Create them with NULL email (will need manual linking later)
INSERT INTO contributors (name, email)
SELECT DISTINCT contributor, NULL
FROM fund_contributions
WHERE contributor IS NOT NULL
  AND contributor != ''
  AND contributor NOT IN (SELECT name FROM contributors WHERE email IS NOT NULL)
  AND (email IS NULL OR email = '')
ON CONFLICT DO NOTHING;

-- =====================================================
-- STEP 3: CREATE CONTRIBUTOR ACCESS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS contributor_access (
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contributor_access_contributor ON contributor_access(contributor_id);
CREATE INDEX IF NOT EXISTS idx_contributor_access_user ON contributor_access(user_id);

-- =====================================================
-- STEP 4: AUTO-GRANT ACCESS FOR MATCHING EMAILS
-- =====================================================

-- Grant access to users whose email matches a contributor's email
INSERT INTO contributor_access (contributor_id, user_id, access_level)
SELECT DISTINCT
    c.id as contributor_id,
    au.id as user_id,
    'owner' as access_level  -- Contributor gets owner access
FROM contributors c
JOIN auth.users au ON normalize_email(c.email) = normalize_email(au.email)
WHERE c.email IS NOT NULL
  AND c.email != ''
ON CONFLICT (contributor_id, user_id) DO NOTHING;

-- =====================================================
-- STEP 5: ADD CONTRIBUTOR_ID TO FUND_CONTRIBUTIONS
-- =====================================================

-- Add contributor_id column
ALTER TABLE fund_contributions
    ADD COLUMN IF NOT EXISTS contributor_id UUID;

-- Populate contributor_id from contributors table
-- Match by name and email (prefer exact match)
UPDATE fund_contributions fc
SET contributor_id = c.id
FROM contributors c
WHERE fc.contributor_id IS NULL
  AND fc.contributor = c.name
  AND (
    -- Exact email match
    (fc.email IS NOT NULL AND fc.email = c.email)
    OR
    -- Both NULL/empty
    (fc.email IS NULL OR fc.email = '') 
    AND (c.email IS NULL OR c.email = '')
  );

-- Handle remaining unmatched (by name only, if email doesn't match)
UPDATE fund_contributions fc
SET contributor_id = c.id
FROM contributors c
WHERE fc.contributor_id IS NULL
  AND fc.contributor = c.name
  AND NOT EXISTS (
    -- Don't match if there's a better match with email
    SELECT 1 FROM contributors c2
    WHERE c2.name = fc.contributor
      AND c2.email = fc.email
      AND fc.email IS NOT NULL
      AND fc.email != ''
  );

-- =====================================================
-- STEP 6: VERIFY MIGRATION
-- =====================================================

-- Display migration summary (all in one query for Supabase)
SELECT 
    '📊 Migration Summary' as section,
    'Total contributions' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM fund_contributions

UNION ALL

SELECT 
    '📊 Migration Summary' as section,
    'Matched contributions' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM fund_contributions 
WHERE contributor_id IS NOT NULL

UNION ALL

SELECT 
    '📊 Migration Summary' as section,
    'Unmatched contributions' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM fund_contributions 
WHERE contributor_id IS NULL

UNION ALL

SELECT 
    '📊 Migration Summary' as section,
    'Total contributors created' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM contributors

UNION ALL

SELECT 
    '📊 Migration Summary' as section,
    'Contributors with user access' as metric,
    COUNT(DISTINCT contributor_id)::text as value,
    NULL::text as detail
FROM contributor_access

UNION ALL

-- Show unmatched contributions (if any)
SELECT 
    '⚠️ Unmatched Contributions' as section,
    contributor as metric,
    COUNT(*)::text as value,
    COALESCE(email, 'No email') || ' | ' || fund as detail
FROM fund_contributions
WHERE contributor_id IS NULL
GROUP BY contributor, email, fund
ORDER BY COUNT(*) DESC
LIMIT 20;

-- =====================================================
-- STEP 7: UPDATE RLS POLICIES (OPTIONAL - COMMENTED OUT)
-- =====================================================

-- Uncomment after verifying the migration works correctly
-- This updates RLS to use contributor_access instead of email matching

/*
-- Drop old policy
DROP POLICY IF EXISTS "Users can view contributions for their funds" ON fund_contributions;

-- Create new policy using contributor_access
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
    OR
    -- Fallback: email match (for backward compatibility during migration)
    contributor_id IN (
        SELECT c.id FROM contributors c
        JOIN auth.users au ON normalize_email(c.email) = normalize_email(au.email)
        WHERE au.id = auth.uid()
    )
);
*/

-- =====================================================
-- STEP 8: CREATE HELPER FUNCTIONS
-- =====================================================

-- Function to grant access to a contributor
CREATE OR REPLACE FUNCTION grant_contributor_access(
    contributor_email TEXT,
    user_email TEXT,
    access_level TEXT DEFAULT 'viewer'
)
RETURNS JSON AS $$
DECLARE
    target_contributor_id UUID;
    target_user_id UUID;
    result JSON;
BEGIN
    -- Get contributor ID
    SELECT id INTO target_contributor_id
    FROM contributors
    WHERE normalize_email(email) = normalize_email(contributor_email);
    
    IF target_contributor_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'message', format('Contributor with email % not found', contributor_email)
        );
    END IF;
    
    -- Get user ID
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE normalize_email(email) = normalize_email(user_email);
    
    IF target_user_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'message', format('User with email % not found', user_email)
        );
    END IF;
    
    -- Grant access
    INSERT INTO contributor_access (contributor_id, user_id, access_level, granted_by)
    VALUES (target_contributor_id, target_user_id, access_level, auth.uid())
    ON CONFLICT (contributor_id, user_id) 
    DO UPDATE SET 
        access_level = EXCLUDED.access_level,
        granted_by = EXCLUDED.granted_by,
        granted_at = NOW();
    
    RETURN json_build_object(
        'success', true,
        'message', format('Access granted: % can view %', user_email, contributor_email)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to revoke access
CREATE OR REPLACE FUNCTION revoke_contributor_access(
    contributor_email TEXT,
    user_email TEXT
)
RETURNS JSON AS $$
DECLARE
    target_contributor_id UUID;
    target_user_id UUID;
    rows_deleted INTEGER;
BEGIN
    -- Get IDs
    SELECT id INTO target_contributor_id FROM contributors
    WHERE normalize_email(email) = normalize_email(contributor_email);
    
    SELECT id INTO target_user_id FROM auth.users
    WHERE normalize_email(email) = normalize_email(user_email);
    
    IF target_contributor_id IS NULL OR target_user_id IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Contributor or user not found');
    END IF;
    
    -- Revoke access
    DELETE FROM contributor_access
    WHERE contributor_id = target_contributor_id
      AND user_id = target_user_id;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN json_build_object(
        'success', rows_deleted > 0,
        'message', format('Access revoked: % can no longer view %', user_email, contributor_email)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

-- Display success message and next steps (all in one query)
SELECT 
    '✅ Migration Complete' as section,
    'Contributors table created' as metric,
    (SELECT COUNT(*) FROM contributors)::text as value,
    'contributors' as detail

UNION ALL

SELECT 
    '✅ Migration Complete' as section,
    'Access records created' as metric,
    (SELECT COUNT(*) FROM contributor_access)::text as value,
    'contributor_access' as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Step 1' as metric,
    'Review unmatched contributions (if any)' as value,
    NULL::text as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Step 2' as metric,
    'Manually link contributors to users if needed' as value,
    NULL::text as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Step 3' as metric,
    'Update application code to use contributor_id' as value,
    NULL::text as detail

UNION ALL

SELECT 
    '📝 Next Steps' as section,
    'Step 4' as metric,
    'Run DF_010 to update RLS policies' as value,
    NULL::text as detail;

