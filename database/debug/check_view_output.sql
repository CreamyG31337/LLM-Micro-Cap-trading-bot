-- Quick check: What is latest_positions view returning?
-- This will show if the view is correctly calculating daily_pnl

SELECT 
    ticker,
    date as latest_date,
    current_price,
    shares,
    yesterday_price,
    yesterday_date,
    daily_pnl,
    daily_pnl_pct,
    -- Manual calculation to verify
    CASE 
        WHEN yesterday_price IS NOT NULL THEN
            (current_price - yesterday_price) * shares
        ELSE NULL
    END as manual_daily_pnl
FROM latest_positions
WHERE fund = 'Project Chimera'
ORDER BY market_value DESC
LIMIT 10;
