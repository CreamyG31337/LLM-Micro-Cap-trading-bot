-- =====================================================
-- Migration: Fix RLS Policy for Contributors Table
-- =====================================================
-- Fixes "permission denied for table users" error by
-- avoiding direct queries to auth.users in RLS policies.
-- =====================================================

-- Drop the problematic policy
DROP POLICY IF EXISTS "Users can view accessible contributors" ON contributors;

-- Recreate with safe email check using user_profiles
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
    -- FIX: Query user_profiles instead of auth.users
    normalize_email(email) = normalize_email(
        (SELECT email FROM user_profiles WHERE user_id = auth.uid())
    )
);

-- Verify policy creation
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    cmd 
FROM pg_policies 
WHERE tablename = 'contributors' 
  AND policyname = 'Users can view accessible contributors';
