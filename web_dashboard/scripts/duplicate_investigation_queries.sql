-- =====================================================
-- SQL Queries for Investigating Duplicate Trades
-- =====================================================
-- Use these queries to investigate duplicates in congress_trades_staging
-- Replace 'YOUR_BATCH_ID' with your actual batch_id

-- =====================================================
-- 1. Find all duplicate groups with counts
-- =====================================================
WITH duplicate_groups AS (
    SELECT 
        politician,
        ticker,
        transaction_date,
        type,
        amount,
        COALESCE(owner, 'Not-Disclosed') as owner,
        COUNT(*) as duplicate_count,
        array_agg(id ORDER BY id) as record_ids,
        array_agg(disclosure_date ORDER BY id) as disclosure_dates,
        array_agg(price ORDER BY id) as prices,
        array_agg(import_timestamp ORDER BY id) as import_timestamps
    FROM congress_trades_staging
    WHERE import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
    GROUP BY politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')
    HAVING COUNT(*) > 1
)
SELECT 
    politician,
    ticker,
    transaction_date,
    type,
    amount,
    owner,
    duplicate_count,
    record_ids,
    disclosure_dates,
    prices,
    import_timestamps
FROM duplicate_groups
ORDER BY duplicate_count DESC, politician, ticker, transaction_date;

-- =====================================================
-- 2. Count duplicates by politician
-- =====================================================
WITH duplicate_groups AS (
    SELECT 
        politician,
        ticker,
        transaction_date,
        type,
        amount,
        COALESCE(owner, 'Not-Disclosed') as owner,
        COUNT(*) as duplicate_count
    FROM congress_trades_staging
    WHERE import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
    GROUP BY politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')
    HAVING COUNT(*) > 1
)
SELECT 
    politician,
    SUM(duplicate_count) as total_duplicate_records,
    COUNT(*) as duplicate_groups
FROM duplicate_groups
GROUP BY politician
ORDER BY total_duplicate_records DESC;

-- =====================================================
-- 3. Show detailed duplicate records for a specific politician
-- =====================================================
-- Replace 'Rohit Khanna' with the politician you want to investigate
WITH duplicate_keys AS (
    SELECT 
        politician,
        ticker,
        transaction_date,
        type,
        amount,
        COALESCE(owner, 'Not-Disclosed') as owner
    FROM congress_trades_staging
    WHERE import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
      AND politician = 'Rohit Khanna'  -- Replace with politician name
    GROUP BY politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')
    HAVING COUNT(*) > 1
)
SELECT 
    s.id,
    s.politician,
    s.ticker,
    s.transaction_date,
    s.disclosure_date,
    s.type,
    s.amount,
    s.owner,
    s.price,
    s.chamber,
    s.party,
    s.state,
    s.asset_type,
    s.source_url,
    s.import_timestamp
FROM congress_trades_staging s
INNER JOIN duplicate_keys dk ON 
    s.politician = dk.politician AND
    s.ticker = dk.ticker AND
    s.transaction_date = dk.transaction_date AND
    s.type = dk.type AND
    s.amount = dk.amount AND
    COALESCE(s.owner, 'Not-Disclosed') = dk.owner
WHERE s.import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
ORDER BY s.politician, s.ticker, s.transaction_date, s.type, s.id;

-- =====================================================
-- 4. Check if duplicates are truly identical (all fields match)
-- =====================================================
WITH duplicate_groups AS (
    SELECT 
        politician,
        ticker,
        transaction_date,
        type,
        amount,
        COALESCE(owner, 'Not-Disclosed') as owner,
        COUNT(*) as duplicate_count,
        COUNT(DISTINCT disclosure_date) as distinct_disclosure_dates,
        COUNT(DISTINCT price) as distinct_prices,
        COUNT(DISTINCT chamber) as distinct_chambers,
        COUNT(DISTINCT party) as distinct_parties,
        COUNT(DISTINCT state) as distinct_states,
        COUNT(DISTINCT asset_type) as distinct_asset_types,
        COUNT(DISTINCT source_url) as distinct_source_urls
    FROM congress_trades_staging
    WHERE import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
    GROUP BY politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')
    HAVING COUNT(*) > 1
)
SELECT 
    politician,
    ticker,
    transaction_date,
    type,
    duplicate_count,
    CASE 
        WHEN distinct_disclosure_dates = 1 AND distinct_prices = 1 AND distinct_chambers = 1 
             AND distinct_parties = 1 AND distinct_states = 1 AND distinct_asset_types = 1 
             AND distinct_source_urls = 1
        THEN 'IDENTICAL - True duplicates'
        ELSE 'DIFFERENT - May be legitimate separate trades'
    END as duplicate_type,
    distinct_disclosure_dates,
    distinct_prices,
    distinct_chambers,
    distinct_parties,
    distinct_states
FROM duplicate_groups
ORDER BY duplicate_count DESC, politician, ticker;

-- =====================================================
-- 5. Find records that should be deleted (keep the first one)
-- =====================================================
-- This identifies which specific record IDs should be deleted
-- Keep the record with the lowest ID in each duplicate group
WITH duplicate_groups AS (
    SELECT 
        politician,
        ticker,
        transaction_date,
        type,
        amount,
        COALESCE(owner, 'Not-Disclosed') as owner,
        MIN(id) as keep_id,
        array_agg(id ORDER BY id) as all_ids
    FROM congress_trades_staging
    WHERE import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
    GROUP BY politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')
    HAVING COUNT(*) > 1
),
records_to_delete AS (
    SELECT unnest(all_ids[2:]) as id_to_delete
    FROM duplicate_groups
)
SELECT 
    s.id,
    s.politician,
    s.ticker,
    s.transaction_date,
    s.type,
    s.amount,
    s.owner,
    s.import_timestamp
FROM congress_trades_staging s
INNER JOIN records_to_delete rtd ON s.id = rtd.id_to_delete
WHERE s.import_batch_id = 'YOUR_BATCH_ID'  -- Replace with your batch_id
ORDER BY s.politician, s.ticker, s.transaction_date, s.id;

-- =====================================================
-- 6. Summary statistics
-- =====================================================
SELECT 
    COUNT(*) as total_trades,
    COUNT(DISTINCT (politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed'))) as unique_trades,
    COUNT(*) - COUNT(DISTINCT (politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed'))) as duplicate_count,
    ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT (politician, ticker, transaction_date, type, amount, COALESCE(owner, 'Not-Disclosed')))) / COUNT(*), 2) as duplicate_percentage
FROM congress_trades_staging
WHERE import_batch_id = 'YOUR_BATCH_ID';  -- Replace with your batch_id

