-- =====================================================
-- ADD POLITICIAN_ID FOREIGN KEY TO CONGRESS_TRADES
-- =====================================================
-- Migration to add proper FK relationship between congress_trades and politicians
-- This improves data integrity and enables proper joins/analysis
-- =====================================================

-- Step 1: Add nullable politician_id column
ALTER TABLE congress_trades 
ADD COLUMN IF NOT EXISTS politician_id INTEGER;

-- Step 2: Add foreign key constraint
ALTER TABLE congress_trades
ADD CONSTRAINT fk_congress_trades_politician
FOREIGN KEY (politician_id) 
REFERENCES politicians(id)
ON DELETE SET NULL;  -- If politician deleted, keep trade but null the FK

-- Step 3: Create index for performance
CREATE INDEX IF NOT EXISTS idx_congress_trades_politician_id 
ON congress_trades(politician_id);

-- Comments
COMMENT ON COLUMN congress_trades.politician_id IS 
  'Foreign key to politicians table. Links trade to official politician record by ID rather than text name.';

-- Note: After this migration, run backfill script to populate politician_id for existing records
-- Then optionally drop the politician (text) column once fully migrated
