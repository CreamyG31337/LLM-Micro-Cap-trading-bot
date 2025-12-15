-- =====================================================
-- Migration: Update RLS Policies for Contributor-User Separation
-- =====================================================
-- This migration updates Row Level Security policies to use
-- the new contributor_access table instead of email matching.
-- 
-- Run this AFTER DF_009 (create contributors and access)
-- =====================================================

-- =====================================================
-- STEP 1: UPDATE FUND_CONTRIBUTIONS RLS
-- =====================================================

-- Drop old policy (if exists)
DROP POLICY IF EXISTS "Users can view contributions for their funds" ON fund_contributions;
DROP POLICY IF EXISTS "Users can view contributions for accessible contributors" ON fund_contributions;

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
    -- User has access via contributor_access table
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
    )
    OR
    -- Fallback: email match (for backward compatibility during migration)
    -- This handles cases where contributor_access hasn't been populated yet
    contributor_id IN (
        SELECT c.id FROM contributors c
        JOIN auth.users au ON normalize_email(c.email) = normalize_email(au.email)
        WHERE au.id = auth.uid()
          AND c.email IS NOT NULL
          AND c.email != ''
    )
);

-- Policy for INSERT (admins and users with manager/owner access)
DROP POLICY IF EXISTS "Admins can manage all contributions" ON fund_contributions;
DROP POLICY IF EXISTS "Users can insert contributions" ON fund_contributions;

CREATE POLICY "Admins can manage all contributions" 
ON fund_contributions FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Users with manager/owner access can insert contributions for their contributors
CREATE POLICY "Users can insert contributions for accessible contributors" 
ON fund_contributions FOR INSERT 
WITH CHECK (
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
          AND access_level IN ('manager', 'owner')
    )
);

-- Users with manager/owner access can update contributions for their contributors
CREATE POLICY "Users can update contributions for accessible contributors" 
ON fund_contributions FOR UPDATE 
USING (
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
          AND access_level IN ('manager', 'owner')
    )
);

-- =====================================================
-- STEP 2: UPDATE CONTRIBUTOR_ACCESS RLS
-- =====================================================

-- Enable RLS on contributor_access table
ALTER TABLE contributor_access ENABLE ROW LEVEL SECURITY;

-- Users can view their own access records
CREATE POLICY "Users can view their own contributor access" 
ON contributor_access FOR SELECT 
USING (user_id = auth.uid());

-- Admins can view all access records
CREATE POLICY "Admins can view all contributor access" 
ON contributor_access FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Admins can manage all access records
CREATE POLICY "Admins can manage all contributor access" 
ON contributor_access FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Users with owner access can grant access to their contributors
CREATE POLICY "Owners can grant access to their contributors" 
ON contributor_access FOR INSERT 
WITH CHECK (
    contributor_id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
          AND access_level = 'owner'
    )
);

-- =====================================================
-- STEP 3: UPDATE CONTRIBUTORS TABLE RLS
-- =====================================================

-- Enable RLS on contributors table
ALTER TABLE contributors ENABLE ROW LEVEL SECURITY;

-- Users can view contributors they have access to
CREATE POLICY "Users can view accessible contributors" 
ON contributors FOR SELECT 
USING (
    -- Admin sees all
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
    OR
    -- User has access via contributor_access
    id IN (
        SELECT contributor_id FROM contributor_access 
        WHERE user_id = auth.uid()
    )
    OR
    -- User's email matches contributor's email
    normalize_email(email) = normalize_email(
        (SELECT email FROM auth.users WHERE id = auth.uid())
    )
);

-- Admins can manage all contributors
CREATE POLICY "Admins can manage all contributors" 
ON contributors FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- =====================================================
-- STEP 4: UPDATE CONTRIBUTOR_OWNERSHIP VIEW RLS
-- =====================================================

-- The view itself doesn't need RLS, but we need to ensure
-- the underlying fund_contributions table policies apply
-- (Views inherit RLS from underlying tables)

-- =====================================================
-- STEP 5: CREATE HELPER FUNCTION FOR ACCESS CHECK
-- =====================================================

-- Function to check if user has access to a contributor
CREATE OR REPLACE FUNCTION user_has_contributor_access(
    target_contributor_id UUID,
    required_access_level TEXT DEFAULT 'viewer'
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Admin always has access
    IF EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check contributor_access table
    RETURN EXISTS (
        SELECT 1 FROM contributor_access 
        WHERE contributor_id = target_contributor_id
          AND user_id = auth.uid()
          AND (
              required_access_level = 'viewer'  -- Viewer can do anything
              OR access_level IN ('manager', 'owner')  -- Manager/owner for higher access
          )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

-- Display success message and next steps (all in one query)
SELECT 
    '✅ RLS Policies Updated' as section,
    'fund_contributions policies' as metric,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'fund_contributions')::text as value,
    'Uses contributor_access table' as detail

UNION ALL

SELECT 
    '✅ RLS Policies Updated' as section,
    'contributor_access policies' as metric,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'contributor_access')::text as value,
    'Users can view their own access' as detail

UNION ALL

SELECT 
    '✅ RLS Policies Updated' as section,
    'contributors policies' as metric,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'contributors')::text as value,
    'Users can view accessible contributors' as detail

UNION ALL

SELECT 
    '📝 Next Step' as section,
    'Action' as metric,
    'Update application code to use contributor_id' as value,
    NULL::text as detail;

