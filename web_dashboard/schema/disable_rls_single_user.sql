-- =====================================================
-- DISABLE RLS FOR SINGLE USER SETUP
-- =====================================================
-- For personal use where you're the only user,
-- RLS just adds complexity without benefit
-- =====================================================

-- Disable RLS on portfolio data tables
ALTER TABLE portfolio_positions DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances DISABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics DISABLE ROW LEVEL SECURITY;

-- Drop the fund-based access policies (no longer needed)
DROP POLICY IF EXISTS "Users can view portfolio positions for their funds" ON portfolio_positions;
DROP POLICY IF EXISTS "Users can view trades for their funds" ON trade_log;
DROP POLICY IF EXISTS "Users can view cash balances for their funds" ON cash_balances;
DROP POLICY IF EXISTS "Users can view performance metrics for their funds" ON performance_metrics;

-- Create simple public read policies
CREATE POLICY "Allow authenticated users to view portfolio positions" ON portfolio_positions
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to view trades" ON trade_log
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to view cash balances" ON cash_balances
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to view performance metrics" ON performance_metrics
    FOR SELECT USING (true);

-- Re-enable RLS (but with permissive policies)
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ RLS simplified for single-user setup';
    RAISE NOTICE '📊 All authenticated users can now see all portfolio data';
    RAISE NOTICE '🔐 User/admin roles still work for fund assignment management';
END $$;
