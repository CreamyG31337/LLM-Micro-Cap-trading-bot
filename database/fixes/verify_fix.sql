-- =====================================================
-- Verification: Test RLS Visibility for User
-- =====================================================
-- Run this in Supabase SQL Editor.
-- Returns a table of results instead of messages.

DO $$
DECLARE
    target_email TEXT := 'lance.colton@gmail.com';
    target_user_id UUID;
    
    -- Variables to hold counts
    contrib_count INTEGER;
    pos_count INTEGER;
    cash_count INTEGER;
    trade_count INTEGER;
    
    -- Status messages
    contrib_status TEXT;
    pos_status TEXT;
    
BEGIN
    -- 1. Get User ID
    SELECT id INTO target_user_id FROM auth.users WHERE email = target_email;
    
    -- 2. Simulate User Session
    IF target_user_id IS NOT NULL THEN
        PERFORM set_config('role', 'authenticated', true);
        PERFORM set_config('request.jwt.claim.sub', target_user_id::text, true);
        
        -- 3. Run Checks AS THE USER
        SELECT count(*) INTO contrib_count FROM fund_contributions;
        SELECT count(*) INTO pos_count FROM portfolio_positions;
        SELECT count(*) INTO cash_count FROM cash_balances;
        SELECT count(*) INTO trade_count FROM trade_log;
        
        -- 4. Create a temporary table to store results so we can select from it
        CREATE TEMP TABLE verification_results (
            check_name TEXT,
            count_visible INTEGER,
            status TEXT
        ) ON COMMIT DROP;
        
        -- Eval Status
        IF contrib_count > 0 THEN contrib_status := 'PASS'; ELSE contrib_status := 'FAIL - DF_015 Required'; END IF;
        IF pos_count > 0 THEN pos_status := 'PASS'; ELSE pos_status := 'FAIL - DF_016 Required'; END IF;

        -- Insert Results
        INSERT INTO verification_results VALUES 
            ('Fund Contributions', contrib_count, contrib_status),
            ('Portfolio Positions', pos_count, pos_status),
            ('Cash Balances', cash_count, 'Info: ' || cash_count || ' visible'),
            ('Trade Log', trade_count, 'Info: ' || trade_count || ' visible');
            
    END IF;
END $$;

-- 5. Select the results (This is what will show in Supabase UI)
SELECT * FROM verification_results;
