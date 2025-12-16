-- =====================================================
-- Migration: Fix RLS Policy for Fund Contributions
-- =====================================================
-- Fixes missing "Your Investment" data by allowing users
-- to view contributions where the email matches their profile,
-- not just for funds they are explicitly assigned to in user_funds.
-- =====================================================

-- Drop the restrictive policy
DROP POLICY IF EXISTS "Users can view contributions for their funds" ON fund_contributions;

-- Recreate with expanded access (Assigned Funds OR Email Match)
CREATE POLICY "Users can view contributions for their funds" 
ON fund_contributions FOR SELECT 
USING (
    -- Case 1: Fund is assigned to user in user_funds (Legacy/Standard way)
    fund IN (
        SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
    )
    OR
    -- Case 2: Contribution email matches user's verified email (Self-service way)
    -- Using normalize_email for robust matching
    normalize_email(email) = normalize_email(
        (SELECT email FROM user_profiles WHERE user_id = auth.uid())
    )
);

-- Verify policy creation
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    cmd,
    qual 
FROM pg_policies 
WHERE tablename = 'fund_contributions' 
  AND policyname = 'Users can view contributions for their funds';
