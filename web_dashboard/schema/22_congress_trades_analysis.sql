-- Congress Trades AI Analysis Results
-- Stores AI conflict of interest analysis for congressional trades
-- Stored in RESEARCH_DATABASE (separate Postgres) to save Supabase storage costs

CREATE TABLE IF NOT EXISTS congress_trades_analysis (
    id SERIAL PRIMARY KEY,
    
    -- Foreign key to the trade being analyzed (from Supabase congress_trades table)
    trade_id INTEGER NOT NULL,
    
    -- Analysis results
    conflict_score DECIMAL(3,2) CHECK (conflict_score >= 0 AND conflict_score <= 1),
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    reasoning TEXT,
    
    -- Analysis metadata
    model_used VARCHAR(100) NOT NULL DEFAULT 'granite3.3:8b',
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Track which version of the prompt/logic was used (for A/B testing)
    analysis_version INTEGER DEFAULT 1,
    
    -- Ensure we don't duplicate analyses
    CONSTRAINT congress_trades_analysis_unique_trade_model_version 
        UNIQUE (trade_id, model_used, analysis_version)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_trade_id 
    ON congress_trades_analysis(trade_id);

CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_score 
    ON congress_trades_analysis(conflict_score);

CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_confidence 
    ON congress_trades_analysis(confidence_score);

CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_analyzed_at 
    ON congress_trades_analysis(analyzed_at DESC);

-- Add comments
COMMENT ON TABLE congress_trades_analysis IS 'AI analysis results for congressional trades (separate from Supabase to save storage costs on large reasoning text)';
COMMENT ON COLUMN congress_trades_analysis.trade_id IS 'Foreign key to congress_trades.id in Supabase';
COMMENT ON COLUMN congress_trades_analysis.conflict_score IS 'AI-generated conflict of interest score (0.0 to 1.0)';
COMMENT ON COLUMN congress_trades_analysis.confidence_score IS 'AI confidence in the analysis (0.0-1.0, higher is more confident)';
COMMENT ON COLUMN congress_trades_analysis.reasoning IS 'AI-generated explanation of the conflict score (can be lengthy, stored here to save Supabase costs)';
COMMENT ON COLUMN congress_trades_analysis.model_used IS 'Name of the AI model used for analysis';
COMMENT ON COLUMN congress_trades_analysis.analysis_version IS 'Version of the analysis prompt/logic (incrementing allows A/B testing different approaches)';
