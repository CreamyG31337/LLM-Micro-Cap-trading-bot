-- =====================================================
-- ADD MARKET RELATIONSHIPS TABLE (GraphRAG/Relationships)
-- =====================================================
-- This table stores persistent relationships found by the AI.
-- Part of Level 2+ RAG upgrade: "Mapping" system for relationship tracking
-- 
-- Purpose: Store relationships between companies/tickers discovered in articles
-- Example: NVDA -> SUPPLIER -> TSM (NVIDIA relies on TSMC as supplier)
-- Example: GOOG -> COMPETITOR -> MSFT (Google competes with Microsoft)
-- 
-- Why separate table: One article might mention 5 different relationships.
-- Storing relationships in research_articles table would be messy.
-- =====================================================

CREATE TABLE IF NOT EXISTS market_relationships (
    id SERIAL PRIMARY KEY,
    
    -- Relationship definition
    source_ticker VARCHAR(20) NOT NULL,      -- e.g., "NVDA"
    target_ticker VARCHAR(20) NOT NULL,      -- e.g., "TSM"
    relationship_type VARCHAR(50) NOT NULL,   -- e.g., 'SUPPLIER', 'COMPETITOR', 'LITIGATION', 'MERGER', 'PARTNER', 'CUSTOMER'
    
    -- Metadata
    confidence_score FLOAT DEFAULT 0.0,       -- How sure is the AI? (0.0 to 1.0)
    detected_at TIMESTAMP DEFAULT NOW(),      -- When was this relationship detected?
    source_article_id UUID REFERENCES research_articles(id) ON DELETE SET NULL,  -- Which article found this?
    
    -- Prevent duplicate edges (We don't need 50 rows saying Apple needs TSMC)
    -- Same relationship from same source to same target should only exist once
    CONSTRAINT unique_relationship UNIQUE (source_ticker, target_ticker, relationship_type)
);

-- Add comments for documentation
COMMENT ON TABLE market_relationships IS 
  'Stores persistent relationships between companies/tickers discovered by AI analysis of articles. Part of GraphRAG/relationship mapping system.';

COMMENT ON COLUMN market_relationships.source_ticker IS 
  'Source company ticker (e.g., "NVDA" for NVIDIA)';

COMMENT ON COLUMN market_relationships.target_ticker IS 
  'Target company ticker (e.g., "TSM" for TSMC)';

COMMENT ON COLUMN market_relationships.relationship_type IS 
  'Type of relationship: SUPPLIER, COMPETITOR, LITIGATION, MERGER, PARTNER, CUSTOMER, etc.';

COMMENT ON COLUMN market_relationships.confidence_score IS 
  'AI confidence in this relationship (0.0 to 1.0). Higher = more certain.';

COMMENT ON COLUMN market_relationships.source_article_id IS 
  'Reference to the research_articles entry where this relationship was discovered. NULL if relationship was inferred or from external source.';

-- Indexes for graph traversals
-- Find all relationships where a ticker is the source (e.g., "Find all suppliers of NVDA")
CREATE INDEX IF NOT EXISTS idx_relationships_source ON market_relationships(source_ticker);

-- Find all relationships where a ticker is the target (e.g., "Who supplies to TSMC?")
CREATE INDEX IF NOT EXISTS idx_relationships_target ON market_relationships(target_ticker);

-- Find relationships by type (e.g., "Find all SUPPLIER relationships")
CREATE INDEX IF NOT EXISTS idx_relationships_type ON market_relationships(relationship_type);

-- Find relationships by confidence (for filtering low-confidence edges)
CREATE INDEX IF NOT EXISTS idx_relationships_confidence ON market_relationships(confidence_score DESC);

-- Find relationships by article (for tracking what relationships came from which article)
CREATE INDEX IF NOT EXISTS idx_relationships_article ON market_relationships(source_article_id);

-- Composite index for common queries: "Find all relationships for a ticker, ordered by confidence"
CREATE INDEX IF NOT EXISTS idx_relationships_source_confidence ON market_relationships(source_ticker, confidence_score DESC);

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show current relationship distribution
DO $$
DECLARE
    total_count INTEGER;
    r RECORD;
BEGIN
    SELECT COUNT(*) INTO total_count FROM market_relationships;
    
    RAISE NOTICE '✅ Market relationships table created!';
    RAISE NOTICE '   Total relationships: %', total_count;
    RAISE NOTICE '';
    
    IF total_count > 0 THEN
        RAISE NOTICE 'Relationship type distribution:';
        
        FOR r IN 
            SELECT relationship_type, COUNT(*) as count 
            FROM market_relationships 
            GROUP BY relationship_type 
            ORDER BY count DESC
        LOOP
            RAISE NOTICE '  - %: % relationships', r.relationship_type, r.count;
        END LOOP;
        
        RAISE NOTICE '';
        RAISE NOTICE 'Top relationships by confidence:';
        
        FOR r IN 
            SELECT source_ticker, target_ticker, relationship_type, confidence_score
            FROM market_relationships 
            ORDER BY confidence_score DESC 
            LIMIT 5
        LOOP
            RAISE NOTICE '  - % -> % (%): %.2f confidence', 
                r.source_ticker, r.target_ticker, r.relationship_type, r.confidence_score;
        END LOOP;
    ELSE
        RAISE NOTICE '   No relationships stored yet.';
        RAISE NOTICE '   Relationships will be populated as articles are analyzed.';
    END IF;
END $$;

