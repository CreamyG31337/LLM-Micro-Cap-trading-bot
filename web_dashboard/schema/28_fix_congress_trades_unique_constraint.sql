-- Migration 28: Fix Congress Trades Unique Constraint After Dropping Politician Column
-- Purpose: Update unique constraint to use politician_id instead of dropped politician column
-- Prerequisites: Migration 27 (drop politician column) must be applied first

-- Drop old unique constraint that references dropped 'politician' column
DO $$
BEGIN
    -- Drop constraint if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_ticker_date_amount_type_owner'
    ) THEN
        ALTER TABLE congress_trades 
        DROP CONSTRAINT congress_trades_unique_politician_ticker_date_amount_type_owner;
        
        RAISE NOTICE '✅ Dropped old unique constraint (with politician text column)';
    END IF;
    
    -- Also drop the variant without owner
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_ticker_date_amount_type'
    ) THEN
        ALTER TABLE congress_trades 
        DROP CONSTRAINT congress_trades_unique_politician_ticker_date_amount_type;
        
        RAISE NOTICE '✅ Dropped old unique constraint variant (without owner)';
    END IF;
END $$;

-- Drop old unique index
DROP INDEX IF EXISTS idx_congress_trades_unique;

-- Create new unique index with politician_id instead of politician
CREATE UNIQUE INDEX IF NOT EXISTS idx_congress_trades_unique 
ON congress_trades(politician_id, ticker, transaction_date, amount, type, COALESCE(owner, 'Unknown'));

-- Add new unique constraint with politician_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_id_ticker_date_amount_type_owner'
    ) THEN
        ALTER TABLE congress_trades 
        ADD CONSTRAINT congress_trades_unique_politician_id_ticker_date_amount_type_owner 
        UNIQUE (politician_id, ticker, transaction_date, amount, type, owner);
        
        RAISE NOTICE '✅ Added new unique constraint (with politician_id)';
    ELSE
        RAISE NOTICE '⚠️  New unique constraint already exists';
    END IF;
END $$;

-- Verification
DO $$
DECLARE
    constraint_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO constraint_count 
    FROM pg_constraint 
    WHERE conname = 'congress_trades_unique_politician_id_ticker_date_amount_type_owner';
    
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE indexname = 'idx_congress_trades_unique';
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ Constraint update complete!';
    RAISE NOTICE '   Unique constraint exists: %', CASE WHEN constraint_count > 0 THEN 'Yes' ELSE 'No' END;
    RAISE NOTICE '   Unique index exists: %', CASE WHEN index_count > 0 THEN 'Yes' ELSE 'No' END;
    RAISE NOTICE '   Now uses: politician_id (FK) instead of politician (text)';
END $$;

