-- =====================================================
-- UPDATE CONGRESS TRADES UNIQUE CONSTRAINT
-- =====================================================
-- Add 'type' to the unique constraint to allow same politician/ticker/date/amount
-- with different transaction types (Purchase, Sale, Exchange)
-- Part of Congress Trading Module
-- 
-- Purpose: Support multiple transaction types for the same trade details
-- =====================================================

-- Drop old unique constraint if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_ticker_date_amount'
    ) THEN
        ALTER TABLE congress_trades 
        DROP CONSTRAINT congress_trades_unique_politician_ticker_date_amount;
        
        RAISE NOTICE '✅ Dropped old unique constraint (without type)';
    ELSE
        RAISE NOTICE '⚠️  Old unique constraint not found (may have different name)';
    END IF;
END $$;

-- Drop old unique index if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_congress_trades_unique'
    ) THEN
        DROP INDEX IF EXISTS idx_congress_trades_unique;
        
        RAISE NOTICE '✅ Dropped old unique index (without type)';
    END IF;
END $$;

-- Create new unique index with type included
CREATE UNIQUE INDEX IF NOT EXISTS idx_congress_trades_unique 
ON congress_trades(politician, ticker, transaction_date, amount, type);

-- Add new unique constraint with type included
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_unique_politician_ticker_date_amount_type'
    ) THEN
        ALTER TABLE congress_trades 
        ADD CONSTRAINT congress_trades_unique_politician_ticker_date_amount_type 
        UNIQUE (politician, ticker, transaction_date, amount, type);
        
        RAISE NOTICE '✅ Added new unique constraint (with type)';
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
    WHERE conname = 'congress_trades_unique_politician_ticker_date_amount_type';
    
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE indexname = 'idx_congress_trades_unique';
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ Constraint update complete!';
    RAISE NOTICE '   Unique constraint exists: %', CASE WHEN constraint_count > 0 THEN 'Yes' ELSE 'No' END;
    RAISE NOTICE '   Unique index exists: %', CASE WHEN index_count > 0 THEN 'Yes' ELSE 'No' END;
    RAISE NOTICE '   Now allows: Same politician/ticker/date/amount with different types';
END $$;


