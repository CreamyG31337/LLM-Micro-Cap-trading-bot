-- =====================================================
-- CREATE CONGRESS TRADES TABLE (Supabase)
-- =====================================================
-- Stores congressional stock trading disclosures from Financial Modeling Prep API
-- Part of Congress Trading Module
-- 
-- Purpose: Track and analyze congressional stock trades for potential conflicts of interest
-- =====================================================

CREATE TABLE IF NOT EXISTS congress_trades (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    politician VARCHAR(200) NOT NULL,
    chamber VARCHAR(20) NOT NULL CHECK (chamber IN ('House', 'Senate')),
    transaction_date DATE NOT NULL,
    disclosure_date DATE NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('Purchase', 'Sale')),
    amount VARCHAR(100),                    -- Store as string range like "$1,001 - $15,000"
    asset_type VARCHAR(50) CHECK (asset_type IN ('Stock', 'Crypto')),
    conflict_score FLOAT,                   -- 0.0 to 1.0 from AI analysis
    notes TEXT,                             -- AI reasoning/analysis
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE congress_trades IS 
  'Congressional stock trading disclosures from FMP API. Analyzed for potential conflicts of interest.';

COMMENT ON COLUMN congress_trades.ticker IS 
  'Stock ticker symbol (e.g., "AAPL", "TSLA"). Empty/null tickers are skipped.';

COMMENT ON COLUMN congress_trades.politician IS 
  'Name of the politician who made the trade';

COMMENT ON COLUMN congress_trades.chamber IS 
  'Congressional chamber: "House" or "Senate"';

COMMENT ON COLUMN congress_trades.transaction_date IS 
  'Date when the trade was executed';

COMMENT ON COLUMN congress_trades.disclosure_date IS 
  'Date when the trade was disclosed to the public';

COMMENT ON COLUMN congress_trades.type IS 
  'Type of transaction: "Purchase" or "Sale"';

COMMENT ON COLUMN congress_trades.amount IS 
  'Transaction amount stored as string range (e.g., "$1,001 - $15,000")';

COMMENT ON COLUMN congress_trades.asset_type IS 
  'Type of asset: "Stock" or "Crypto"';

COMMENT ON COLUMN congress_trades.conflict_score IS 
  'AI-generated conflict score: 0.0 (no conflict) to 1.0 (high conflict)';

COMMENT ON COLUMN congress_trades.notes IS 
  'AI-generated reasoning and analysis of the trade';

-- Unique constraint to prevent duplicates
-- A politician can have multiple trades of the same ticker on the same date,
-- but only if the amount is different
CREATE UNIQUE INDEX IF NOT EXISTS idx_congress_trades_unique 
ON congress_trades(politician, ticker, transaction_date, amount);

-- Also create a UNIQUE constraint (PostgREST/Supabase upsert works better with constraints)
-- Use DO block to handle case where constraint already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_ticker_date_amount'
    ) THEN
        ALTER TABLE congress_trades 
        ADD CONSTRAINT congress_trades_unique_politician_ticker_date_amount 
        UNIQUE (politician, ticker, transaction_date, amount);
    END IF;
END $$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_congress_ticker ON congress_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_congress_politician ON congress_trades(politician);
CREATE INDEX IF NOT EXISTS idx_congress_transaction_date ON congress_trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_congress_disclosure_date ON congress_trades(disclosure_date DESC);
CREATE INDEX IF NOT EXISTS idx_congress_chamber ON congress_trades(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_conflict_score ON congress_trades(conflict_score DESC NULLS LAST);

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    total_count INTEGER;
    house_count INTEGER;
    senate_count INTEGER;
    purchase_count INTEGER;
    sale_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM congress_trades;
    SELECT COUNT(*) INTO house_count FROM congress_trades WHERE chamber = 'House';
    SELECT COUNT(*) INTO senate_count FROM congress_trades WHERE chamber = 'Senate';
    SELECT COUNT(*) INTO purchase_count FROM congress_trades WHERE type = 'Purchase';
    SELECT COUNT(*) INTO sale_count FROM congress_trades WHERE type = 'Sale';
    
    RAISE NOTICE '✅ Congress trades table created!';
    RAISE NOTICE '   Total trades: %', total_count;
    RAISE NOTICE '   House trades: %', house_count;
    RAISE NOTICE '   Senate trades: %', senate_count;
    RAISE NOTICE '   Purchases: %', purchase_count;
    RAISE NOTICE '   Sales: %', sale_count;
    RAISE NOTICE '';
    
    IF total_count > 0 THEN
        RAISE NOTICE 'Recent trades (last 10):';
        
        FOR r IN 
            SELECT politician, ticker, chamber, type, transaction_date, 
                   conflict_score, created_at
            FROM congress_trades 
            ORDER BY created_at DESC 
            LIMIT 10
        LOOP
            RAISE NOTICE '  % | % | % | % | % | Score: %.2f | %', 
                r.politician, r.ticker, r.chamber, r.type, 
                r.transaction_date, 
                COALESCE(r.conflict_score, 0.0), r.created_at;
        END LOOP;
    ELSE
        RAISE NOTICE '   No trades yet.';
        RAISE NOTICE '   Trades will be populated when fetch_congress_trades job runs.';
    END IF;
END $$;

