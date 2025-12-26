-- =====================================================
-- ADD FUND COLUMN TO RESEARCH_ARTICLES
-- =====================================================
-- Adds fund column to support fund-specific research materials
-- Purpose: Tag uploaded research reports and fund-specific documents
-- General market news (e.g., NVIDIA news) should remain NULL
-- Only fund-specific materials (uploaded reports) should have a fund value
-- =====================================================

-- Add fund column (nullable - NULL for general market news)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS fund VARCHAR(100);

-- Add comment for documentation
COMMENT ON COLUMN research_articles.fund IS 
  'Fund name for fund-specific research materials (e.g., uploaded research reports prepared for a specific fund). 
   NULL for general market news/articles that apply to all funds. 
   Purpose: Tag fund-specific research reports prepared for a specific fund. 
   Note: A stock (e.g., NVDA) may exist in multiple funds, but fund-specific research documents should be tagged with the fund they were created for.';

-- Add index for fast filtering by fund
CREATE INDEX IF NOT EXISTS idx_research_fund ON research_articles(fund);

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show current fund distribution
DO $$
DECLARE
    total_count INTEGER;
    with_fund_count INTEGER;
    without_fund_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM research_articles;
    SELECT COUNT(*) INTO with_fund_count FROM research_articles WHERE fund IS NOT NULL;
    SELECT COUNT(*) INTO without_fund_count FROM research_articles WHERE fund IS NULL;
    
    RAISE NOTICE '✅ Fund column migration complete!';
    RAISE NOTICE '   Total articles: %', total_count;
    RAISE NOTICE '   Articles with fund: %', with_fund_count;
    RAISE NOTICE '   Articles without fund (general): %', without_fund_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Fund distribution:';
    
    FOR r IN 
        SELECT fund, COUNT(*) as count 
        FROM research_articles 
        WHERE fund IS NOT NULL 
        GROUP BY fund 
        ORDER BY count DESC
    LOOP
        RAISE NOTICE '  - %: % articles', r.fund, r.count;
    END LOOP;
END $$;

