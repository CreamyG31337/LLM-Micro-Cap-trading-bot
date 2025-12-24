-- Check portfolio positions for RRSP Lance Webull fund
-- This will show us what dates exist and if there are duplicates

SELECT 
    date::date as position_date,
    COUNT(*) as num_positions,
    COUNT(DISTINCT ticker) as num_tickers,
    MIN(date) as earliest_time,
    MAX(date) as latest_time
FROM portfolio_positions
WHERE fund = 'RRSP Lance Webull'
GROUP BY date::date
ORDER BY position_date DESC
LIMIT 20;

-- Also check the latest timestamp
SELECT MAX(date) as latest_timestamp
FROM portfolio_positions
WHERE fund = 'RRSP Lance Webull';
