-- =====================================================
-- P&L CALCULATION VIEWS
-- =====================================================
-- Views for calculating portfolio P&L automatically
-- =====================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS current_positions CASCADE;
DROP VIEW IF EXISTS daily_pnl_summary CASCADE;
DROP VIEW IF EXISTS trade_performance CASCADE;
DROP VIEW IF EXISTS portfolio_summary CASCADE;

-- =====================================================
-- CURRENT POSITIONS VIEW
-- =====================================================
-- Shows the latest position for each ticker with calculated P&L
CREATE VIEW current_positions AS
WITH latest_positions AS (
    SELECT 
        fund,
        ticker,
        MAX(date) as latest_date
    FROM portfolio_positions
    GROUP BY fund, ticker
)
SELECT 
    pp.fund,
    pp.ticker,
    pp.company,
    pp.shares,
    pp.price as current_price,
    pp.cost_basis,
    (pp.shares * pp.price) as market_value,
    (pp.shares * pp.price - pp.cost_basis) as unrealized_pnl,
    CASE 
        WHEN pp.cost_basis > 0 THEN 
            ((pp.shares * pp.price - pp.cost_basis) / pp.cost_basis) * 100
        ELSE 0 
    END as return_percentage,
    pp.currency,
    pp.date as last_updated
FROM portfolio_positions pp
INNER JOIN latest_positions lp ON 
    pp.fund = lp.fund AND 
    pp.ticker = lp.ticker AND 
    pp.date = lp.latest_date
ORDER BY pp.fund, pp.ticker;

-- =====================================================
-- DAILY P&L SUMMARY VIEW
-- =====================================================
-- Shows daily portfolio performance summary
CREATE VIEW daily_pnl_summary AS
SELECT 
    fund,
    DATE(date) as trade_date,
    COUNT(DISTINCT ticker) as positions_count,
    SUM(shares * price) as total_market_value,
    SUM(cost_basis) as total_cost_basis,
    SUM(shares * price - cost_basis) as total_unrealized_pnl,
    CASE 
        WHEN SUM(cost_basis) > 0 THEN 
            (SUM(shares * price - cost_basis) / SUM(cost_basis)) * 100
        ELSE 0 
    END as total_return_percentage
FROM portfolio_positions
GROUP BY fund, DATE(date)
ORDER BY fund, trade_date DESC;

-- =====================================================
-- TRADE PERFORMANCE VIEW
-- =====================================================
-- Shows individual trade performance with current prices
CREATE VIEW trade_performance AS
SELECT 
    t.fund,
    t.ticker,
    t.date as trade_date,
    t.shares,
    t.price as trade_price,
    t.cost_basis,
    cp.current_price,
    cp.market_value,
    (cp.current_price - t.price) * t.shares as price_change_pnl,
    CASE 
        WHEN t.price > 0 THEN 
            ((cp.current_price - t.price) / t.price) * 100
        ELSE 0 
    END as return_percentage,
    t.reason,
    t.currency
FROM trade_log t
LEFT JOIN current_positions cp ON 
    t.ticker = cp.ticker AND 
    t.fund = cp.fund
WHERE t.shares > 0  -- Only buy transactions
ORDER BY t.fund, t.date DESC;

-- =====================================================
-- PORTFOLIO SUMMARY VIEW
-- =====================================================
-- High-level portfolio summary with totals
CREATE VIEW portfolio_summary AS
SELECT 
    fund,
    COUNT(DISTINCT ticker) as total_positions,
    SUM(shares * price) as total_market_value,
    SUM(cost_basis) as total_cost_basis,
    SUM(shares * price - cost_basis) as total_unrealized_pnl,
    CASE 
        WHEN SUM(cost_basis) > 0 THEN 
            (SUM(shares * price - cost_basis) / SUM(cost_basis)) * 100
        ELSE 0 
    END as total_return_percentage,
    MAX(date) as last_updated
FROM current_positions
GROUP BY fund
ORDER BY fund;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
-- Create indexes to improve view performance
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_fund_ticker_date 
ON portfolio_positions(fund, ticker, date DESC);

CREATE INDEX IF NOT EXISTS idx_trade_log_fund_ticker_date 
ON trade_log(fund, ticker, date DESC);

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON VIEW current_positions IS 'Latest position for each ticker with calculated P&L';
COMMENT ON VIEW daily_pnl_summary IS 'Daily portfolio performance summary';
COMMENT ON VIEW trade_performance IS 'Individual trade performance with current prices';
COMMENT ON VIEW portfolio_summary IS 'High-level portfolio summary with totals';
