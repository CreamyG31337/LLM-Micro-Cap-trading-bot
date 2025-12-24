-- Cleanup Script: Remove Securities Not in Trade Log
-- Description: Safely delete test data from securities table by removing tickers that don't exist in trade_log
-- Date: 2025-12-24

-- First, let's see what we're about to delete (DRY RUN - uncomment to preview)
-- SELECT ticker, company_name, sector, industry 
-- FROM securities 
-- WHERE ticker NOT IN (SELECT DISTINCT ticker FROM trade_log);

-- Delete securities that aren't in the trade_log table
DELETE FROM securities
WHERE ticker NOT IN (
    SELECT DISTINCT ticker 
    FROM trade_log
);

-- Verify the cleanup
SELECT 
    COUNT(*) as remaining_securities,
    COUNT(DISTINCT CASE WHEN sector IS NOT NULL THEN ticker END) as with_sector_data,
    COUNT(DISTINCT CASE WHEN industry IS NOT NULL THEN ticker END) as with_industry_data
FROM securities;
