-- =====================================================
-- UPDATE CONGRESS TRADES TYPE CONSTRAINT
-- =====================================================
-- Allow "Received" as a valid transaction type
-- Part of Congress Trading Module
-- 
-- Purpose: Support received transactions from scraped data
-- =====================================================

-- Drop existing constraint if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_type_check'
    ) THEN
        ALTER TABLE congress_trades 
        DROP CONSTRAINT congress_trades_type_check;
        
        RAISE NOTICE '✅ Dropped existing congress_trades_type_check constraint';
    ELSE
        RAISE NOTICE '⚠️  congress_trades_type_check constraint not found';
    END IF;
END $$;

-- Add new constraint that allows "Received" in addition to Purchase, Sale, Exchange
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'congress_trades_type_check'
    ) THEN
        ALTER TABLE congress_trades 
        ADD CONSTRAINT congress_trades_type_check 
        CHECK (type IN ('Purchase', 'Sale', 'Exchange', 'Received'));
        
        RAISE NOTICE '✅ Added congress_trades_type_check constraint (allows Purchase, Sale, Exchange, Received)';
    ELSE
        RAISE NOTICE '⚠️  congress_trades_type_check constraint already exists';
    END IF;
END $$;

-- Update comment
COMMENT ON COLUMN congress_trades.type IS 
  'Type of transaction: "Purchase", "Sale", "Exchange", or "Received"';

-- Verification
DO $$
DECLARE
    purchase_count INTEGER;
    sale_count INTEGER;
    exchange_count INTEGER;
    received_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO purchase_count FROM congress_trades WHERE type = 'Purchase';
    SELECT COUNT(*) INTO sale_count FROM congress_trades WHERE type = 'Sale';
    SELECT COUNT(*) INTO exchange_count FROM congress_trades WHERE type = 'Exchange';
    SELECT COUNT(*) INTO received_count FROM congress_trades WHERE type = 'Received';
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ Constraint update complete!';
    RAISE NOTICE '   Purchases: %', purchase_count;
    RAISE NOTICE '   Sales: %', sale_count;
    RAISE NOTICE '   Exchanges: %', exchange_count;
    RAISE NOTICE '   Received: %', received_count;
END $$;

