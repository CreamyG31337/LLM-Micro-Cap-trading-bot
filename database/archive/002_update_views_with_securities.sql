-- Migration: Update Views to JOIN with Securities
-- Description: Modify latest_positions view to get company/sector/industry from securities table
-- Date: 2025-12-13

-- Drop existing view
DROP VIEW IF EXISTS latest_positions;

-- Recreate view with JOIN to securities table
-- Note: This view adds calculated columns not in base table
CREATE VIEW latest_positions AS
WITH latest_dates AS (
    SELECT fund, MAX(date) as max_date
    FROM portfolio_positions
    GROUP BY fund
),
latest_rows AS (
    SELECT 
        p.*,
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
    company_name as company,
    sector,
    industry,
    shares,
    price as current_price,
    cost_basis,
    total_value as market_value,
    pnl as unrealized_pnl,
    CASE 
        WHEN cost_basis > 0 THEN (pnl / cost_basis * 100)
        ELSE 0 
    END as return_pct,
    currency,
    date,
    -- Placeholder columns for compatibility (to be calculated elsewhere)
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

-- Add comment
COMMENT ON VIEW latest_positions IS 'Latest position for each ticker in each fund, with company/sector/industry from securities table';
