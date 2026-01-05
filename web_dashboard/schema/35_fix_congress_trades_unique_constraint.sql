-- Migration 35: Fix Congress Trades Unique Constraint After Dropping Politician Column
-- Purpose: Update unique constraint to use politician_id instead of dropped politician column
-- Prerequisites: Migration 27 (drop politician column) must be applied first
--
-- This migration:
-- 1. Identifies and removes duplicate trades (keeps the one with lowest ID)
-- 2. Drops old unique constraints/indexes that reference dropped 'politician' column
-- 3. Creates new unique constraint using politician_id

-- Step 1: Remove duplicates before creating unique constraint
-- Keep the record with the lowest ID for each duplicate group
WITH duplicate_groups AS (
    SELECT 
        politician_id,
        ticker,
        transaction_date,
        amount,
        type,
        COALESCE(owner, 'Unknown') as owner_key,
        MIN(id) as keep_id,
        array_agg(id ORDER BY id) as all_ids
    FROM congress_trades
    WHERE politician_id IS NOT NULL
    GROUP BY politician_id, ticker, transaction_date, amount, type, COALESCE(owner, 'Unknown')
    HAVING COUNT(*) > 1
),
ids_to_delete AS (
    SELECT unnest(all_ids[2:]) as id_to_delete
    FROM duplicate_groups
)
DELETE FROM congress_trades
WHERE id IN (SELECT id_to_delete FROM ids_to_delete);

-- Step 2: Drop old unique constraint that references dropped 'politician' column
ALTER TABLE congress_trades 
DROP CONSTRAINT IF EXISTS congress_trades_unique_politician_ticker_date_amount_type_owner;

ALTER TABLE congress_trades 
DROP CONSTRAINT IF EXISTS congress_trades_unique_politician_ticker_date_amount_type;

-- Step 3: Drop old unique index
DROP INDEX IF EXISTS idx_congress_trades_unique;
DROP INDEX IF EXISTS congress_trades_unique_politician_id_ticker_date_amount_type_owner_idx;

-- Step 4: Create new unique index with politician_id instead of politician
-- Note: Using partial unique index (WHERE politician_id IS NOT NULL) because:
-- 1. Trades without politician_id (politician not in database) can't be deduplicated this way
-- 2. Multiple NULL politician_id rows are allowed, but uniqueness is enforced for known politicians
CREATE UNIQUE INDEX IF NOT EXISTS idx_congress_trades_unique 
ON congress_trades(politician_id, ticker, transaction_date, amount, type, COALESCE(owner, 'Unknown'))
WHERE politician_id IS NOT NULL;

-- Migration complete!
-- The unique index idx_congress_trades_unique now enforces uniqueness on:
-- (politician_id, ticker, transaction_date, amount, type, owner)
-- Only for rows where politician_id IS NOT NULL

