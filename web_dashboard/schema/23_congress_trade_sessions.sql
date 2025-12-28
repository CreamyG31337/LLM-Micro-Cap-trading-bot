-- Congress Trade Sessions Table
-- ================================
-- Tracks "living sessions" of related trades that tell a story together.
-- Sessions can span multiple days (7-day gap rule) and are re-analyzed as new trades arrive.

CREATE TABLE IF NOT EXISTS congress_trade_sessions (
    id SERIAL PRIMARY KEY,
    
    -- Session metadata
    politician_id INTEGER,  -- Foreign key to politicians table (not enforced for flexibility)
    politician_name VARCHAR(255) NOT NULL,  -- Denormalized for easier querying
    
    -- Date range
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- Session stats
    trade_count INTEGER DEFAULT 0,
    total_value_estimate VARCHAR(100),  -- e.g., "$100k-$500k" (estimated from ranges)
    
    -- AI Analysis Results (for the ENTIRE session)
    conflict_score DECIMAL(3,2) CHECK (conflict_score >= 0 AND conflict_score <= 1),
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ai_summary TEXT,  -- The "story" that Granite tells about this session
    
    -- Tracking & triggers
    last_analyzed_at TIMESTAMP WITH TIME ZONE,
    needs_reanalysis BOOLEAN DEFAULT TRUE,  -- Set to TRUE when new trades added
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Model version tracking
    model_used VARCHAR(100),
    analysis_version INTEGER DEFAULT 1,
    
    -- Ensure we don't create duplicate sessions
    CONSTRAINT unique_politician_date_range UNIQUE (politician_name, start_date, end_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_congress_trade_sessions_politician 
    ON congress_trade_sessions(politician_name);

CREATE INDEX IF NOT EXISTS idx_congress_trade_sessions_dates 
    ON congress_trade_sessions(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_congress_trade_sessions_needs_reanalysis 
    ON congress_trade_sessions(needs_reanalysis) 
    WHERE needs_reanalysis = TRUE;  -- Partial index for efficiency

CREATE INDEX IF NOT EXISTS idx_congress_trade_sessions_score 
    ON congress_trade_sessions(conflict_score);

-- Comments
COMMENT ON TABLE congress_trade_sessions IS 'Trading sessions that group related trades together for pattern analysis';
COMMENT ON COLUMN congress_trade_sessions.politician_name IS 'Denormalized politician name for easier querying';
COMMENT ON COLUMN congress_trade_sessions.start_date IS 'First trade date in this session';
COMMENT ON COLUMN congress_trade_sessions.end_date IS 'Last trade date in this session (can be updated as new trades arrive)';
COMMENT ON COLUMN congress_trade_sessions.trade_count IS 'Number of trades in this session';
COMMENT ON COLUMN congress_trade_sessions.conflict_score IS 'AI-generated conflict score for the ENTIRE session (0.0-1.0)';
COMMENT ON COLUMN congress_trade_sessions.ai_summary IS 'AI-generated narrative explaining the session and any suspicious patterns';
COMMENT ON COLUMN congress_trade_sessions.needs_reanalysis IS 'TRUE when new trades added to session or analysis needs updating';
COMMENT ON COLUMN congress_trade_sessions.last_analyzed_at IS 'Last time this session was analyzed by AI';

-- Update the existing congress_trades_analysis table to link to sessions
ALTER TABLE congress_trades_analysis 
ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES congress_trade_sessions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_session 
    ON congress_trades_analysis(session_id);

COMMENT ON COLUMN congress_trades_analysis.session_id IS 'Links this trade analysis to its session (all trades in session share same analysis)';
