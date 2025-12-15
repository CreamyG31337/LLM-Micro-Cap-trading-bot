-- =====================================================
-- DF_006: ENABLE RLS SECURITY FIX
-- =====================================================
-- Fixes all Supabase security linter errors:
-- 1. policy_exists_rls_disabled - Enable RLS on tables that have policies
-- 2. rls_disabled_in_public - Add RLS to public tables
-- 3. security_definer_view - Recreate views without SECURITY DEFINER
-- 4. function_search_path_mutable - Add search_path to all functions
-- =====================================================

-- =====================================================
-- PART 1: ENABLE RLS ON ALL TABLES
-- =====================================================

-- Tables that have policies but RLS not enabled
ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;

-- Tables completely missing RLS
ALTER TABLE securities ENABLE ROW LEVEL SECURITY;
ALTER TABLE funds ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- PART 2: ADD RLS POLICIES FOR NEW TABLES
-- =====================================================

-- Securities table: allow public read (ticker info is not sensitive)
DROP POLICY IF EXISTS "Allow read access to securities" ON securities;
CREATE POLICY "Allow read access to securities" ON securities
    FOR SELECT USING (true);

-- Allow service role to manage securities (for data updates)
DROP POLICY IF EXISTS "Service role can manage securities" ON securities;
CREATE POLICY "Service role can manage securities" ON securities
    FOR ALL USING (auth.role() = 'service_role');

-- Funds table: users can see funds they're assigned to, admins see all
DROP POLICY IF EXISTS "Users can view assigned funds" ON funds;
CREATE POLICY "Users can view assigned funds" ON funds
    FOR SELECT USING (
        name IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- Allow service role to manage funds
DROP POLICY IF EXISTS "Service role can manage funds" ON funds;
CREATE POLICY "Service role can manage funds" ON funds
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- PART 2B: ADD ADMIN POLICIES FOR PORTFOLIO TABLES
-- =====================================================

-- Portfolio positions: user-fund access + admin access + service role
DROP POLICY IF EXISTS "Users can view portfolio positions for their funds" ON portfolio_positions;
DROP POLICY IF EXISTS "Admins can view all portfolio positions" ON portfolio_positions;
DROP POLICY IF EXISTS "Service role full access to portfolio_positions" ON portfolio_positions;

CREATE POLICY "Users can view portfolio positions for their funds" ON portfolio_positions
    FOR SELECT USING (
        fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    );

CREATE POLICY "Admins can view all portfolio positions" ON portfolio_positions
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "Service role full access to portfolio_positions" ON portfolio_positions
    FOR ALL USING (auth.role() = 'service_role');

-- Trade log: user-fund access + admin access + service role
DROP POLICY IF EXISTS "Users can view trades for their funds" ON trade_log;
DROP POLICY IF EXISTS "Admins can view all trades" ON trade_log;
DROP POLICY IF EXISTS "Service role full access to trade_log" ON trade_log;

CREATE POLICY "Users can view trades for their funds" ON trade_log
    FOR SELECT USING (
        fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    );

CREATE POLICY "Admins can view all trades" ON trade_log
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "Service role full access to trade_log" ON trade_log
    FOR ALL USING (auth.role() = 'service_role');

-- Cash balances: user-fund access + admin access + service role
DROP POLICY IF EXISTS "Users can view cash balances for their funds" ON cash_balances;
DROP POLICY IF EXISTS "Admins can view all cash balances" ON cash_balances;
DROP POLICY IF EXISTS "Service role full access to cash_balances" ON cash_balances;

CREATE POLICY "Users can view cash balances for their funds" ON cash_balances
    FOR SELECT USING (
        fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    );

CREATE POLICY "Admins can view all cash balances" ON cash_balances
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "Service role full access to cash_balances" ON cash_balances
    FOR ALL USING (auth.role() = 'service_role');

-- Performance metrics: user-fund access + admin access + service role
DROP POLICY IF EXISTS "Users can view performance metrics for their funds" ON performance_metrics;
DROP POLICY IF EXISTS "Admins can view all performance metrics" ON performance_metrics;
DROP POLICY IF EXISTS "Service role full access to performance_metrics" ON performance_metrics;

CREATE POLICY "Users can view performance metrics for their funds" ON performance_metrics
    FOR SELECT USING (
        fund IN (SELECT fund_name FROM user_funds WHERE user_id = auth.uid())
    );

CREATE POLICY "Admins can view all performance metrics" ON performance_metrics
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "Service role full access to performance_metrics" ON performance_metrics
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- PART 3: FIX SECURITY DEFINER VIEWS
-- =====================================================
-- Recreate views without SECURITY DEFINER (they use SECURITY INVOKER by default)

-- 3a. Recreate latest_positions view
DROP VIEW IF EXISTS latest_positions CASCADE;

CREATE VIEW latest_positions AS
WITH 
ranked_positions AS (
    SELECT 
        fund,
        ticker,
        shares,
        price as current_price,
        cost_basis,
        currency,
        date,
        (shares * price) as market_value,
        (shares * price - cost_basis) as unrealized_pnl,
        ROW_NUMBER() OVER (
            PARTITION BY fund, ticker 
            ORDER BY date DESC
        ) as rn
    FROM portfolio_positions
    WHERE shares > 0
),
latest_pos AS (
    SELECT * FROM ranked_positions WHERE rn = 1
),
yesterday_positions AS (
    SELECT 
        pp.fund,
        pp.ticker,
        pp.price as yesterday_price,
        pp.date as yesterday_date,
        ROW_NUMBER() OVER (
            PARTITION BY pp.fund, pp.ticker 
            ORDER BY pp.date DESC
        ) as rn
    FROM portfolio_positions pp
    INNER JOIN latest_pos lp 
        ON pp.fund = lp.fund 
        AND pp.ticker = lp.ticker
    WHERE pp.date < lp.date
      AND pp.shares > 0
),
five_day_positions AS (
    SELECT 
        pp.fund,
        pp.ticker,
        pp.price as five_day_price,
        pp.date as five_day_date,
        ROW_NUMBER() OVER (
            PARTITION BY pp.fund, pp.ticker 
            ORDER BY pp.date DESC
        ) as rn
    FROM portfolio_positions pp
    INNER JOIN latest_pos lp 
        ON pp.fund = lp.fund 
        AND pp.ticker = lp.ticker
    WHERE pp.date < (lp.date - INTERVAL '4 days')
      AND pp.shares > 0
)
SELECT 
    lp.fund,
    lp.ticker,
    lp.shares,
    lp.current_price,
    lp.cost_basis,
    lp.market_value,
    lp.unrealized_pnl,
    CASE 
        WHEN lp.cost_basis > 0 THEN 
            (lp.unrealized_pnl / lp.cost_basis) * 100
        ELSE 0 
    END as return_pct,
    lp.currency,
    lp.date,
    yp.yesterday_price,
    yp.yesterday_date,
    CASE 
        WHEN yp.yesterday_price IS NOT NULL THEN
            (lp.current_price - yp.yesterday_price) * lp.shares
        ELSE NULL
    END as daily_pnl,
    CASE 
        WHEN yp.yesterday_price IS NOT NULL AND yp.yesterday_price > 0 THEN
            ((lp.current_price - yp.yesterday_price) / yp.yesterday_price) * 100
        ELSE NULL
    END as daily_pnl_pct,
    fp.five_day_price,
    fp.five_day_date,
    CASE 
        WHEN fp.five_day_price IS NOT NULL THEN
            (lp.current_price - fp.five_day_price) * lp.shares
        ELSE NULL
    END as five_day_pnl,
    CASE 
        WHEN fp.five_day_price IS NOT NULL AND fp.five_day_price > 0 THEN
            ((lp.current_price - fp.five_day_price) / fp.five_day_price) * 100
        ELSE NULL
    END as five_day_pnl_pct,
    CASE 
        WHEN fp.five_day_date IS NOT NULL THEN
            EXTRACT(DAY FROM (lp.date - fp.five_day_date))
        ELSE NULL
    END as five_day_period_days
FROM latest_pos lp
LEFT JOIN yesterday_positions yp 
    ON lp.fund = yp.fund 
    AND lp.ticker = yp.ticker 
    AND yp.rn = 1
LEFT JOIN five_day_positions fp 
    ON lp.fund = fp.fund 
    AND lp.ticker = fp.ticker 
    AND fp.rn = 1
ORDER BY lp.fund, lp.market_value DESC;

-- 3b. Recreate contributor_ownership view
DROP VIEW IF EXISTS contributor_ownership CASCADE;

CREATE VIEW contributor_ownership AS
SELECT 
    fund,
    contributor,
    email,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_contribution,
    COUNT(*) as transaction_count,
    MIN(timestamp) as first_contribution,
    MAX(timestamp) as last_transaction
FROM fund_contributions
GROUP BY fund, contributor, email
HAVING SUM(CASE 
    WHEN contribution_type = 'CONTRIBUTION' THEN amount 
    WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
    ELSE 0 
END) > 0
ORDER BY fund, net_contribution DESC;

-- 3c. Recreate daily_portfolio_snapshots view
DROP VIEW IF EXISTS daily_portfolio_snapshots CASCADE;

CREATE VIEW daily_portfolio_snapshots AS
WITH daily_positions AS (
    SELECT 
        fund,
        ticker,
        DATE(date) as snapshot_date,
        shares,
        price,
        cost_basis,
        (shares * price) as market_value,
        (shares * price - cost_basis) as unrealized_pnl,
        date as full_timestamp
    FROM portfolio_positions
    WHERE shares > 0
),
ranked_daily AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY fund, ticker, snapshot_date 
            ORDER BY full_timestamp DESC
        ) as rn
    FROM daily_positions
),
latest_daily AS (
    SELECT *
    FROM ranked_daily
    WHERE rn = 1
)
SELECT 
    fund,
    snapshot_date,
    COUNT(DISTINCT ticker) as position_count,
    SUM(market_value) as total_market_value,
    SUM(cost_basis) as total_cost_basis,
    SUM(unrealized_pnl) as total_unrealized_pnl,
    CASE 
        WHEN SUM(cost_basis) > 0 THEN 
            (SUM(unrealized_pnl) / SUM(cost_basis)) * 100
        ELSE 0 
    END as total_return_pct
FROM latest_daily
GROUP BY fund, snapshot_date
ORDER BY fund, snapshot_date DESC;

-- 3d. Recreate fund_contributor_summary view
DROP VIEW IF EXISTS fund_contributor_summary CASCADE;

CREATE VIEW fund_contributor_summary AS
SELECT 
    fund,
    COUNT(DISTINCT contributor) as total_contributors,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_capital,
    MIN(timestamp) as fund_inception,
    MAX(timestamp) as last_activity
FROM fund_contributions
GROUP BY fund;

-- Grant permissions on recreated views
GRANT SELECT ON latest_positions TO authenticated;
GRANT SELECT ON latest_positions TO service_role;
GRANT SELECT ON contributor_ownership TO authenticated;
GRANT SELECT ON contributor_ownership TO service_role;
GRANT SELECT ON daily_portfolio_snapshots TO authenticated;
GRANT SELECT ON daily_portfolio_snapshots TO service_role;
GRANT SELECT ON fund_contributor_summary TO authenticated;
GRANT SELECT ON fund_contributor_summary TO service_role;

-- =====================================================
-- PART 4: FIX FUNCTION SEARCH_PATH
-- =====================================================
-- Recreate all functions with SET search_path = public

-- 4a. is_admin
CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4b. normalize_email
CREATE OR REPLACE FUNCTION normalize_email(email TEXT)
RETURNS TEXT AS $$
DECLARE
    normalized TEXT;
    local_part TEXT;
    domain_part TEXT;
BEGIN
    normalized := LOWER(TRIM(COALESCE(email, '')));
    
    IF normalized = '' OR POSITION('@' IN normalized) = 0 THEN
        RETURN normalized;
    END IF;
    
    local_part := SPLIT_PART(normalized, '@', 1);
    domain_part := SPLIT_PART(normalized, '@', 2);
    
    IF domain_part IN ('gmail.com', 'googlemail.com') THEN
        local_part := REPLACE(local_part, '.', '');
    END IF;
    
    RETURN local_part || '@' || domain_part;
END;
$$ LANGUAGE plpgsql IMMUTABLE
SET search_path = public;

-- 4c. get_user_funds
CREATE OR REPLACE FUNCTION get_user_funds(user_uuid UUID)
RETURNS TABLE(fund_name VARCHAR(50)) AS $$
BEGIN
    RETURN QUERY
    SELECT uf.fund_name
    FROM user_funds uf
    WHERE uf.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4d. user_has_fund_access
CREATE OR REPLACE FUNCTION user_has_fund_access(user_uuid UUID, fund_name VARCHAR(50))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_funds 
        WHERE user_id = user_uuid AND user_funds.fund_name = user_has_fund_access.fund_name
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4e. get_user_accessible_funds
CREATE OR REPLACE FUNCTION get_user_accessible_funds()
RETURNS TABLE(fund_name VARCHAR(50)) AS $$
BEGIN
    RETURN QUERY
    SELECT uf.fund_name
    FROM user_funds uf
    WHERE uf.user_id = auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4f. create_user_profile
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
DECLARE
    user_count INTEGER;
    user_role VARCHAR(50);
BEGIN
    SELECT COUNT(*) INTO user_count FROM user_profiles;
    
    IF user_count = 0 THEN
        user_role := 'admin';
    ELSE
        user_role := 'user';
    END IF;
    
    INSERT INTO user_profiles (user_id, email, full_name, role)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        user_role
    );
    
    INSERT INTO user_funds (user_id, fund_name)
    SELECT DISTINCT NEW.id, fc.fund
    FROM fund_contributions fc
    WHERE normalize_email(fc.email) = normalize_email(NEW.email)
    ON CONFLICT (user_id, fund_name) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4g. assign_fund_to_user
CREATE OR REPLACE FUNCTION assign_fund_to_user(user_email TEXT, fund_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
BEGIN
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
    
    INSERT INTO user_funds (user_id, fund_name)
    VALUES (target_user_id, fund_name)
    ON CONFLICT (user_id, fund_name) DO NOTHING;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4h. remove_fund_from_user
CREATE OR REPLACE FUNCTION remove_fund_from_user(user_email TEXT, fund_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
    rows_deleted INTEGER;
BEGIN
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
    
    DELETE FROM user_funds
    WHERE user_id = target_user_id AND user_funds.fund_name = remove_fund_from_user.fund_name;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN rows_deleted > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4i. delete_user_safe
CREATE OR REPLACE FUNCTION delete_user_safe(user_email TEXT)
RETURNS JSON AS $$
DECLARE
    target_user_id UUID;
    contributor_count INTEGER;
    result JSON;
BEGIN
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'User not found');
    END IF;
    
    SELECT COUNT(*) INTO contributor_count
    FROM fund_contributions
    WHERE normalize_email(fund_contributions.email) = normalize_email(user_email);
    
    IF contributor_count > 0 THEN
        RETURN json_build_object(
            'success', false, 
            'message', 'Cannot delete: User is a fund contributor with ' || contributor_count || ' contribution record(s). Remove their contributions first.',
            'is_contributor', true
        );
    END IF;
    
    DELETE FROM auth.users WHERE id = target_user_id;
    
    RETURN json_build_object('success', true, 'message', 'User deleted successfully');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4j. list_users_with_funds
CREATE OR REPLACE FUNCTION list_users_with_funds()
RETURNS TABLE(
    user_id UUID,
    email TEXT,
    full_name TEXT,
    funds TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        up.user_id,
        up.email::TEXT,
        up.full_name::TEXT,
        ARRAY_AGG(uf.fund_name)::TEXT[] as funds
    FROM user_profiles up
    LEFT JOIN user_funds uf ON up.user_id = uf.user_id
    GROUP BY up.user_id, up.email, up.full_name
    ORDER BY up.email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4k. list_unregistered_contributors
CREATE OR REPLACE FUNCTION list_unregistered_contributors()
RETURNS TABLE(
    contributor TEXT,
    email TEXT,
    funds TEXT[],
    total_contribution DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fc.contributor::TEXT,
        fc.email::TEXT,
        ARRAY_AGG(DISTINCT fc.fund)::TEXT[] as funds,
        SUM(CASE 
            WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
            WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
            ELSE 0 
        END) as total_contribution
    FROM fund_contributions fc
    WHERE fc.email IS NOT NULL
      AND fc.email != ''
      AND NOT EXISTS (
          SELECT 1 FROM auth.users au 
          WHERE normalize_email(au.email) = normalize_email(fc.email)
      )
    GROUP BY fc.contributor, fc.email
    HAVING SUM(CASE 
        WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
        WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
        ELSE 0 
    END) > 0
    ORDER BY fc.contributor;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4l. update_updated_at_column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

-- 4m. calculate_daily_performance
CREATE OR REPLACE FUNCTION calculate_daily_performance(target_date DATE, fund_name VARCHAR(50) DEFAULT NULL)
RETURNS TABLE (
    fund VARCHAR(50),
    total_value DECIMAL(10, 2),
    cost_basis DECIMAL(10, 2),
    unrealized_pnl DECIMAL(10, 2),
    performance_pct DECIMAL(5, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.fund,
        COALESCE(SUM(p.total_value), 0) as total_value,
        COALESCE(SUM(p.cost_basis), 0) as cost_basis,
        COALESCE(SUM(p.pnl), 0) as unrealized_pnl,
        CASE
            WHEN SUM(p.cost_basis) > 0 THEN (SUM(p.pnl) / SUM(p.cost_basis)) * 100
            ELSE 0
        END as performance_pct
    FROM portfolio_positions p
    WHERE p.date::date = target_date
      AND p.shares > 0
      AND (fund_name IS NULL OR p.fund = fund_name)
    GROUP BY p.fund;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

-- 4n. get_exchange_rate_for_date
CREATE OR REPLACE FUNCTION get_exchange_rate_for_date(
    target_date TIMESTAMP WITH TIME ZONE,
    from_curr VARCHAR(3) DEFAULT 'USD',
    to_curr VARCHAR(3) DEFAULT 'CAD'
)
RETURNS DECIMAL(10, 6) AS $$
DECLARE
    result_rate DECIMAL(10, 6);
BEGIN
    SELECT rate INTO result_rate
    FROM exchange_rates
    WHERE from_currency = from_curr
      AND to_currency = to_curr
      AND timestamp <= target_date
    ORDER BY timestamp DESC
    LIMIT 1;
    
    RETURN COALESCE(result_rate, 1.35);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4o. get_latest_exchange_rate
CREATE OR REPLACE FUNCTION get_latest_exchange_rate(
    from_curr VARCHAR(3) DEFAULT 'USD',
    to_curr VARCHAR(3) DEFAULT 'CAD'
)
RETURNS DECIMAL(10, 6) AS $$
DECLARE
    result_rate DECIMAL(10, 6);
BEGIN
    SELECT rate INTO result_rate
    FROM exchange_rates
    WHERE from_currency = from_curr
      AND to_currency = to_curr
    ORDER BY timestamp DESC
    LIMIT 1;
    
    RETURN COALESCE(result_rate, 1.35);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- 4p. get_fund_thesis
CREATE OR REPLACE FUNCTION get_fund_thesis(fund_name VARCHAR(50))
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'guiding_thesis', json_build_object(
            'title', ft.title,
            'overview', ft.overview,
            'pillars', COALESCE(
                (SELECT json_agg(
                    json_build_object(
                        'name', ftp.name,
                        'allocation', ftp.allocation,
                        'thesis', ftp.thesis
                    ) ORDER BY ftp.pillar_order
                )
                FROM fund_thesis_pillars ftp 
                WHERE ftp.thesis_id = ft.id), 
                '[]'::json
            )
        )
    ) INTO result
    FROM fund_thesis ft
    WHERE ft.fund = fund_name;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check RLS is enabled on all tables
SELECT 'RLS Status:' as check_type;
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('portfolio_positions', 'trade_log', 'cash_balances', 
                  'performance_metrics', 'securities', 'funds',
                  'fund_contributions', 'user_funds', 'user_profiles');

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ DF_006: RLS Security Fix Complete!';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Changes made:';
    RAISE NOTICE '   - Enabled RLS on 6 tables';
    RAISE NOTICE '   - Added policies for securities and funds tables';
    RAISE NOTICE '   - Recreated 4 views without SECURITY DEFINER';
    RAISE NOTICE '   - Added search_path to 16 functions';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 Next step: Re-run Supabase Database Linter to verify all errors are fixed';
END $$;
