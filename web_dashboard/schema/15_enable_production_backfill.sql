-- =====================================================
-- MARK FUNDS AS PRODUCTION TO ENABLE BACKFILL
-- =====================================================
-- This enables the automatic backfill system which will
-- populate all missing pre-converted currency values.
-- =====================================================

-- Mark your actual funds as production
UPDATE funds 
SET is_production = true 
WHERE name IN ('Project Chimera', 'RRSP Lance Webull');

-- Verify the update
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '✅ Production funds updated!';
    RAISE NOTICE '';
    RAISE NOTICE 'Production funds:';
    
    FOR r IN SELECT name, base_currency FROM funds WHERE is_production = true ORDER BY name
    LOOP
        RAISE NOTICE '  - % (base_currency: %)', r.name, r.base_currency;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '🔄 Next step: Restart the web dashboard';
    RAISE NOTICE '   The backfill job will automatically run on startup and populate';
    RAISE NOTICE '   all missing pre-converted currency values for historical data.';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ After backfill completes, you will see:';
    RAISE NOTICE '   "⚡ Using pre-converted base currency values (FAST PATH)"';
    RAISE NOTICE '   instead of the slow path warning.';
END $$;
