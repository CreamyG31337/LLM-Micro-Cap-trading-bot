-- =====================================================
-- LATEST POSITIONS VIEW
-- =====================================================
-- This view efficiently gets the latest position for each ticker
-- This replaces the inefficient Python grouping
-- =====================================================

-- Drop existing view if it exists
DROP VIEW IF EXISTS latest_positions CASCADE;

-- Create the latest positions view with P&L calculations
CREATE VIEW latest_positions AS
WITH current_positions AS (
    SELECT DISTINCT ON (ticker, fund) 
        id,
        ticker,
        company,
        shares,
        price,
        cost_basis,
        pnl,
        currency,
        fund,
        date,
        created_at,
        updated_at
    FROM portfolio_positions 
    WHERE shares > 0
    ORDER BY ticker, fund, date DESC
),
historical_prices AS (
    SELECT 
        ticker,
        fund,
        price,
        date,
        ROW_NUMBER() OVER (PARTITION BY ticker, fund ORDER BY date DESC) as rn
    FROM portfolio_positions 
    WHERE shares > 0
),
daily_pnl AS (
    SELECT 
        cp.ticker,
        cp.fund,
        cp.shares,
        cp.price as current_price,
        -- Get previous day's price
        (SELECT price FROM historical_prices hp 
         WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2) as prev_price,
        -- Calculate daily P&L
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2) IS NOT NULL 
            THEN (cp.price - (SELECT price FROM historical_prices hp 
                              WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2)) * cp.shares
            ELSE 0
        END as daily_pnl_dollar,
        -- Calculate daily P&L percentage
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2) IS NOT NULL 
            THEN ((cp.price - (SELECT price FROM historical_prices hp 
                               WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2)) / 
                   (SELECT price FROM historical_prices hp 
                    WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 2)) * 100
            ELSE 0
        END as daily_pnl_pct
    FROM current_positions cp
),
weekly_pnl AS (
    SELECT 
        cp.ticker,
        cp.fund,
        cp.shares,
        cp.price as current_price,
        -- Get 7 days ago price
        (SELECT price FROM historical_prices hp 
         WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8) as week_ago_price,
        -- Calculate 7-day P&L
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8) IS NOT NULL 
            THEN (cp.price - (SELECT price FROM historical_prices hp 
                              WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8)) * cp.shares
            ELSE 0
        END as weekly_pnl_dollar,
        -- Calculate 7-day P&L percentage
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8) IS NOT NULL 
            THEN ((cp.price - (SELECT price FROM historical_prices hp 
                               WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8)) / 
                   (SELECT price FROM historical_prices hp 
                    WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 8)) * 100
            ELSE 0
        END as weekly_pnl_pct
    FROM current_positions cp
),
monthly_pnl AS (
    SELECT 
        cp.ticker,
        cp.fund,
        cp.shares,
        cp.price as current_price,
        -- Get 30 days ago price
        (SELECT price FROM historical_prices hp 
         WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31) as month_ago_price,
        -- Calculate 30-day P&L
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31) IS NOT NULL 
            THEN (cp.price - (SELECT price FROM historical_prices hp 
                              WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31)) * cp.shares
            ELSE 0
        END as monthly_pnl_dollar,
        -- Calculate 30-day P&L percentage
        CASE 
            WHEN (SELECT price FROM historical_prices hp 
                  WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31) IS NOT NULL 
            THEN ((cp.price - (SELECT price FROM historical_prices hp 
                               WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31)) / 
                   (SELECT price FROM historical_prices hp 
                    WHERE hp.ticker = cp.ticker AND hp.fund = cp.fund AND hp.rn = 31)) * 100
            ELSE 0
        END as monthly_pnl_pct
    FROM current_positions cp
)
SELECT 
    cp.*,
    dp.daily_pnl_dollar,
    dp.daily_pnl_pct,
    wp.weekly_pnl_dollar,
    wp.weekly_pnl_pct,
    mp.monthly_pnl_dollar,
    mp.monthly_pnl_pct
FROM current_positions cp
LEFT JOIN daily_pnl dp ON cp.ticker = dp.ticker AND cp.fund = dp.fund
LEFT JOIN weekly_pnl wp ON cp.ticker = wp.ticker AND cp.fund = wp.fund
LEFT JOIN monthly_pnl mp ON cp.ticker = mp.ticker AND cp.fund = mp.fund;

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_ticker_fund_date 
ON portfolio_positions(ticker, fund, date DESC);

-- Grant permissions
GRANT SELECT ON latest_positions TO authenticated;
GRANT SELECT ON latest_positions TO service_role;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Latest positions view created successfully!';
    RAISE NOTICE '📋 This view efficiently groups positions by ticker and fund';
    RAISE NOTICE '🔧 Use: SELECT * FROM latest_positions WHERE fund = ''FUND_NAME''';
END $$;
