-- =====================================================
-- CREATE WATCHED TICKERS TABLE (Supabase)
-- =====================================================
-- Tracks tickers we want to monitor for social sentiment
-- Pre-populated from trade_log (all tickers ever traded)
-- 
-- Purpose: Centralized watchlist for social sentiment tracking
-- Logic: "If it's good enough for my RRSP, it's good enough for other funds"
-- =====================================================

-- Create watched_tickers table
CREATE TABLE IF NOT EXISTS watched_tickers (
    ticker VARCHAR(20) PRIMARY KEY,
    priority_tier VARCHAR(10) DEFAULT 'B' CHECK (priority_tier IN ('A', 'B', 'C')),
    is_active BOOLEAN DEFAULT TRUE,
    source VARCHAR(50), -- 'TRADELOG', 'MANUAL', 'REDDIT_DISCOVERY'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comment for documentation
COMMENT ON TABLE watched_tickers IS 
  'Centralized watchlist of tickers to monitor for social sentiment. Pre-populated from trade_log.';

COMMENT ON COLUMN watched_tickers.priority_tier IS 
  'Priority level: A (Active/High), B (Standard/Default), C (Passive/Low)';

COMMENT ON COLUMN watched_tickers.source IS 
  'Origin of ticker: TRADELOG (from trade history), MANUAL (manually added), REDDIT_DISCOVERY (found via Reddit)';

-- Create index for active tickers (most common query)
CREATE INDEX IF NOT EXISTS idx_watched_tickers_active ON watched_tickers(is_active) WHERE is_active = TRUE;

-- Create index for priority tier
CREATE INDEX IF NOT EXISTS idx_watched_tickers_priority ON watched_tickers(priority_tier);

-- =====================================================
-- PRE-POPULATION: Extract distinct tickers from trade_log
-- =====================================================
-- Logic: If we've traded it before, we should monitor it
-- This ensures all tickers from all funds are included

INSERT INTO watched_tickers (ticker, priority_tier, is_active, source)
SELECT DISTINCT 
    ticker,
    'B' as priority_tier,  -- Default to standard priority
    TRUE as is_active,
    'TRADELOG' as source
FROM trade_log
WHERE ticker IS NOT NULL
  AND ticker != ''
  AND ticker NOT IN (SELECT ticker FROM watched_tickers)  -- Avoid duplicates
ON CONFLICT (ticker) DO NOTHING;  -- Skip if already exists

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    total_count INTEGER;
    active_count INTEGER;
    tradelog_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM watched_tickers;
    SELECT COUNT(*) INTO active_count FROM watched_tickers WHERE is_active = TRUE;
    SELECT COUNT(*) INTO tradelog_count FROM watched_tickers WHERE source = 'TRADELOG';
    
    RAISE NOTICE '✅ Watched tickers table created and populated!';
    RAISE NOTICE '   Total tickers: %', total_count;
    RAISE NOTICE '   Active tickers: %', active_count;
    RAISE NOTICE '   From trade_log: %', tradelog_count;
    RAISE NOTICE '';
    
    IF total_count > 0 THEN
        RAISE NOTICE 'Priority tier distribution:';
        
        FOR r IN 
            SELECT priority_tier, COUNT(*) as count 
            FROM watched_tickers 
            GROUP BY priority_tier 
            ORDER BY priority_tier
        LOOP
            RAISE NOTICE '  - Tier %: % tickers', r.priority_tier, r.count;
        END LOOP;
        
        RAISE NOTICE '';
        RAISE NOTICE 'Source distribution:';
        
        FOR r IN 
            SELECT source, COUNT(*) as count 
            FROM watched_tickers 
            GROUP BY source 
            ORDER BY count DESC
        LOOP
            RAISE NOTICE '  - %: % tickers', r.source, r.count;
        END LOOP;
    ELSE
        RAISE NOTICE '   No tickers found in trade_log.';
        RAISE NOTICE '   Table is ready for manual additions.';
    END IF;
END $$;

