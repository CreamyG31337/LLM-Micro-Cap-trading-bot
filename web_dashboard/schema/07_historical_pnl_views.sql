-- =====================================================
-- HISTORICAL P&L CALCULATION VIEWS
-- =====================================================
-- Views for calculating 7-day and 30-day P&L from historical data
-- =====================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS historical_pnl_summary CASCADE;
DROP VIEW IF EXISTS daily_portfolio_snapshots CASCADE;
DROP VIEW IF EXISTS weekly_pnl_summary CASCADE;
DROP VIEW IF EXISTS monthly_pnl_summary CASCADE;

-- =====================================================
-- DAILY PORTFOLIO SNAPSHOTS VIEW
-- =====================================================
-- Creates daily snapshots of portfolio values for historical P&L calculations
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
-- HISTORICAL P&L SUMMARY VIEW
-- =====================================================
-- Shows current portfolio with 7-day and 30-day P&L calculations
CREATE VIEW historical_pnl_summary AS
WITH current_snapshot AS (
    SELECT *
    FROM daily_portfolio_snapshots
    WHERE snapshot_date = (
        SELECT MAX(snapshot_date) 
        FROM daily_portfolio_snapshots
    )
),
seven_days_ago AS (
    SELECT *
    FROM daily_portfolio_snapshots
    WHERE snapshot_date = (
        SELECT MAX(snapshot_date) 
        FROM daily_portfolio_snapshots
        WHERE snapshot_date <= CURRENT_DATE - INTERVAL '7 days'
    )
),
thirty_days_ago AS (
    SELECT *
    FROM daily_portfolio_snapshots
    WHERE snapshot_date = (
        SELECT MAX(snapshot_date) 
        FROM daily_portfolio_snapshots
        WHERE snapshot_date <= CURRENT_DATE - INTERVAL '30 days'
    )
)
SELECT 
    cs.fund,
    cs.snapshot_date as current_date,
    cs.total_market_value as current_value,
    cs.total_cost_basis as current_cost_basis,
    cs.total_unrealized_pnl as current_pnl,
    cs.total_return_pct as current_return_pct,
    
    -- 7-day P&L
    CASE 
        WHEN sda.total_market_value IS NOT NULL THEN 
            cs.total_market_value - sda.total_market_value
        ELSE 0 
    END as pnl_7d,
    CASE 
        WHEN sda.total_market_value IS NOT NULL AND sda.total_market_value > 0 THEN 
            ((cs.total_market_value - sda.total_market_value) / sda.total_market_value) * 100
        ELSE 0 
    END as return_pct_7d,
    
    -- 30-day P&L
    CASE 
        WHEN tda.total_market_value IS NOT NULL THEN 
            cs.total_market_value - tda.total_market_value
        ELSE 0 
    END as pnl_30d,
    CASE 
        WHEN tda.total_market_value IS NOT NULL AND tda.total_market_value > 0 THEN 
            ((cs.total_market_value - tda.total_market_value) / tda.total_market_value) * 100
        ELSE 0 
    END as return_pct_30d,
    
    -- Historical values for reference
    sda.total_market_value as value_7d_ago,
    tda.total_market_value as value_30d_ago,
    sda.snapshot_date as date_7d_ago,
    tda.snapshot_date as date_30d_ago
FROM current_snapshot cs
LEFT JOIN seven_days_ago sda ON cs.fund = sda.fund
LEFT JOIN thirty_days_ago tda ON cs.fund = tda.fund;

-- =====================================================
-- WEEKLY P&L SUMMARY VIEW
-- =====================================================
-- Shows weekly portfolio performance
CREATE VIEW weekly_pnl_summary AS
WITH weekly_data AS (
    SELECT 
        fund,
        DATE_TRUNC('week', snapshot_date) as week_start,
        MAX(snapshot_date) as latest_date_in_week,
        AVG(total_market_value) as avg_weekly_value,
        MAX(total_market_value) as max_weekly_value,
        MIN(total_market_value) as min_weekly_value,
        MAX(total_unrealized_pnl) as max_weekly_pnl,
        MIN(total_unrealized_pnl) as min_weekly_pnl
    FROM daily_portfolio_snapshots
    GROUP BY fund, DATE_TRUNC('week', snapshot_date)
),
weekly_changes AS (
    SELECT 
        *,
        LAG(total_market_value) OVER (
            PARTITION BY fund 
            ORDER BY week_start
        ) as prev_week_value,
        LAG(total_unrealized_pnl) OVER (
            PARTITION BY fund 
            ORDER BY week_start
        ) as prev_week_pnl
    FROM weekly_data
)
SELECT 
    fund,
    week_start,
    latest_date_in_week,
    avg_weekly_value,
    max_weekly_value,
    min_weekly_value,
    max_weekly_pnl,
    min_weekly_pnl,
    CASE 
        WHEN prev_week_value IS NOT NULL THEN 
            avg_weekly_value - prev_week_value
        ELSE 0 
    END as week_over_week_change,
    CASE 
        WHEN prev_week_value IS NOT NULL AND prev_week_value > 0 THEN 
            ((avg_weekly_value - prev_week_value) / prev_week_value) * 100
        ELSE 0 
    END as week_over_week_pct
FROM weekly_changes
ORDER BY fund, week_start DESC;

-- =====================================================
-- MONTHLY P&L SUMMARY VIEW
-- =====================================================
-- Shows monthly portfolio performance
CREATE VIEW monthly_pnl_summary AS
WITH monthly_data AS (
    SELECT 
        fund,
        DATE_TRUNC('month', snapshot_date) as month_start,
        MAX(snapshot_date) as latest_date_in_month,
        AVG(total_market_value) as avg_monthly_value,
        MAX(total_market_value) as max_monthly_value,
        MIN(total_market_value) as min_monthly_value,
        MAX(total_unrealized_pnl) as max_monthly_pnl,
        MIN(total_unrealized_pnl) as min_monthly_pnl
    FROM daily_portfolio_snapshots
    GROUP BY fund, DATE_TRUNC('month', snapshot_date)
),
monthly_changes AS (
    SELECT 
        *,
        LAG(total_market_value) OVER (
            PARTITION BY fund 
            ORDER BY month_start
        ) as prev_month_value,
        LAG(total_unrealized_pnl) OVER (
            PARTITION BY fund 
            ORDER BY month_start
        ) as prev_month_pnl
    FROM monthly_data
)
SELECT 
    fund,
    month_start,
    latest_date_in_month,
    avg_monthly_value,
    max_monthly_value,
    min_monthly_value,
    max_monthly_pnl,
    min_monthly_pnl,
    CASE 
        WHEN prev_month_value IS NOT NULL THEN 
            avg_monthly_value - prev_month_value
        ELSE 0 
    END as month_over_month_change,
    CASE 
        WHEN prev_month_value IS NOT NULL AND prev_month_value > 0 THEN 
            ((avg_monthly_value - prev_month_value) / prev_month_value) * 100
        ELSE 0 
    END as month_over_month_pct
FROM monthly_changes
ORDER BY fund, month_start DESC;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
-- Create indexes to improve view performance
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_fund_date 
ON portfolio_positions(fund, date DESC);

CREATE INDEX IF NOT EXISTS idx_portfolio_positions_fund_ticker_date 
ON portfolio_positions(fund, ticker, date DESC);

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON VIEW daily_portfolio_snapshots IS 'Daily portfolio snapshots for historical P&L calculations';
COMMENT ON VIEW historical_pnl_summary IS 'Current portfolio with 7-day and 30-day P&L calculations';
COMMENT ON VIEW weekly_pnl_summary IS 'Weekly portfolio performance summary';
COMMENT ON VIEW monthly_pnl_summary IS 'Monthly portfolio performance summary';
