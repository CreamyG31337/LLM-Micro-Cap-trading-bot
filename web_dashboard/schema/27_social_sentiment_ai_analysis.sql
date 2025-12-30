-- =====================================================
-- SOCIAL SENTIMENT AI ANALYSIS TABLES (Postgres Research DB)
-- =====================================================
-- Stores AI analysis results for social sentiment data
-- Part of Phase 2: Social Sentiment Tracking with AI Analysis
--
-- Purpose: Enable comprehensive AI analysis of social sentiment
-- while keeping large text content separate from Supabase
-- =====================================================

-- =====================================================
-- SOCIAL SENTIMENT ANALYSIS TABLE
-- =====================================================
-- Stores detailed AI analysis results for sentiment sessions
-- Similar to congress_trades_analysis but for social sentiment
-- =====================================================

CREATE TABLE IF NOT EXISTS social_sentiment_analysis (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,       -- FK to Supabase sentiment_sessions
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),

    -- AI analysis results
    sentiment_score DECIMAL(3,2),      -- -2.0 to 2.0 (EUPHORIC to FEARFUL)
    confidence_score DECIMAL(3,2),     -- 0.0 to 1.0
    sentiment_label VARCHAR(20),       -- EUPHORIC, BULLISH, NEUTRAL, BEARISH, FEARFUL

    -- AI-generated content
    summary TEXT,                      -- AI summary of all posts in session
    key_themes TEXT[],                 -- Main topics discussed
    reasoning TEXT,                    -- Detailed AI reasoning for the analysis

    -- Metadata
    model_used VARCHAR(100) DEFAULT 'granite3.1:8b',
    analysis_version INTEGER DEFAULT 1,
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for social_sentiment_analysis table
COMMENT ON TABLE social_sentiment_analysis IS
  'AI analysis results for social sentiment sessions, stored in research DB to save Supabase costs';

COMMENT ON COLUMN social_sentiment_analysis.session_id IS
  'Foreign key to sentiment_sessions table in Supabase';

COMMENT ON COLUMN social_sentiment_analysis.sentiment_score IS
  'AI-calculated sentiment score from -2.0 (FEARFUL) to 2.0 (EUPHORIC)';

COMMENT ON COLUMN social_sentiment_analysis.confidence_score IS
  'AI confidence in the analysis (0.0 to 1.0)';

COMMENT ON COLUMN social_sentiment_analysis.sentiment_label IS
  'Categorized sentiment label based on score';

COMMENT ON COLUMN social_sentiment_analysis.summary IS
  'AI-generated summary of the sentiment session';

COMMENT ON COLUMN social_sentiment_analysis.key_themes IS
  'Array of main topics/themes identified by AI';

COMMENT ON COLUMN social_sentiment_analysis.reasoning IS
  'Detailed AI reasoning explaining the sentiment analysis';

COMMENT ON COLUMN social_sentiment_analysis.model_used IS
  'Ollama model used for the analysis';

COMMENT ON COLUMN social_sentiment_analysis.analysis_version IS
  'Version of the analysis pipeline/prompts used';

-- Indexes for social_sentiment_analysis
CREATE INDEX IF NOT EXISTS idx_social_analysis_session ON social_sentiment_analysis(session_id);
CREATE INDEX IF NOT EXISTS idx_social_analysis_ticker ON social_sentiment_analysis(ticker);
CREATE INDEX IF NOT EXISTS idx_social_analysis_platform ON social_sentiment_analysis(platform);
CREATE INDEX IF NOT EXISTS idx_social_analysis_sentiment ON social_sentiment_analysis(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_social_analysis_confidence ON social_sentiment_analysis(confidence_score);
CREATE INDEX IF NOT EXISTS idx_social_analysis_analyzed_at ON social_sentiment_analysis(analyzed_at DESC);

-- =====================================================
-- EXTRACTED TICKERS TABLE
-- =====================================================
-- Stores AI-validated tickers extracted from social posts
-- Includes context and confidence scores
-- =====================================================

CREATE TABLE IF NOT EXISTS extracted_tickers (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES social_sentiment_analysis(id),
    ticker VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2),            -- AI confidence in extraction (0.0-1.0)
    context TEXT,                       -- Sentence/context where ticker was found
    is_primary BOOLEAN DEFAULT FALSE,   -- Main ticker of the session
    company_name VARCHAR(200),          -- Resolved company name
    sector VARCHAR(100),                -- Company sector if available
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for extracted_tickers table
COMMENT ON TABLE extracted_tickers IS
  'AI-validated tickers extracted from social posts with context and confidence';

COMMENT ON COLUMN extracted_tickers.analysis_id IS
  'Foreign key to social_sentiment_analysis table';

COMMENT ON COLUMN extracted_tickers.confidence IS
  'AI confidence score for the ticker extraction (0.0-1.0)';

COMMENT ON COLUMN extracted_tickers.context IS
  'The sentence or context where the ticker was mentioned';

COMMENT ON COLUMN extracted_tickers.is_primary IS
  'Flag indicating if this is the primary/main ticker of the analysis session';

COMMENT ON COLUMN extracted_tickers.company_name IS
  'Resolved company name for the ticker';

COMMENT ON COLUMN extracted_tickers.sector IS
  'Company sector/industry classification';

-- Indexes for extracted_tickers
CREATE INDEX IF NOT EXISTS idx_extracted_tickers_analysis ON extracted_tickers(analysis_id);
CREATE INDEX IF NOT EXISTS idx_extracted_tickers_ticker ON extracted_tickers(ticker);
CREATE INDEX IF NOT EXISTS idx_extracted_tickers_confidence ON extracted_tickers(confidence);
CREATE INDEX IF NOT EXISTS idx_extracted_tickers_primary ON extracted_tickers(is_primary);

-- =====================================================
-- POST SUMMARIES TABLE
-- =====================================================
-- Stores AI-generated summaries for individual posts
-- Enables detailed post-level analysis
-- =====================================================

CREATE TABLE IF NOT EXISTS post_summaries (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,           -- FK to Supabase social_posts
    summary TEXT NOT NULL,              -- AI-generated summary
    key_points TEXT[],                  -- Bullet points of main ideas
    sentiment_impact DECIMAL(3,2),      -- Contribution to overall sentiment (-2.0 to 2.0)
    summarized_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for post_summaries table
COMMENT ON TABLE post_summaries IS
  'AI-generated summaries for individual social posts';

COMMENT ON COLUMN post_summaries.post_id IS
  'Foreign key to social_posts table in Supabase';

COMMENT ON COLUMN post_summaries.summary IS
  'AI-generated summary of the individual post';

COMMENT ON COLUMN post_summaries.key_points IS
  'Array of key points extracted from the post';

COMMENT ON COLUMN post_summaries.sentiment_impact IS
  'Estimated sentiment impact of this post on the overall session (-2.0 to 2.0)';

-- Indexes for post_summaries
CREATE INDEX IF NOT EXISTS idx_post_summaries_post ON post_summaries(post_id);
CREATE INDEX IF NOT EXISTS idx_post_summaries_impact ON post_summaries(sentiment_impact);
CREATE INDEX IF NOT EXISTS idx_post_summaries_summarized_at ON post_summaries(summarized_at DESC);

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    social_metrics_count INTEGER;
    social_posts_count INTEGER;
    sentiment_sessions_count INTEGER;
    analysis_count INTEGER;
    tickers_count INTEGER;
    summaries_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO social_metrics_count FROM social_metrics;
    SELECT COUNT(*) INTO social_posts_count FROM social_posts;
    SELECT COUNT(*) INTO sentiment_sessions_count FROM sentiment_sessions;
    SELECT COUNT(*) INTO analysis_count FROM social_sentiment_analysis;
    SELECT COUNT(*) INTO tickers_count FROM extracted_tickers;
    SELECT COUNT(*) INTO summaries_count FROM post_summaries;

    RAISE NOTICE '✅ Social sentiment AI analysis schema created!';
    RAISE NOTICE '   social_metrics: %', social_metrics_count;
    RAISE NOTICE '   social_posts: %', social_posts_count;
    RAISE NOTICE '   sentiment_sessions: %', sentiment_sessions_count;
    RAISE NOTICE '   social_sentiment_analysis: %', analysis_count;
    RAISE NOTICE '   extracted_tickers: %', tickers_count;
    RAISE NOTICE '   post_summaries: %', summaries_count;
    RAISE NOTICE '';

    IF social_metrics_count > 0 THEN
        RAISE NOTICE 'Recent social metrics (last 5):';
        FOR r IN
            SELECT ticker, platform, volume, sentiment_label, sentiment_score,
                   has_ai_analysis, post_count, created_at
            FROM social_metrics
            ORDER BY created_at DESC
            LIMIT 5
        LOOP
            RAISE NOTICE '  % | % | Vol: % | % (%.1f) | AI: % | Posts: % | %',
                r.ticker, r.platform, r.volume, r.sentiment_label,
                COALESCE(r.sentiment_score, 0.0), r.has_ai_analysis,
                r.post_count, r.created_at;
        END LOOP;
    ELSE
        RAISE NOTICE '   No social metrics yet.';
        RAISE NOTICE '   Data will be populated when social sentiment collection runs.';
    END IF;

    IF analysis_count > 0 THEN
        RAISE NOTICE 'Recent AI analyses (last 3):';
        FOR r IN
            SELECT ticker, platform, sentiment_label, confidence_score, analyzed_at
            FROM social_sentiment_analysis
            ORDER BY analyzed_at DESC
            LIMIT 3
        LOOP
            RAISE NOTICE '  % | % | % | Conf: %.1f | %',
                r.ticker, r.platform, r.sentiment_label,
                COALESCE(r.confidence_score, 0.0), r.analyzed_at;
        END LOOP;
    ELSE
        RAISE NOTICE '   No AI analyses yet.';
        RAISE NOTICE '   Analyses will be created when the AI analysis job runs.';
    END IF;
END $$;