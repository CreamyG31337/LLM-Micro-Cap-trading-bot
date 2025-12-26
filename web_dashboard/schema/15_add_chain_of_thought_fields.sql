-- =====================================================
-- ADD CHAIN OF THOUGHT FIELDS TO RESEARCH_ARTICLES
-- =====================================================
-- Adds fields for Chain of Thought analysis and sentiment categorization
-- Part of Level 2 RAG upgrade: "Librarian" → "Analyst"
-- 
-- New fields:
--   - claims: JSONB array of specific claims with numbers/dates
--   - fact_check: TEXT with simple fact-checking analysis
--   - conclusion: TEXT with net impact on ticker(s)
--   - sentiment: VARCHAR(20) with sentiment category
-- =====================================================

-- Add claims column (JSONB array for structured data)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS claims JSONB;

-- Add fact_check column (TEXT for fact-checking analysis)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS fact_check TEXT;

-- Add conclusion column (TEXT for net impact analysis)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS conclusion TEXT;

-- Add sentiment column (VARCHAR for sentiment category - human-readable label)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20);

-- Add sentiment_score column (FLOAT for numeric calculations - avoids CASE WHEN in queries)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;

-- Add comments for documentation
COMMENT ON COLUMN research_articles.claims IS 
  'JSONB array of specific claims extracted from article (numbers, dates, percentages, causal claims). Part of Chain of Thought analysis.';

COMMENT ON COLUMN research_articles.fact_check IS 
  'Simple fact-checking analysis to filter garbage/clickbait. Part of Chain of Thought Step 2.';

COMMENT ON COLUMN research_articles.conclusion IS 
  'Net impact on stock ticker(s) with specific implications. Part of Chain of Thought Step 3.';

COMMENT ON COLUMN research_articles.sentiment IS 
  'Sentiment category: VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, VERY_BEARISH. Human-readable label for display.';

COMMENT ON COLUMN research_articles.sentiment_score IS 
  'Numeric sentiment score for calculations: VERY_BULLISH=2.0, BULLISH=1.0, NEUTRAL=0.0, BEARISH=-1.0, VERY_BEARISH=-2.0. Use for averages and aggregations.';

-- Add index for fast filtering by sentiment (important for tier 2 analysis)
CREATE INDEX IF NOT EXISTS idx_research_sentiment ON research_articles(sentiment);

-- Add index for sentiment_score (for sorting and aggregations)
CREATE INDEX IF NOT EXISTS idx_research_sentiment_score ON research_articles(sentiment_score);

-- Add index for claims (GIN index for JSONB queries)
CREATE INDEX IF NOT EXISTS idx_research_claims ON research_articles USING GIN (claims);

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show current sentiment distribution
DO $$
DECLARE
    total_count INTEGER;
    with_sentiment_count INTEGER;
    without_sentiment_count INTEGER;
    avg_score FLOAT;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM research_articles;
    SELECT COUNT(*) INTO with_sentiment_count FROM research_articles WHERE sentiment IS NOT NULL;
    SELECT COUNT(*) INTO without_sentiment_count FROM research_articles WHERE sentiment IS NULL;
    SELECT AVG(sentiment_score) INTO avg_score FROM research_articles WHERE sentiment_score IS NOT NULL;
    
    RAISE NOTICE '✅ Chain of Thought fields migration complete!';
    RAISE NOTICE '   Total articles: %', total_count;
    RAISE NOTICE '   Articles with sentiment: %', with_sentiment_count;
    RAISE NOTICE '   Articles without sentiment (old data): %', without_sentiment_count;
    IF avg_score IS NOT NULL THEN
        RAISE NOTICE '   Average sentiment score: %.2f', avg_score;
    END IF;
    RAISE NOTICE '';
    RAISE NOTICE 'Sentiment distribution:';
    
    FOR r IN 
        SELECT sentiment, COUNT(*) as count 
        FROM research_articles 
        WHERE sentiment IS NOT NULL 
        GROUP BY sentiment 
        ORDER BY 
            CASE sentiment
                WHEN 'VERY_BULLISH' THEN 1
                WHEN 'BULLISH' THEN 2
                WHEN 'NEUTRAL' THEN 3
                WHEN 'BEARISH' THEN 4
                WHEN 'VERY_BEARISH' THEN 5
                ELSE 6
            END
    LOOP
        RAISE NOTICE '  - %: % articles', r.sentiment, r.count;
    END LOOP;
END $$;

