
    SELECT 
        fund,
        MAX(date) as latest_date,
        COUNT(*) as position_count
    FROM portfolio_positions
    GROUP BY fund
    ORDER BY latest_date DESC;
