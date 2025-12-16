-- =====================================================
-- Migration: Fix RLS Policy for Fund Data Tables
-- =====================================================
-- Fixes missing NAV calculation data by allowing contributors
-- to view portfolio positions, trades, and cash balances
-- for funds where they have a contribution.
-- =====================================================

-- 1. FIX PORTFOLIO POSITIONS
DROP POLICY IF EXISTS "Users can view portfolio positions for their funds" ON portfolio_positions;

CREATE POLICY "Users can view portfolio positions for their funds" 
ON portfolio_positions FOR SELECT 
USING (
    -- Assigned funds
    fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    OR
    -- Contributed funds (where user email matches contribution email)
    fund IN (
        SELECT fund FROM fund_contributions 
        WHERE normalize_email(email) = normalize_email((SELECT email FROM user_profiles WHERE user_id = auth.uid()))
    )
);

-- 2. FIX TRADE LOG
DROP POLICY IF EXISTS "Users can view trades for their funds" ON trade_log;

CREATE POLICY "Users can view trades for their funds" 
ON trade_log FOR SELECT 
USING (
    fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    OR
    fund IN (
        SELECT fund FROM fund_contributions 
        WHERE normalize_email(email) = normalize_email((SELECT email FROM user_profiles WHERE user_id = auth.uid()))
    )
);

-- 3. FIX CASH BALANCES
DROP POLICY IF EXISTS "Users can view cash balances for their funds" ON cash_balances;

CREATE POLICY "Users can view cash balances for their funds" 
ON cash_balances FOR SELECT 
USING (
    fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    OR
    fund IN (
        SELECT fund FROM fund_contributions 
        WHERE normalize_email(email) = normalize_email((SELECT email FROM user_profiles WHERE user_id = auth.uid()))
    )
);

-- 4. FIX PERFORMANCE METRICS
DROP POLICY IF EXISTS "Users can view performance metrics for their funds" ON performance_metrics;

CREATE POLICY "Users can view performance metrics for their funds" 
ON performance_metrics FOR SELECT 
USING (
    fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    OR
    fund IN (
        SELECT fund FROM fund_contributions 
        WHERE normalize_email(email) = normalize_email((SELECT email FROM user_profiles WHERE user_id = auth.uid()))
    )
);

-- Verify policies
SELECT tablename, policyname FROM pg_policies WHERE tablename IN ('portfolio_positions', 'trade_log', 'cash_balances', 'performance_metrics');
