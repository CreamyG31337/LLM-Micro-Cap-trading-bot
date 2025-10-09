-- =====================================================
-- OPTIMIZED PORTFOLIO VIEWS
-- =====================================================
-- Pre-calculate market_value and P&L in database for efficiency
-- =====================================================

-- =====================================================
-- OPTIMIZED CURRENT POSITIONS VIEW
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
-- OPTIMIZED LATEST POSITIONS VIEW
-- =====================================================
DROP VIEW IF EXISTS latest_positions CASCADE;

CREATE VIEW latest_positions AS
WITH ranked_positions AS (
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
    CASE 
        WHEN cost_basis > 0 THEN 
            (unrealized_pnl / cost_basis) * 100
        ELSE 0 
    END as return_pct,
    currency,
    date
FROM ranked_positions
WHERE rn = 1
ORDER BY fund, ticker;

-- =====================================================
-- OPTIMIZED DAILY PORTFOLIO SNAPSHOTS
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
-- UPDATE HISTORICAL P&L SUMMARY VIEW
-- =====================================================
-- No changes needed - it already uses daily_portfolio_snapshots

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
COMMENT ON VIEW latest_positions IS 'Latest position for each ticker with pre-calculated market_value and P&L (most recent per ticker per fund)';
COMMENT ON VIEW daily_portfolio_snapshots IS 'Daily portfolio snapshots with pre-calculated aggregates for historical P&L analysis';

-- =====================================================
-- VERIFICATION QUERY
-- =====================================================
-- Run this after applying the views to verify they work:
-- SELECT fund, COUNT(*) as positions, SUM(market_value) as total_value 
-- FROM current_positions 
-- WHERE fund = 'TEST' 
-- GROUP BY fund;

