-- =====================================================
-- Migration: Clean Trade Log & Portfolio Positions + Add FK Constraints
-- =====================================================
-- This migration:
-- 1. Creates a funds table (if not exists)
-- 2. Populates it with valid fund names
-- 3. Deletes all data from trade_log and portfolio_positions
-- 4. Adds foreign key constraints on fund column for both tables
-- 
-- After running this SQL:
-- 1. Run reload_trade_log.py to repopulate trade_log from CSV
-- 2. Run rebuild_portfolio_from_scratch.py to rebuild portfolio_positions
-- =====================================================

-- Step 1: Create funds table if it doesn't exist
CREATE TABLE IF NOT EXISTS funds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    currency VARCHAR(10) NOT NULL DEFAULT 'CAD',
    fund_type VARCHAR(50) NOT NULL DEFAULT 'investment',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 2: Insert valid fund names
INSERT INTO funds (name, description, fund_type) VALUES
    ('Project Chimera', 'Main investment fund', 'investment'),
    ('RRSP Lance Webull', 'Retirement savings account', 'retirement'),
    ('TFSA', 'Tax-free savings account', 'tfsa'),
    ('Test Fund', 'Test/development fund', 'test')
ON CONFLICT (name) DO NOTHING;

-- Step 3: View current funds
SELECT * FROM funds ORDER BY name;

-- =====================================================
-- TRADE_LOG CLEANUP
-- =====================================================

-- Step 4a: Check what garbage fund values exist before deletion
SELECT DISTINCT fund, COUNT(*) as count 
FROM trade_log 
GROUP BY fund 
ORDER BY count DESC;

-- Step 4b: DELETE ALL data from trade_log (will be reloaded from CSV)
-- !!! CSV FILES ARE THE SOURCE OF TRUTH !!!
DELETE FROM trade_log;

-- Step 4c: Drop existing constraint if any
ALTER TABLE trade_log DROP CONSTRAINT IF EXISTS fk_trade_log_fund;

-- Step 4d: Add foreign key constraint
ALTER TABLE trade_log 
ADD CONSTRAINT fk_trade_log_fund 
FOREIGN KEY (fund) REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT;

-- =====================================================
-- PORTFOLIO_POSITIONS CLEANUP
-- =====================================================

-- Step 5a: Check what garbage fund values exist before deletion
SELECT DISTINCT fund, COUNT(*) as count 
FROM portfolio_positions 
GROUP BY fund 
ORDER BY count DESC;

-- Step 5b: DELETE ALL data from portfolio_positions
-- This will be rebuilt from trade logs using rebuild_portfolio_from_scratch.py
DELETE FROM portfolio_positions;

-- Step 5c: Drop existing constraint if any
ALTER TABLE portfolio_positions DROP CONSTRAINT IF EXISTS fk_portfolio_positions_fund;

-- Step 5d: Add foreign key constraint
ALTER TABLE portfolio_positions 
ADD CONSTRAINT fk_portfolio_positions_fund 
FOREIGN KEY (fund) REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT;

-- =====================================================
-- FUND_THESIS CLEANUP
-- =====================================================

-- Step 5e: Check fund values in fund_thesis
SELECT DISTINCT fund, COUNT(*) as count 
FROM fund_thesis 
GROUP BY fund 
ORDER BY count DESC;

-- Step 5f: Delete invalid fund_thesis entries (keep valid ones)
DELETE FROM fund_thesis WHERE fund NOT IN (SELECT name FROM funds);

-- Step 5g: Add FK constraint to fund_thesis
ALTER TABLE fund_thesis DROP CONSTRAINT IF EXISTS fk_fund_thesis_fund;
ALTER TABLE fund_thesis 
ADD CONSTRAINT fk_fund_thesis_fund 
FOREIGN KEY (fund) REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT;

-- =====================================================
-- PERFORMANCE_METRICS CLEANUP
-- =====================================================

-- Step 5h: Check fund values in performance_metrics
SELECT DISTINCT fund, COUNT(*) as count 
FROM performance_metrics 
GROUP BY fund 
ORDER BY count DESC;

-- Step 5i: Delete invalid performance_metrics entries (keep valid ones)
DELETE FROM performance_metrics WHERE fund NOT IN (SELECT name FROM funds);

-- Step 5j: Add FK constraint to performance_metrics
ALTER TABLE performance_metrics DROP CONSTRAINT IF EXISTS fk_performance_metrics_fund;
ALTER TABLE performance_metrics 
ADD CONSTRAINT fk_performance_metrics_fund 
FOREIGN KEY (fund) REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT;

-- =====================================================
-- FUTURE: USER_PROFILES <-> FUND_CONTRIBUTIONS RELATIONSHIP
-- =====================================================
-- When RLS is implemented, the intended access pattern is:
--   user_profiles.email -> fund_contributions.email (implicit link)
--   fund_contributions.fund -> funds.name (FK)
--   Users should only see:
--     - Funds they have contributed to
--     - Their own contribution amount and name
--     - Not other contributors' private info
--
-- For now, just adding fund FK to fund_contributions if it exists:

-- Step 5k: Check if fund_contributions exists and add FK
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'fund_contributions') THEN
        -- Check fund values
        RAISE NOTICE 'fund_contributions table exists - checking fund values';
        
        -- Add FK constraint
        EXECUTE 'ALTER TABLE fund_contributions DROP CONSTRAINT IF EXISTS fk_fund_contributions_fund';
        EXECUTE 'ALTER TABLE fund_contributions ADD CONSTRAINT fk_fund_contributions_fund FOREIGN KEY (fund) REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT';
        
        RAISE NOTICE 'Added FK constraint to fund_contributions';
    ELSE
        RAISE NOTICE 'fund_contributions table does not exist - skipping';
    END IF;
END $$;


-- =====================================================
-- VERIFICATION - Fund Constraints
-- =====================================================

-- Step 6: Verify fund constraints were added
SELECT 
    tc.table_name,
    tc.constraint_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (tc.table_name = 'trade_log' OR tc.table_name = 'portfolio_positions');

-- =====================================================
-- PHASE 2: TICKER FK CONSTRAINTS
-- =====================================================
-- RUN THIS SECTION AFTER RELOADING DATA FROM CSVs
-- This adds ticker -> securities.ticker FK to ensure data integrity

-- Step 7a: DIAGNOSTIC - Find tickers in trade_log NOT in securities table
-- These need to be added to securities before FK can be applied
SELECT DISTINCT t.ticker as missing_ticker, COUNT(*) as trade_count
FROM trade_log t
LEFT JOIN securities s ON t.ticker = s.ticker
WHERE s.ticker IS NULL
GROUP BY t.ticker
ORDER BY trade_count DESC;

-- Step 7b: DIAGNOSTIC - Find tickers in portfolio_positions NOT in securities table
SELECT DISTINCT p.ticker as missing_ticker, COUNT(*) as position_count
FROM portfolio_positions p
LEFT JOIN securities s ON p.ticker = s.ticker
WHERE s.ticker IS NULL
GROUP BY p.ticker
ORDER BY position_count DESC;

-- Step 7c: DIAGNOSTIC - Check for duplicate tickers in securities
SELECT ticker, COUNT(*) as count
FROM securities
GROUP BY ticker
HAVING COUNT(*) > 1;

-- Step 7d: DIAGNOSTIC - Check for case variations or similar tickers
SELECT ticker
FROM securities
WHERE ticker LIKE '%.TO' OR ticker LIKE '%.V'
ORDER BY ticker;

-- Step 7e: DIAGNOSTIC - All unique tickers across both tables
SELECT 'trade_log' as source, ticker, COUNT(*) as count
FROM trade_log
GROUP BY ticker
UNION ALL
SELECT 'portfolio_positions', ticker, COUNT(*)
FROM portfolio_positions
GROUP BY ticker
ORDER BY ticker, source;

-- =====================================================
-- Step 8: ADD TICKER FK CONSTRAINTS (ONLY RUN IF DIAGNOSTICS PASS)
-- =====================================================

-- Drop existing constraints if any
ALTER TABLE trade_log DROP CONSTRAINT IF EXISTS fk_trade_log_ticker;
ALTER TABLE portfolio_positions DROP CONSTRAINT IF EXISTS fk_portfolio_positions_ticker;

-- Add ticker FK to trade_log
ALTER TABLE trade_log 
ADD CONSTRAINT fk_trade_log_ticker 
FOREIGN KEY (ticker) REFERENCES securities(ticker) ON UPDATE CASCADE ON DELETE RESTRICT;

-- Add ticker FK to portfolio_positions  
ALTER TABLE portfolio_positions 
ADD CONSTRAINT fk_portfolio_positions_ticker 
FOREIGN KEY (ticker) REFERENCES securities(ticker) ON UPDATE CASCADE ON DELETE RESTRICT;

-- =====================================================
-- FINAL VERIFICATION
-- =====================================================

-- Step 9: Verify ALL constraints
SELECT 
    tc.table_name,
    tc.constraint_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (tc.table_name = 'trade_log' OR tc.table_name = 'portfolio_positions')
ORDER BY tc.table_name, tc.constraint_name;

-- Step 10: Final row counts
SELECT 'trade_log' as table_name, COUNT(*) as row_count FROM trade_log
UNION ALL
SELECT 'portfolio_positions', COUNT(*) FROM portfolio_positions
UNION ALL
SELECT 'securities', COUNT(*) FROM securities
UNION ALL
SELECT 'funds', COUNT(*) FROM funds;
