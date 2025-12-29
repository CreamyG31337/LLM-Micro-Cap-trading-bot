-- =====================================================
-- CREATE CONGRESS TRADES STAGING TABLE
-- =====================================================
-- Staging table for importing congress trades before validation
-- Allows review and quality checks before promoting to production

CREATE TABLE IF NOT EXISTS congress_trades_staging (
    -- Same schema as congress_trades
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    politician VARCHAR(200) NOT NULL,
    chamber VARCHAR(20) NOT NULL CHECK (chamber IN ('House', 'Senate')),
    transaction_date DATE NOT NULL,
    disclosure_date DATE NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('Purchase', 'Sale', 'Exchange', 'Received')),
    amount VARCHAR(100),
    price NUMERIC(10, 2) DEFAULT NULL,
    asset_type VARCHAR(50) CHECK (asset_type IN ('Stock', 'Crypto')),
    party VARCHAR(50) CHECK (party IN ('Republican', 'Democrat', 'Independent')),
    state VARCHAR(2),
    owner VARCHAR(100),
    conflict_score FLOAT,
    notes TEXT,
    
    -- Staging-specific metadata
    import_batch_id UUID DEFAULT gen_random_uuid(),
    import_timestamp TIMESTAMPTZ DEFAULT NOW(),
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'approved', 'rejected')),
    validation_notes TEXT,
    promoted_to_production BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMPTZ,
    
    -- Source tracking
    source_url TEXT,
    raw_data JSONB
);

-- Indexes for staging table
CREATE INDEX IF NOT EXISTS idx_staging_batch ON congress_trades_staging(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_staging_status ON congress_trades_staging(validation_status);
CREATE INDEX IF NOT EXISTS idx_staging_promoted ON congress_trades_staging(promoted_to_production);
CREATE INDEX IF NOT EXISTS idx_staging_politician ON congress_trades_staging(politician);
CREATE INDEX IF NOT EXISTS idx_staging_ticker ON congress_trades_staging(ticker);
CREATE INDEX IF NOT EXISTS idx_staging_date ON congress_trades_staging(transaction_date DESC);

-- Comments
COMMENT ON TABLE congress_trades_staging IS 
  'Staging table for congress trades imports. Data is validated here before promotion to production.';

COMMENT ON COLUMN congress_trades_staging.import_batch_id IS
  'UUID identifying the import batch. All trades imported in one scraper run share the same batch ID.';

COMMENT ON COLUMN congress_trades_staging.validation_status IS
  'Status of validation: pending (awaiting review), approved (ready for promotion), rejected (will not be promoted)';

COMMENT ON COLUMN congress_trades_staging.raw_data IS
  'Original JSON data from scraper for debugging and troubleshooting';

-- Verification
DO $$
DECLARE
    staging_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO staging_count FROM congress_trades_staging;
    
    RAISE NOTICE '✅ Congress trades staging table created!';
    RAISE NOTICE '   Current staging records: %', staging_count;
    RAISE NOTICE '';
    RAISE NOTICE '   Use seed_congress_trades_staging.py to import new data';
    RAISE NOTICE '   Use promote_congress_trades.py to move validated data to production';
END $$;
