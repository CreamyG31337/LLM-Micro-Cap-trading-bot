-- =====================================================
-- OPTIMIZED PORTFOLIO VIEWS WITH HISTORICAL P&L
-- =====================================================
-- Pre-calculate market_value, P&L, and historical P&L in database for efficiency
-- =====================================================
-- This is an UPDATED version of 08_optimized_views.sql that adds
-- daily and 5-day P&L calculations to the existing views
-- =====================================================

-- =====================================================
-- OPTIMIZED CURRENT POSITIONS VIEW (unchanged)
-- =====================================================
DROP VIEW IF EXISTS current_positions CASCADE;

CREATE VIEW current_positions AS
WITH latest_date AS (
    SELECT 
        fund,
        MAX(date) as max_date
    FROM portfolio_positions
    GROUP BY fund
),
latest_positions AS (
    SELECT 
        pp.fund,
        pp.ticker,
        pp.company,
        pp.shares,
        pp.price as current_price,
        pp.cost_basis,
        pp.currency,
        pp.date,
        -- Pre-calculate market_value in the database
        (pp.shares * pp.price) as market_value,
        -- Pre-calculate unrealized P&L
        (pp.shares * pp.price - pp.cost_basis) as unrealized_pnl,
        -- Pre-calculate return percentage
        CASE 
            WHEN pp.cost_basis > 0 THEN 
                ((pp.shares * pp.price - pp.cost_basis) / pp.cost_basis) * 100
            ELSE 0 
        END as return_pct
    FROM portfolio_positions pp
    INNER JOIN latest_date ld 
        ON pp.fund = ld.fund 
        AND pp.date = ld.max_date
    WHERE pp.shares > 0
)
SELECT 
    fund,
    ticker,
    company,
    shares,
    current_price,
    cost_basis,
    market_value,
    unrealized_pnl,
    return_pct,
    currency,
    date
FROM latest_positions
ORDER BY fund, ticker;

-- =====================================================
-- OPTIMIZED LATEST POSITIONS VIEW (WITH HISTORICAL P&L)
-- =====================================================
DROP VIEW IF EXISTS latest_positions CASCADE;

CREATE VIEW latest_positions AS
WITH 
-- Get the latest position for each ticker per fund
ranked_positions AS (
    SELECT 
        fund,
        ticker,
        company,
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
-- Get yesterday's position for each ticker (for 1-day P&L)
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
-- Get 5-days-ago position for each ticker (for 5-day P&L)
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
    lp.company,
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
    AND yp.rn = 1
LEFT JOIN five_day_positions fp 
    ON lp.fund = fp.fund 
    AND lp.ticker = fp.ticker 
    AND fp.rn = 1
ORDER BY lp.fund, lp.market_value DESC;

-- =====================================================
-- OPTIMIZED DAILY PORTFOLIO SNAPSHOTS (unchanged)
-- =====================================================
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

-- =====================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_fund_date_ticker 
ON portfolio_positions(fund, date DESC, ticker);

CREATE INDEX IF NOT EXISTS idx_portfolio_positions_date_fund 
ON portfolio_positions(date DESC, fund);

CREATE INDEX IF NOT EXISTS idx_portfolio_positions_ticker_fund_date 
ON portfolio_positions(ticker, fund, date DESC);

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
GRANT SELECT ON current_positions TO authenticated;
GRANT SELECT ON current_positions TO service_role;
GRANT SELECT ON latest_positions TO authenticated;
GRANT SELECT ON latest_positions TO service_role;
GRANT SELECT ON daily_portfolio_snapshots TO authenticated;
GRANT SELECT ON daily_portfolio_snapshots TO service_role;

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON VIEW current_positions IS 'Current portfolio positions with pre-calculated market_value and P&L (most recent date per fund)';
COMMENT ON VIEW latest_positions IS 'Latest position for each ticker with pre-calculated market_value, P&L, and historical 1-day/5-day P&L (most recent per ticker per fund)';
COMMENT ON VIEW daily_portfolio_snapshots IS 'Daily portfolio snapshots with pre-calculated aggregates for historical P&L analysis';

-- =====================================================
-- VERIFICATION QUERY
-- =====================================================
-- Run this after applying the views to verify they work:
-- 
-- Check basic data:
-- SELECT fund, COUNT(*) as positions, SUM(market_value) as total_value 
-- FROM latest_positions 
-- WHERE fund = 'Project Chimera' 
-- GROUP BY fund;
--
-- Check P&L calculations:
-- SELECT 
--     ticker, 
--     company,
--     current_price,
--     unrealized_pnl,
--     daily_pnl,
--     daily_pnl_pct,
--     five_day_pnl,
--     five_day_pnl_pct,
--     yesterday_price,
--     five_day_price
-- FROM latest_positions
-- WHERE fund = 'Project Chimera'
-- ORDER BY market_value DESC
-- LIMIT 10;
--
-- Verify Total P&L ≠ Daily P&L:
-- SELECT 
--     COUNT(*) as total_positions,
--     COUNT(CASE WHEN ABS(unrealized_pnl - COALESCE(daily_pnl, 0)) < 0.01 THEN 1 END) as matching_pnl,
--     COUNT(CASE WHEN ABS(unrealized_pnl - COALESCE(daily_pnl, 0)) >= 0.01 THEN 1 END) as different_pnl
-- FROM latest_positions
-- WHERE fund = 'Project Chimera' AND daily_pnl IS NOT NULL;


