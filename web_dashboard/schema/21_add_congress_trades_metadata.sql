-- =====================================================
-- MIGRATION: Add party, state, owner, representative columns
-- =====================================================
-- Adds metadata fields to existing congress_trades table without dropping data
-- Run this ONCE to upgrade the schema

-- Add new columns (safe - no data loss)
ALTER TABLE congress_trades 
ADD COLUMN IF NOT EXISTS party VARCHAR(50) CHECK (party IN ('Republican', 'Democrat', 'Independent')),
ADD COLUMN IF NOT EXISTS state VARCHAR(2),
ADD COLUMN IF NOT EXISTS owner VARCHAR(100),
ADD COLUMN IF NOT EXISTS representative VARCHAR(200);

-- Update notes column comment
COMMENT ON COLUMN congress_trades.notes IS
  'AI-generated reasoning, tooltip from source, or trade description';

-- Add comments for new columns
COMMENT ON COLUMN congress_trades.party IS
  'Political party affiliation: Republican, Democrat, or Independent';

COMMENT ON COLUMN congress_trades.state IS
  'Two-letter state code of the politician (e.g., CA, NY, TX)';

COMMENT ON COLUMN congress_trades.owner IS
  'Asset owner: Self, Spouse, Dependent Child, Joint, etc.';

COMMENT ON COLUMN congress_trades.representative IS
  'Full representative name (may differ from politician for spousal/dependent trades)';

-- Drop old unique constraint
ALTER TABLE congress_trades DROP CONSTRAINT IF EXISTS congress_trades_unique_politician_ticker_date_amount_type;

-- Drop old unique index
DROP INDEX IF EXISTS idx_congress_trades_unique;

-- Add new unique constraint with owner field
-- Note: Using COALESCE in index to handle NULL owner values
CREATE UNIQUE INDEX IF NOT EXISTS idx_congress_trades_unique 
ON congress_trades(politician, ticker, transaction_date, amount, type, COALESCE(owner, 'Unknown'));

-- Add new constraint (for Supabase upsert)
ALTER TABLE congress_trades 
ADD CONSTRAINT congress_trades_unique_politician_ticker_date_amount_type_owner 
UNIQUE (politician, ticker, transaction_date, amount, type, owner);

-- Add new indexes
CREATE INDEX IF NOT EXISTS idx_congress_party ON congress_trades(party);
CREATE INDEX IF NOT EXISTS idx_congress_state ON congress_trades(state);
CREATE INDEX IF NOT EXISTS idx_congress_owner ON congress_trades(owner);

-- Verification
DO $$
DECLARE
    total_count INTEGER;
    party_count INTEGER;
    state_count INTEGER;
    owner_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM congress_trades;
    SELECT COUNT(*) INTO party_count FROM congress_trades WHERE party IS NOT NULL;
    SELECT COUNT(*) INTO state_count FROM congress_trades WHERE state IS NOT NULL;
    SELECT COUNT(*) INTO owner_count FROM congress_trades WHERE owner IS NOT NULL;
    
    RAISE NOTICE '✅ Migration complete!';
    RAISE NOTICE '   Total trades: %', total_count;
    RAISE NOTICE '   Trades with party: %', party_count;
    RAISE NOTICE '   Trades with state: %', state_count;
    RAISE NOTICE '   Trades with owner: %', owner_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Run scraper/job to populate new fields for existing records.';
END $$;
