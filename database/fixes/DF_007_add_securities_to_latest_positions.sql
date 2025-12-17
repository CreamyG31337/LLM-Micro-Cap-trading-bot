-- FIX: Add company, sector, industry columns to latest_positions view
-- Description: The DF_006 view removed the securities table join. This restores it.
-- Date: 2025-01-27

-- Drop and recreate latest_positions view with securities join
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
    s.company_name AS company,  -- From securities table
    s.sector,                    -- From securities table
    s.industry,                  -- From securities table
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
LEFT JOIN securities s ON lp.ticker = s.ticker  -- JOIN to get company, sector, industry
LEFT JOIN yesterday_positions yp 
    ON lp.fund = yp.fund 
    AND lp.ticker = yp.ticker 
    AND yp.rn = 1
LEFT JOIN five_day_positions fp 
    ON lp.fund = fp.fund 
    AND lp.ticker = fp.ticker 
    AND fp.rn = 1
ORDER BY lp.fund, lp.market_value DESC;

-- Restore permissions
GRANT SELECT ON latest_positions TO authenticated;
GRANT SELECT ON latest_positions TO service_role;

-- Add comment
COMMENT ON VIEW latest_positions IS 'Latest position for each ticker in each fund, with company/sector/industry from securities table';

