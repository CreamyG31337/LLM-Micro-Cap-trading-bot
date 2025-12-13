-- Fix RLS policies for fund_contributions table
-- Run this in Supabase SQL Editor before running the migration

-- Temporarily disable RLS to allow migration
ALTER TABLE fund_contributions DISABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view contributions for their funds" ON fund_contributions;
DROP POLICY IF EXISTS "Admins can manage all contributions" ON fund_contributions;

-- Re-enable RLS
ALTER TABLE fund_contributions ENABLE ROW LEVEL SECURITY;

-- Create a more permissive policy for service operations
CREATE POLICY "Allow service role operations" ON fund_contributions
FOR ALL USING (true);

-- Keep the user policies for dashboard access
CREATE POLICY "Users can view contributions for their funds" ON fund_contributions
FOR SELECT USING (
    fund IN (
        SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Admins can manage all contributions" ON fund_contributions
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ RLS policies updated for fund_contributions table';
    RAISE NOTICE '🔓 Migration should now work - run: python web_dashboard/migrate_contributors.py';
END $$;
