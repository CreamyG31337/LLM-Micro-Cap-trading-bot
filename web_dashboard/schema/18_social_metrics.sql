-- =====================================================
-- CREATE SOCIAL METRICS TABLE (Postgres)
-- =====================================================
-- Stores social sentiment data from StockTwits and Reddit
-- Part of Phase 2: Social Sentiment Tracking
-- 
-- Purpose: Track retail hype and sentiment for watched tickers
-- =====================================================

CREATE TABLE IF NOT EXISTS social_metrics (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
    volume INTEGER DEFAULT 0,          -- Post count filtered for last 60 minutes
    bull_bear_ratio FLOAT DEFAULT 0.0, -- Crucial for StockTwits: ratio of Bullish to Bearish posts
    sentiment_label VARCHAR(20),       -- 'EUPHORIC', 'BULLISH', 'NEUTRAL', 'BEARISH', 'FEARFUL'
    sentiment_score FLOAT,             -- -2.0 to 2.0 (mapped from label in Python)
    raw_data JSONB,                    -- Top 3 posts/comments for context
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE social_metrics IS 
  'Social sentiment metrics from StockTwits and Reddit for watched tickers. Updated every 30 minutes.';

COMMENT ON COLUMN social_metrics.volume IS 
  'Post count filtered for last 60 minutes (StockTwits) or last 24 hours (Reddit)';

COMMENT ON COLUMN social_metrics.bull_bear_ratio IS 
  'StockTwits-specific: Ratio of Bullish to Bearish posts (0.0 to 1.0). 0.0 = no labels, 0.5 = equal, 1.0 = all bullish.';

COMMENT ON COLUMN social_metrics.sentiment_label IS 
  'AI-categorized sentiment label: EUPHORIC, BULLISH, NEUTRAL, BEARISH, FEARFUL';

COMMENT ON COLUMN social_metrics.sentiment_score IS 
  'Numeric sentiment score mapped from label: EUPHORIC=2.0, BULLISH=1.0, NEUTRAL=0.0, BEARISH=-1.0, FEARFUL=-2.0';

COMMENT ON COLUMN social_metrics.raw_data IS 
  'Top 3 posts/comments stored as JSONB for context and debugging';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_social_ticker_time ON social_metrics(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_platform ON social_metrics(platform);
CREATE INDEX IF NOT EXISTS idx_social_created_at ON social_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_ticker_platform ON social_metrics(ticker, platform);

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    total_count INTEGER;
    stocktwits_count INTEGER;
    reddit_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM social_metrics;
    SELECT COUNT(*) INTO stocktwits_count FROM social_metrics WHERE platform = 'stocktwits';
    SELECT COUNT(*) INTO reddit_count FROM social_metrics WHERE platform = 'reddit';
    
    RAISE NOTICE '✅ Social metrics table created!';
    RAISE NOTICE '   Total metrics: %', total_count;
    RAISE NOTICE '   StockTwits metrics: %', stocktwits_count;
    RAISE NOTICE '   Reddit metrics: %', reddit_count;
    RAISE NOTICE '';
    
    IF total_count > 0 THEN
        RAISE NOTICE 'Recent metrics (last 10):';
        
        FOR r IN 
            SELECT ticker, platform, volume, sentiment_label, sentiment_score, created_at
            FROM social_metrics 
            ORDER BY created_at DESC 
            LIMIT 10
        LOOP
            RAISE NOTICE '  % | % | Vol: % | % (%.1f) | %', 
                r.ticker, r.platform, r.volume, r.sentiment_label, 
                COALESCE(r.sentiment_score, 0.0), r.created_at;
        END LOOP;
    ELSE
        RAISE NOTICE '   No metrics yet.';
        RAISE NOTICE '   Metrics will be populated when social_sentiment job runs.';
    END IF;
END $$;

