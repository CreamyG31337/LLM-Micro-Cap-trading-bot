-- Fix: Make daily_pnl calculation more robust by finding last trading day
-- Instead of failing silently when yesterday doesn't exist,
-- find the most recent previous trading day within a reasonable lookback window

DROP VIEW IF EXISTS latest_positions CASCADE;

CREATE VIEW latest_positions AS
WITH 
-- Get the latest position for each ticker per fund
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
-- Get previous trading day for each ticker (for 1-day P&L)
-- IMPROVED: Looks for most recent date < today, even if it's from several days ago
-- This handles weekends, holidays, and gaps in trading
yesterday_positions AS (
    SELECT 
        pp.fund,
        pp.ticker,
        pp.price as yesterday_price,
        pp.date as yesterday_date,
        ROW_NUMBER() OVER (
            PARTITION BY pp.fund, pp.ticker 
            ORDER BY pp.date DESC  -- Get the MOST RECENT date before today
        ) as rn
    FROM portfolio_positions pp
    INNER JOIN latest_pos lp 
        ON pp.fund = lp.fund 
        AND pp.ticker = lp.ticker
    WHERE pp.date < lp.date  -- Any date before latest
      AND pp.shares > 0
      AND pp.date >= (lp.date - INTERVAL '14 days')  -- Look back max 14 days (handles long weekends/holidays)
),
-- Get 5-days-ago position for each ticker (for 5-day P&L)
-- IMPROVED: More flexible lookback window
five_day_positions AS (
    SELECT 
        pp.fund,
        pp.ticker,
        pp.price as five_day_price,
        pp.date as five_day_date,
        ROW_NUMBER() OVER (
            PARTITION BY pp.fund, pp.ticker 
            ORDER BY ABS(EXTRACT(EPOCH FROM (pp.date - (lp.date - INTERVAL '5 days'))))  -- Closest to 5 days ago
        ) as rn
    FROM portfolio_positions pp
    INNER JOIN latest_pos lp 
        ON pp.fund = lp.fund 
        AND pp.ticker = lp.ticker
    WHERE pp.date < lp.date
      AND pp.shares > 0
      AND pp.date >= (lp.date - INTERVAL '10 days')  -- Look within 10 day window
      AND pp.date <= (lp.date - INTERVAL '3 days')   -- But at least 3 days ago
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
    
    -- 1-Day P&L calculations
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
    
    -- 5-Day P&L calculations
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
    
    -- Calculate how many days of data we actually have for the 5-day period
    CASE 
        WHEN fp.five_day_date IS NOT NULL THEN
            EXTRACT(DAY FROM (lp.date - fp.five_day_date))
        ELSE NULL
    END as five_day_period_days
    
FROM latest_pos lp
LEFT JOIN yesterday_positions yp 
    ON lp.fund = yp.fund 
    AND lp.ticker = yp.ticker 
    AND yp.rn = 1  -- Get the most recent previous day
LEFT JOIN five_day_positions fp 
    ON lp.fund = fp.fund 
    AND lp.ticker = fp.ticker 
    AND fp.rn = 1  -- Get the closest to 5 days ago
ORDER BY lp.fund, lp.market_value DESC;

-- Restore permissions
GRANT SELECT ON latest_positions TO authenticated;
GRANT SELECT ON latest_positions TO service_role;

-- Update comment
COMMENT ON VIEW latest_positions IS 'Latest position for each ticker with pre-calculated market_value, P&L, and historical 1-day/5-day P&L. Uses flexible lookback to handle weekends/holidays (up to 14 days for daily P&L).';
