-- Diagnostic: Why is daily_pnl still $0?
-- Run this in Supabase SQL Editor to see what data exists

-- 1. Check latest position dates
SELECT 
    'Latest Position Dates' as check_name,
    date,
    COUNT(*) as position_count,
    SUM(shares * price) as total_value
FROM portfolio_positions
WHERE fund = 'Project Chimera'
GROUP BY date
ORDER BY date DESC
LIMIT 10;

-- 2. Check what latest_positions view returns
SELECT 
    'Latest Positions View Data' as check_name,
    ticker,
    date as latest_date,
    current_price,
    yesterday_price,
    yesterday_date,
    daily_pnl,
    daily_pnl_pct
FROM latest_positions
WHERE fund = 'Project Chimera'
ORDER BY market_value DESC
LIMIT 10;

-- 3. Check total daily P&L
SELECT 
    'Total Daily PnL' as check_name,
    SUM(COALESCE(daily_pnl, 0)) as total_daily_pnl,
    COUNT(*) as total_positions,
    COUNT(daily_pnl) as positions_with_pnl,
    COUNT(*) - COUNT(daily_pnl) as positions_with_null_pnl
FROM latest_positions
WHERE fund = 'Project Chimera';

-- 4. Check for gaps in recent dates
WITH recent_dates AS (
    SELECT DISTINCT date
    FROM portfolio_positions
    WHERE fund = 'Project Chimera'
    AND date >= CURRENT_DATE - INTERVAL '14 days'
    ORDER BY date DESC
)
SELECT 
    'Recent Date Gaps' as check_name,
    date,
    LAG(date) OVER (ORDER BY date DESC) as previous_date,
    EXTRACT(DAY FROM (LAG(date) OVER (ORDER BY date DESC) - date)) as days_gap
FROM recent_dates
ORDER BY date DESC;
