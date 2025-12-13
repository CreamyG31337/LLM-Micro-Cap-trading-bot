-- Migration: Remove company column and fix dependent views
-- Description: Updates views to remove dependency on 'company' column, then drops the column.
-- This handles the dependency error: "cannot drop column company ... because other objects depend on it"

-- 1. Drop dependent views first
DROP VIEW IF EXISTS current_positions;
DROP VIEW IF EXISTS latest_positions;

-- 2. Recreate latest_positions view WITHOUT 'company' column from portfolio_positions
--    Using explicit column selection to avoid dependency on dropped column
CREATE OR REPLACE VIEW latest_positions AS
WITH latest_dates AS (
    SELECT fund, MAX(date) as max_date
    FROM portfolio_positions
    GROUP BY fund
),
latest_rows AS (
    SELECT 
        p.id,
        p.ticker,
        p.shares,
        p.price,
        p.cost_basis,
        p.pnl,
        p.currency,
        p.fund,
        p.date,
        s.company_name,
        s.sector,
        s.industry
    FROM portfolio_positions p
    INNER JOIN latest_dates ld ON p.fund = ld.fund AND p.date = ld.max_date
    LEFT JOIN securities s ON p.ticker = s.ticker
)
SELECT 
    fund,
    ticker,
    company_name as company, -- From securities table
    sector,
    industry,
    shares,
    price as current_price,
    cost_basis,
    (shares * price) as market_value, -- Calculated explicit
    pnl as unrealized_pnl,
    CASE 
        WHEN cost_basis > 0 THEN (pnl / cost_basis * 100)
        ELSE 0 
    END as return_pct,
    currency,
    date,
    -- Compatibility columns
    NULL::NUMERIC as yesterday_price,
    NULL::DATE as yesterday_date,
    0::NUMERIC as daily_pnl,
    0::NUMERIC as daily_pnl_pct,
    NULL::NUMERIC as five_day_price,
    NULL::DATE as five_day_date,
    0::NUMERIC as five_day_pnl,
    0::NUMERIC as five_day_pnl_pct,
    0::INTEGER as five_day_period_days
FROM latest_rows;

COMMENT ON VIEW latest_positions IS 'Latest position for each ticker in each fund, with company/sector/industry from securities table';

-- 3. Restore current_positions as alias to latest_positions (for backward compatibility)
CREATE VIEW current_positions AS SELECT * FROM latest_positions;

-- 4. NOW safe to drop the column
ALTER TABLE portfolio_positions DROP COLUMN IF EXISTS company;
