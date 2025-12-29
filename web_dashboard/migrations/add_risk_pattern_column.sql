-- Add risk_pattern column to congress analysis tables
-- Stores the enumerated risk pattern: DIRECT_CONFLICT, PIVOT, MACRO_RISK, or ROUTINE

-- Add to congress_trades_analysis
ALTER TABLE congress_trades_analysis 
ADD COLUMN IF NOT EXISTS risk_pattern VARCHAR(20);

-- Add index for filtering by risk pattern
CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_risk_pattern 
    ON congress_trades_analysis(risk_pattern);

-- Add comment
COMMENT ON COLUMN congress_trades_analysis.risk_pattern IS 'Enumerated risk pattern: DIRECT_CONFLICT, PIVOT, MACRO_RISK, or ROUTINE';

-- Add to congress_trade_sessions
ALTER TABLE congress_trade_sessions 
ADD COLUMN IF NOT EXISTS risk_pattern VARCHAR(20);

-- Add index for filtering by risk pattern
CREATE INDEX IF NOT EXISTS idx_congress_trade_sessions_risk_pattern 
    ON congress_trade_sessions(risk_pattern);

-- Add comment
COMMENT ON COLUMN congress_trade_sessions.risk_pattern IS 'Enumerated risk pattern for the session: DIRECT_CONFLICT, PIVOT, MACRO_RISK, or ROUTINE';
