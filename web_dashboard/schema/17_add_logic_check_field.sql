-- =====================================================
-- ADD LOGIC_CHECK FIELD TO RESEARCH_ARTICLES
-- =====================================================
-- Adds logic_check field for categorical classification of article quality
-- Part of GraphRAG/Relationship extraction system
-- 
-- Purpose: Categorize articles as DATA_BACKED, HYPE_DETECTED, or NEUTRAL
-- This field is used to determine initial confidence scores for extracted relationships
-- 
-- Note: fact_check (TEXT) already exists and stores detailed analysis text.
-- logic_check (VARCHAR) is a separate categorical field for confidence scoring.
-- =====================================================

-- Add logic_check column (VARCHAR for categorical classification)
ALTER TABLE research_articles ADD COLUMN IF NOT EXISTS logic_check VARCHAR(20);

-- Add comment for documentation
COMMENT ON COLUMN research_articles.logic_check IS 
  'Categorical classification of article quality: DATA_BACKED (hard numbers/facts), HYPE_DETECTED (clickbait/rumors), or NEUTRAL (standard reporting). Used for relationship confidence scoring.';

-- Add index for fast filtering by quality (important for relationship extraction)
CREATE INDEX IF NOT EXISTS idx_research_logic_check ON research_articles(logic_check);

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show current logic_check distribution
DO $$
DECLARE
    total_count INTEGER;
    with_logic_check_count INTEGER;
    without_logic_check_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM research_articles;
    SELECT COUNT(*) INTO with_logic_check_count FROM research_articles WHERE logic_check IS NOT NULL;
    SELECT COUNT(*) INTO without_logic_check_count FROM research_articles WHERE logic_check IS NULL;
    
    RAISE NOTICE '✅ Logic check field migration complete!';
    RAISE NOTICE '   Total articles: %', total_count;
    RAISE NOTICE '   Articles with logic_check: %', with_logic_check_count;
    RAISE NOTICE '   Articles without logic_check (old data): %', without_logic_check_count;
    RAISE NOTICE '';
    
    IF with_logic_check_count > 0 THEN
        RAISE NOTICE 'Logic check distribution:';
        
        FOR r IN 
            SELECT logic_check, COUNT(*) as count 
            FROM research_articles 
            WHERE logic_check IS NOT NULL 
            GROUP BY logic_check 
            ORDER BY count DESC
        LOOP
            RAISE NOTICE '  - %: % articles', r.logic_check, r.count;
        END LOOP;
    ELSE
        RAISE NOTICE '   No articles with logic_check yet.';
        RAISE NOTICE '   Logic check will be populated as new articles are analyzed.';
    END IF;
END $$;

