-- Migration: Replace ticker column with tickers array
-- This allows storing multiple tickers per article (e.g., "top 5 tech stocks")

-- Step 1: Add new tickers array column
ALTER TABLE research_articles 
  ADD COLUMN IF NOT EXISTS tickers text[];

-- Step 2: Migrate existing data: convert single ticker to array
UPDATE research_articles 
SET tickers = ARRAY[ticker] 
WHERE ticker IS NOT NULL AND (tickers IS NULL OR array_length(tickers, 1) IS NULL);

-- Step 3: Create GIN index for fast array lookups
-- This index makes queries like WHERE 'AAPL' = ANY(tickers) very fast
CREATE INDEX IF NOT EXISTS idx_research_tickers_gin 
  ON research_articles USING GIN (tickers);

-- Step 4: Drop old ticker column and index (commented out for safety - uncomment after verifying migration)
-- DROP INDEX IF EXISTS idx_research_ticker;
-- ALTER TABLE research_articles DROP COLUMN IF EXISTS ticker;

