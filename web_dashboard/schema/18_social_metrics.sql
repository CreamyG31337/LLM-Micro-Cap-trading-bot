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
    raw_data JSONB,                    -- Top 3 posts/comments for context (deprecated - use social_posts)
    -- Enhanced fields for AI analysis
    basic_sentiment_score DECIMAL(3,2), -- Basic sentiment score before AI analysis
    has_ai_analysis BOOLEAN DEFAULT FALSE, -- Whether AI analysis has been performed
    analysis_session_id INTEGER,       -- FK to sentiment_sessions table
    raw_posts JSONB[],                 -- Array of complete post objects
    post_count INTEGER DEFAULT 0,      -- Total posts analyzed
    engagement_score FLOAT DEFAULT 0.0, -- Weighted engagement metric
    data_quality_score FLOAT DEFAULT 0.0, -- Confidence score for data completeness
    collection_metadata JSONB,         -- Debug info (API response times, error counts)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE social_metrics IS 
  'Social sentiment metrics from StockTwits and Reddit for watched tickers. Updated every 60 minutes (1 hour).';

COMMENT ON COLUMN social_metrics.volume IS 
  'Post count filtered for last 60 minutes (StockTwits) or last 24 hours (Reddit)';

COMMENT ON COLUMN social_metrics.bull_bear_ratio IS 
  'StockTwits-specific: Ratio of Bullish to Bearish posts (0.0 to 1.0). 0.0 = no labels, 0.5 = equal, 1.0 = all bullish.';

COMMENT ON COLUMN social_metrics.sentiment_label IS 
  'AI-categorized sentiment label: EUPHORIC, BULLISH, NEUTRAL, BEARISH, FEARFUL';

COMMENT ON COLUMN social_metrics.sentiment_score IS 
  'Numeric sentiment score mapped from label: EUPHORIC=2.0, BULLISH=1.0, NEUTRAL=0.0, BEARISH=-1.0, FEARFUL=-2.0';

COMMENT ON COLUMN social_metrics.raw_data IS 
  'Top 3 posts/comments stored as JSONB for context and debugging (deprecated - use social_posts table)';

COMMENT ON COLUMN social_metrics.basic_sentiment_score IS 
  'Basic sentiment score calculated from platform APIs before AI analysis';

COMMENT ON COLUMN social_metrics.has_ai_analysis IS 
  'Flag indicating whether comprehensive AI analysis has been performed';

COMMENT ON COLUMN social_metrics.analysis_session_id IS 
  'Foreign key to sentiment_sessions table for grouping related posts';

COMMENT ON COLUMN social_metrics.raw_posts IS 
  'Array of complete post objects with full metadata for AI analysis';

COMMENT ON COLUMN social_metrics.post_count IS 
  'Total number of posts analyzed (beyond just top 3)';

COMMENT ON COLUMN social_metrics.engagement_score IS 
  'Weighted engagement metric combining upvotes, comments, and other factors';

COMMENT ON COLUMN social_metrics.data_quality_score IS 
  'Confidence score (0.0-1.0) for data completeness and reliability';

COMMENT ON COLUMN social_metrics.collection_metadata IS 
  'Debug metadata including API response times, error counts, and collection stats';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_social_ticker_time ON social_metrics(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_platform ON social_metrics(platform);
CREATE INDEX IF NOT EXISTS idx_social_created_at ON social_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_ticker_platform ON social_metrics(ticker, platform);
CREATE INDEX IF NOT EXISTS idx_social_engagement ON social_metrics(engagement_score);
CREATE INDEX IF NOT EXISTS idx_social_quality ON social_metrics(data_quality_score);
CREATE INDEX IF NOT EXISTS idx_social_session ON social_metrics(analysis_session_id);

-- =====================================================
-- SOCIAL POSTS TABLE
-- =====================================================
-- Stores individual posts extracted from social media platforms
-- Enables detailed AI analysis and ticker extraction
-- =====================================================

CREATE TABLE IF NOT EXISTS social_posts (
    id SERIAL PRIMARY KEY,
    metric_id INTEGER REFERENCES social_metrics(id),
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
    post_id VARCHAR(100),              -- Platform-specific unique identifier
    content TEXT NOT NULL,             -- Full post content
    author VARCHAR(100),               -- Username/handle of poster
    posted_at TIMESTAMPTZ,             -- Original post timestamp
    engagement_score INTEGER DEFAULT 0, -- upvotes + comments (weighted)
    url TEXT,                          -- Direct link to original post
    extracted_tickers TEXT[],          -- Basic regex-extracted tickers
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for social_posts table
COMMENT ON TABLE social_posts IS 
  'Individual social media posts extracted from raw_data for detailed analysis';

COMMENT ON COLUMN social_posts.metric_id IS 
  'Foreign key to social_metrics table';

COMMENT ON COLUMN social_posts.post_id IS 
  'Platform-specific unique identifier for the post';

COMMENT ON COLUMN social_posts.engagement_score IS 
  'Weighted engagement score (upvotes + comments * weight)';

COMMENT ON COLUMN social_posts.extracted_tickers IS 
  'Array of tickers extracted via basic regex patterns before AI validation';

-- Indexes for social_posts
CREATE INDEX IF NOT EXISTS idx_social_posts_metric ON social_posts(metric_id);
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_posted_at ON social_posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_posts_tickers ON social_posts USING GIN(extracted_tickers);

-- =====================================================
-- SENTIMENT SESSIONS TABLE
-- =====================================================
-- Groups related posts into analysis sessions (similar to congress trades)
-- Enables comprehensive AI analysis of sentiment patterns
-- =====================================================

CREATE TABLE IF NOT EXISTS sentiment_sessions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
    session_start TIMESTAMPTZ NOT NULL,
    session_end TIMESTAMPTZ NOT NULL,
    post_count INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    needs_ai_analysis BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for sentiment_sessions table
COMMENT ON TABLE sentiment_sessions IS 
  'Groups related social posts into analysis sessions for comprehensive AI evaluation';

COMMENT ON COLUMN sentiment_sessions.session_start IS 
  'Start timestamp of the sentiment session window';

COMMENT ON COLUMN sentiment_sessions.session_end IS 
  'End timestamp of the sentiment session window';

COMMENT ON COLUMN sentiment_sessions.needs_ai_analysis IS 
  'Flag indicating whether this session requires AI analysis';

-- Indexes for sentiment_sessions
CREATE INDEX IF NOT EXISTS idx_sentiment_sessions_ticker ON sentiment_sessions(ticker);
CREATE INDEX IF NOT EXISTS idx_sentiment_sessions_platform ON sentiment_sessions(platform);
CREATE INDEX IF NOT EXISTS idx_sentiment_sessions_time ON sentiment_sessions(session_start, session_end);
CREATE INDEX IF NOT EXISTS idx_sentiment_sessions_needs_analysis ON sentiment_sessions(needs_ai_analysis);

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

