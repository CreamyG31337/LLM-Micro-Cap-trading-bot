-- Migration 36: Fix Congress Trades Unique Index to Support ON CONFLICT
-- Purpose: Replace partial unique index with a proper unique constraint that can be used in ON CONFLICT
-- Prerequisites: Migration 35 must be applied first
--
-- Problem: The current partial unique index uses COALESCE and WHERE clause:
--   CREATE UNIQUE INDEX idx_congress_trades_unique 
--   ON congress_trades(politician_id, ticker, transaction_date, amount, type, COALESCE(owner, 'Unknown'))
--   WHERE politician_id IS NOT NULL;
--
-- This cannot be used in ON CONFLICT because:
-- 1. PostgreSQL doesn't support ON CONFLICT with partial indexes (WHERE clauses)
-- 2. PostgreSQL doesn't support ON CONFLICT with expression indexes (COALESCE)
--
-- Solution: Drop the partial index and create a standard unique constraint

-- Step 1: Drop the existing partial unique index
DROP INDEX IF EXISTS idx_congress_trades_unique;

-- Step 2: Set all NULL owner values to 'Unknown' to prepare for constraint
UPDATE congress_trades 
SET owner = 'Unknown' 
WHERE owner IS NULL;

-- Step 3: Add NOT NULL constraint to owner column
ALTER TABLE congress_trades 
ALTER COLUMN owner SET NOT NULL;

-- Step 4: Set default value for owner column
ALTER TABLE congress_trades 
ALTER COLUMN owner SET DEFAULT 'Unknown';

-- Step 5: Create a standard unique constraint
-- This can be used in ON CONFLICT clauses
ALTER TABLE congress_trades 
ADD CONSTRAINT congress_trades_politician_ticker_date_amount_type_owner_key 
UNIQUE (politician_id, ticker, transaction_date, amount, type, owner);

-- Verification
SELECT 
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint 
WHERE conrelid = 'congress_trades'::regclass 
AND conname LIKE '%politician%ticker%'
ORDER BY conname;
