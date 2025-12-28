-- Add confidence_score column to congress_trades_analysis table
-- This migration adds AI confidence scoring to track how certain the AI is about its conflict analysis

ALTER TABLE congress_trades_analysis 
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2) 
CHECK (confidence_score >= 0 AND confidence_score <= 1);

-- Add index for performance when filtering/sorting by confidence
CREATE INDEX IF NOT EXISTS idx_congress_trades_analysis_confidence 
ON congress_trades_analysis(confidence_score);

-- Add column documentation
COMMENT ON COLUMN congress_trades_analysis.confidence_score IS 
'AI confidence in the analysis (0.0-1.0, higher is more confident)';
