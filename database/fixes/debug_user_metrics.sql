-- =====================================================
-- Comprehensive Debug: Trace get_user_investment_metrics Logic
-- =====================================================
-- This script simulates the exact logic of get_user_investment_metrics
-- to identify which condition is causing it to return None

DO $$
DECLARE
    target_email TEXT := 'lance.colton@gmail.com';
    target_user_id UUID;
    target_fund TEXT := 'Project Chimera';
    
    -- Variables matching Python function
    contrib_count INTEGER;
    portfolio_value DECIMAL;
    cash_cad DECIMAL;
    cash_usd DECIMAL;
    fund_total_value DECIMAL;
    total_units DECIMAL := 0;
    user_contributor TEXT;
    user_units DECIMAL;
    user_net_contribution DECIMAL;
    
BEGIN
    CREATE TEMP TABLE debug_results (
        check_name TEXT,
        status TEXT,
        value TEXT,
        notes TEXT
    ) ON COMMIT DROP;
    
    -- Grant permissions so we can insert even after role switch
    GRANT ALL ON TABLE debug_results TO authenticated;
    GRANT ALL ON TABLE debug_results TO PUBLIC;

    -- 1. Get User ID
    SELECT id INTO target_user_id FROM auth.users WHERE email = target_email;
    INSERT INTO debug_results VALUES ('User ID', 
        CASE WHEN target_user_id IS NOT NULL THEN 'PASS' ELSE 'FAIL' END,
        target_user_id::TEXT,
        'User must exist in auth.users');
    
    IF target_user_id IS NULL THEN
        INSERT INTO debug_results VALUES ('FATAL', 'FAIL', NULL, 'User not found - cannot continue');
        RETURN;
    END IF;

    -- Simulate user session (move this AFTER table creation)
    PERFORM set_config('role', 'authenticated', true);
    PERFORM set_config('request.jwt.claim.sub', target_user_id::TEXT, true);

    -- 2. Check fund_contributions (Line 1042-1043 in Python)
    SELECT count(*) INTO contrib_count FROM fund_contributions WHERE fund = target_fund;
    INSERT INTO debug_results VALUES ('Fund Contributions Count', 
        CASE WHEN contrib_count > 0 THEN 'PASS' ELSE 'FAIL - Line 1044 returns None' END,
        contrib_count::TEXT,
        'Python checks: if not all_contributions: return None');

    -- 3. Check portfolio_value from latest_positions (streamlit_app.py line 838-846)
    SELECT COALESCE(SUM(market_value), 0) INTO portfolio_value 
    FROM latest_positions 
    WHERE fund = target_fund;
    
    INSERT INTO debug_results VALUES ('Portfolio Value (no cash)', 
        CASE WHEN portfolio_value > 0 THEN 'PASS' ELSE 'WARNING' END,
        portfolio_value::TEXT,
        'Calculated from latest_positions');

    -- 4. Check cash balances
    SELECT COALESCE(SUM(amount), 0) INTO cash_cad 
    FROM cash_balances 
    WHERE fund = target_fund AND currency = 'CAD';
    
    SELECT COALESCE(SUM(amount), 0) INTO cash_usd 
    FROM cash_balances 
    WHERE fund = target_fund AND currency = 'USD';
    
    INSERT INTO debug_results VALUES ('Cash CAD', 'INFO', cash_cad::TEXT, NULL);
    INSERT INTO debug_results VALUES ('Cash USD', 'INFO', cash_usd::TEXT, 'Will be converted to CAD');

    -- 5. Calculate fund_total_value (Line 1058-1061 in Python)
    -- Assume USD to CAD rate of 1.42
    fund_total_value := portfolio_value + cash_cad + (cash_usd * 1.42);
    
    INSERT INTO debug_results VALUES ('Fund Total Value', 
        CASE WHEN fund_total_value > 0 THEN 'PASS' ELSE 'FAIL - Line 1062 returns None' END,
        fund_total_value::TEXT,
        'Python checks: if fund_total_value <= 0: return None');

    -- 6. Calculate total_units (simplified version of Lines 1140-1219)
    -- This is a complex NAV calculation, but we can check if there are ANY contributions
    WITH contrib_calc AS (
        SELECT 
            contributor,
            email,
            SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE -amount END) as net
        FROM fund_contributions
        WHERE fund = target_fund
        GROUP BY contributor, email
    )
    SELECT SUM(net) INTO total_units FROM contrib_calc WHERE net > 0;
    
    INSERT INTO debug_results VALUES ('Total Units (simplified)', 
        CASE WHEN total_units > 0 THEN 'PASS' ELSE 'FAIL - Line 1222 returns None' END,
        COALESCE(total_units::TEXT, '0'),
        'Python checks: if total_units <= 0: return None');

    -- 7. Find user contributor by email match (Lines 1226-1234)
    SELECT contributor INTO user_contributor
    FROM fund_contributions
    WHERE fund = target_fund 
      AND LOWER(email) = LOWER(target_email)
    LIMIT 1;
    
    INSERT INTO debug_results VALUES ('User Contributor Match', 
        CASE WHEN user_contributor IS NOT NULL THEN 'PASS' ELSE 'FAIL - Line 1237 returns None' END,
        COALESCE(user_contributor, 'NULL'),
        'Python checks: if contrib_email.lower() == user_email.lower()');
    
    -- 8. Calculate user net contribution (Line 1239-1243)
    IF user_contributor IS NOT NULL THEN
        SELECT SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE -amount END)
        INTO user_net_contribution
        FROM fund_contributions
        WHERE fund = target_fund 
          AND contributor = user_contributor;
        
        INSERT INTO debug_results VALUES ('User Net Contribution', 
            CASE WHEN user_net_contribution > 0 THEN 'PASS' ELSE 'FAIL - Line 1244 returns None' END,
            COALESCE(user_net_contribution::TEXT, '0'),
            'Python checks: if user_net_contribution <= 0: return None');
    ELSE
        INSERT INTO debug_results VALUES ('User Net Contribution', 'SKIP', NULL, 
            'Skipped because user_contributor is NULL');
    END IF;

    -- 9. Show all emails in fund_contributions for comparison
    INSERT INTO debug_results 
    SELECT 'Available Emails in DB', 'INFO', email, contributor
    FROM fund_contributions 
    WHERE fund = target_fund
    GROUP BY email, contributor
    LIMIT 10;

END $$;

-- Display results
SELECT * FROM debug_results ORDER BY 
    CASE 
        WHEN check_name = 'FATAL' THEN 0
        WHEN status LIKE 'FAIL%' THEN 1
        WHEN status = 'WARNING' THEN 2
        WHEN status = 'PASS' THEN 3
        ELSE 4
    END,
    check_name;
