-- Research Articles Schema
-- Stores scraped articles from websites for AI-powered research
-- Uses pgvector for semantic search capabilities

-- Ensure vector extension is enabled (run this first if not already done)
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS research_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core Identifiers
    ticker VARCHAR(20),             -- e.g. "NVDA"
    sector VARCHAR(100),           -- e.g. "Technology"
    article_type VARCHAR(50),      -- 'ticker_news', 'market_news', 'earnings'
    
    -- Content
    title TEXT NOT NULL,
    url TEXT UNIQUE,                -- Prevent duplicate scrapes
    summary TEXT,                   -- AI-generated summary (keep it short)
    content TEXT,                   -- Full raw text (for context if needed)
    source VARCHAR(100),            -- e.g. "Yahoo Finance", "Reuters"
    
    -- Metadata & Scoring
    published_at TIMESTAMP,         -- When the article was written
    fetched_at TIMESTAMP DEFAULT NOW(), -- When we scraped it
    relevance_score DECIMAL(3,2),   -- 0.00 to 1.00
    
    -- The AI Brain (768 dimensions is standard for nomic-embed-text)
    embedding vector(768)
);

-- Indexes for Speed
CREATE INDEX IF NOT EXISTS idx_research_ticker ON research_articles(ticker);
CREATE INDEX IF NOT EXISTS idx_research_fetched ON research_articles(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_type ON research_articles(article_type);

-- Index for vector similarity search (future use)
-- CREATE INDEX IF NOT EXISTS idx_research_embedding ON research_articles 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

