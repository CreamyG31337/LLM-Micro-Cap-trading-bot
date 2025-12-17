-- =====================================================
-- ADD PRODUCTION FLAG TO FUNDS
-- =====================================================
-- Marks funds as production vs test/development
-- Only production funds are included in automated backfill
-- =====================================================

-- Add is_production column to funds table
ALTER TABLE funds ADD COLUMN IF NOT EXISTS is_production BOOLEAN DEFAULT false;

-- Mark existing production funds
-- User specified: Project Chimera and RRSP Lance Webull
UPDATE funds 
SET is_production = true 
WHERE name IN ('Project Chimera', 'RRSP Lance Webull');

-- Add comment for documentation
COMMENT ON COLUMN funds.is_production IS 
  'Marks fund as production (true) vs test/development (false). Only production funds are included in automated backfill and scheduled jobs.';

-- Optional: Add index if querying by production status becomes common
CREATE INDEX IF NOT EXISTS idx_funds_is_production 
  ON funds(is_production) 
  WHERE is_production = true;

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show current production status
DO $$
DECLARE
    prod_count INTEGER;
    test_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO prod_count FROM funds WHERE is_production = true;
    SELECT COUNT(*) INTO test_count FROM funds WHERE is_production = false;
    
    RAISE NOTICE '✅ Production flag migration complete!';
    RAISE NOTICE '   Production funds: %', prod_count;
    RAISE NOTICE '   Test/Dev funds: %', test_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Production funds:';
    
    FOR r IN SELECT name FROM funds WHERE is_production = true ORDER BY name
    LOOP
        RAISE NOTICE '  - %', r.name;
    END LOOP;
END $$;
