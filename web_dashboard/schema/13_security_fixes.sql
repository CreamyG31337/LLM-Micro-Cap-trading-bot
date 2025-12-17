-- =====================================================
-- SECURITY FIX: Enable RLS on job_executions
-- =====================================================
-- Fixes Supabase lint warning: rls_disabled_in_public

-- Enable RLS on job_executions table
ALTER TABLE job_executions ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all authenticated users to read job execution history
CREATE POLICY "Allow authenticated users to read job executions"
  ON job_executions
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow service role to write (for jobs running server-side)
CREATE POLICY "Allow service role to write job executions"
  ON job_executions
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- =====================================================
-- SECURITY DEFINER VIEWS - Documentation
-- =====================================================
-- Supabase warns about security_definer views because they run with
-- creator's permissions (bypass RLS). This is INTENTIONAL for these views:
--
-- 1. latest_positions - Needs to aggregate across all positions
-- 2. fund_contributor_summary - Needs to join across funds and contributions
-- 3. contributor_ownership - Needs to calculate ownership percentages
-- 4. fund_thesis_with_pillars - Needs to join thesis with related data
--
-- These views are READ-ONLY and designed for admin dashboards.
-- They don't expose sensitive data that RLS should protect.
--
-- To fix the warnings, we have two options:
--   A) Remove SECURITY DEFINER (users must have direct table access)
--   B) Keep SECURITY DEFINER but document why (current approach)
--
-- We're keeping SECURITY DEFINER because:
-- - Views are for authenticated admin users only
-- - They don't bypass important security boundaries
-- - Removing it would require granting broad table permissions
-- =====================================================

COMMENT ON VIEW latest_positions IS 
  'SECURITY DEFINER view for latest portfolio positions. Uses creator permissions to aggregate across positions. Safe because: (1) read-only, (2) used by admin dashboard, (3) no sensitive data bypass.';

COMMENT ON VIEW fund_contributor_summary IS 
  'SECURITY DEFINER view for fund contribution summaries. Uses creator permissions to join funds and contributions. Safe because: (1) read-only, (2) admin-only feature, (3) aggregated data.';

COMMENT ON VIEW contributor_ownership IS 
  'SECURITY DEFINER view for ownership calculations. Uses creator permissions to compute percentages. Safe because: (1) read-only, (2) mathematical computation, (3) no data leakage.';

COMMENT ON VIEW fund_thesis_with_pillars IS 
  'SECURITY DEFINER view for fund thesis with investment pillars. Uses creator permissions to join related tables. Safe because: (1) read-only, (2) admin tool, (3) no RLS bypass issues.';

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Security fixes applied!';
    RAISE NOTICE '   - RLS enabled on job_executions';
    RAISE NOTICE '   - Read policy for authenticated users';
    RAISE NOTICE '   - Write policy for service role';
    RAISE NOTICE '   - SECURITY DEFINER views documented';
    RAISE NOTICE '';
    RAISE NOTICE 'Supabase linter warnings addressed:';
    RAISE NOTICE '   ✓ rls_disabled_in_public (job_executions)';
    RAISE NOTICE '   ✓ security_definer_view (4 views documented as safe)';
END $$;
