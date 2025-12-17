-- =====================================================
-- JOB EXECUTION TRACKING
-- =====================================================
-- Tracks job execution status to detect incomplete runs
-- Enables reliable backfill detection when Docker stops mid-job
-- =====================================================

-- Create job_executions table
CREATE TABLE IF NOT EXISTS job_executions (
  id SERIAL PRIMARY KEY,
  job_name VARCHAR(100) NOT NULL,
  target_date DATE NOT NULL,
  fund_name VARCHAR(200),  -- NULL for jobs that process all funds
  status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'failed')),
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  funds_processed TEXT[],  -- List of funds successfully completed
  error_message TEXT,
  CONSTRAINT unique_job_execution UNIQUE(job_name, target_date, fund_name)
);

-- Add comments for documentation
COMMENT ON TABLE job_executions IS 
  'Tracks job execution status to detect incomplete runs when container crashes or is stopped mid-job';

COMMENT ON COLUMN job_executions.job_name IS 
  'Name of the job (e.g., update_portfolio_prices, portfolio_refresh)';

COMMENT ON COLUMN job_executions.target_date IS 
  'Date that the job is processing data for (not when it ran)';

COMMENT ON COLUMN job_executions.fund_name IS 
  'Specific fund being processed, NULL if job processes all funds';

COMMENT ON COLUMN job_executions.status IS 
  'running = in progress (becomes stale if crashed), success = completed normally, failed = error occurred';

COMMENT ON COLUMN job_executions.funds_processed IS 
  'Array of fund names that completed successfully (for audit trail)';

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_job_executions_status 
  ON job_executions(job_name, target_date, status);

CREATE INDEX IF NOT EXISTS idx_job_executions_date 
  ON job_executions(target_date DESC);

CREATE INDEX IF NOT EXISTS idx_job_executions_running
  ON job_executions(status)
  WHERE status = 'running';

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Job execution tracking table created!';
    RAISE NOTICE '   Table: job_executions';
    RAISE NOTICE '   Indexes: 3 created';
    RAISE NOTICE '';
    RAISE NOTICE 'This table will track:';
    RAISE NOTICE '  - Job start/completion timestamps';
    RAISE NOTICE '  - Success/failure status';
    RAISE NOTICE '  - Which funds completed before crash';
    RAISE NOTICE '';
    RAISE NOTICE 'Backfill will now detect:';
    RAISE NOTICE '  - Crashed jobs (status=running for old dates)';
    RAISE NOTICE '  - Failed jobs (status=failed)';
    RAISE NOTICE '  - Partial completions (some funds done, others not)';
END $$;
