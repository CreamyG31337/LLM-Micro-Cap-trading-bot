-- =====================================================
-- ADD UNIQUE CONSTRAINT TO PORTFOLIO_POSITIONS
-- =====================================================
-- Prevents duplicate portfolio positions for the same (fund, date, ticker) combination
-- This ensures data integrity and prevents NAV calculation errors
-- 
-- The constraint allows only one position record per fund per date per ticker
-- =====================================================

-- First, clean up any existing duplicates (keep most recent)
-- This is done via application script: debug/clean_existing_duplicates.py
-- Run that script before applying this migration

-- Add unique index on (fund, date, ticker)
-- Note: The date column is TIMESTAMP WITH TIME ZONE, but we want uniqueness per day
-- For Supabase compatibility, we'll use a trigger to populate date_only column
-- (Generated columns with date expressions are not immutable in PostgreSQL)

-- Add date_only column (regular column, not generated)
ALTER TABLE portfolio_positions 
ADD COLUMN IF NOT EXISTS date_only DATE;

-- Create function to set date_only from date column
CREATE OR REPLACE FUNCTION set_portfolio_position_date_only()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_only := (NEW.date AT TIME ZONE 'UTC')::date;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically set date_only on insert/update
DROP TRIGGER IF EXISTS trigger_set_portfolio_position_date_only ON portfolio_positions;
CREATE TRIGGER trigger_set_portfolio_position_date_only
    BEFORE INSERT OR UPDATE ON portfolio_positions
    FOR EACH ROW
    EXECUTE FUNCTION set_portfolio_position_date_only();

-- Backfill existing rows
UPDATE portfolio_positions 
SET date_only = (date AT TIME ZONE 'UTC')::date
WHERE date_only IS NULL;

-- Create unique index on the date_only column
CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_positions_unique 
ON portfolio_positions(fund, ticker, date_only);

-- Also create a UNIQUE constraint (PostgREST/Supabase upsert works better with constraints)
-- The constraint uses the same columns as the index
ALTER TABLE portfolio_positions 
ADD CONSTRAINT portfolio_positions_unique_fund_ticker_date 
UNIQUE (fund, ticker, date_only);

-- Add comment for documentation
COMMENT ON INDEX idx_portfolio_positions_unique IS 
'Ensures only one portfolio position per fund per date per ticker. Prevents duplicate positions that cause NAV calculation errors.';

