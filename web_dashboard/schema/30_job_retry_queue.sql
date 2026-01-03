-- =====================================================
-- JOB RETRY QUEUE
-- =====================================================
-- Tracks failed jobs/days that need automatic retry
-- Survives container restarts (persistent in database)
-- =====================================================

CREATE TABLE IF NOT EXISTS job_retry_queue (
  id SERIAL PRIMARY KEY,
  
  -- Job identification
  job_name VARCHAR(100) NOT NULL,
  target_date DATE,  -- NULL for non-date-based jobs
  
  -- Entity tracking (flexible for different job types)
  entity_id VARCHAR(200),  -- e.g., fund_name, ticker, trade_id, or NULL for all-funds jobs
  entity_type VARCHAR(50) DEFAULT 'fund',  -- 'fund', 'ticker', 'trade', 'all_funds', etc.
  
  -- Failure tracking
  failure_reason VARCHAR(50) NOT NULL,  -- 'chunk_failed', 'insert_failed', 'container_restart', 'validation_failed', 'job_failed'
  error_message TEXT,
  failed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Retry tracking
  retry_count INTEGER DEFAULT 0,
  last_retry_at TIMESTAMP WITH TIME ZONE,
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'retrying', 'resolved', 'abandoned')),
  
  -- Context (JSONB for flexibility - batch ranges, chunk numbers, etc.)
  context JSONB,
  
  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  resolved_at TIMESTAMP WITH TIME ZONE,
  
  -- Unique constraint: one retry entry per job+date+entity combination
  CONSTRAINT unique_retry_entry UNIQUE(job_name, target_date, entity_id, entity_type)
);

-- Add comments for documentation
COMMENT ON TABLE job_retry_queue IS 
  'Tracks failed jobs/days that need automatic retry. Survives container restarts.';

COMMENT ON COLUMN job_retry_queue.job_name IS 
  'Name of the job (e.g., update_portfolio_prices, performance_metrics)';

COMMENT ON COLUMN job_retry_queue.target_date IS 
  'Date that needs reprocessing. NULL for non-date-based jobs.';

COMMENT ON COLUMN job_retry_queue.entity_id IS 
  'Specific entity (fund_name, ticker, etc.) or NULL for all-funds jobs';

COMMENT ON COLUMN job_retry_queue.entity_type IS 
  'Type of entity: fund, ticker, trade, all_funds, etc.';

COMMENT ON COLUMN job_retry_queue.failure_reason IS 
  'Why it failed: chunk_failed, insert_failed, container_restart, validation_failed, job_failed';

COMMENT ON COLUMN job_retry_queue.status IS 
  'pending = needs retry, retrying = currently being retried, resolved = succeeded, abandoned = gave up after max retries';

COMMENT ON COLUMN job_retry_queue.context IS 
  'JSONB for job-specific context (batch ranges, chunk numbers, etc.)';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_retry_queue_status 
  ON job_retry_queue(status, target_date NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_retry_queue_pending
  ON job_retry_queue(target_date NULLS LAST)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_retry_queue_job_entity
  ON job_retry_queue(job_name, entity_type, status);

CREATE INDEX IF NOT EXISTS idx_retry_queue_created
  ON job_retry_queue(created_at DESC);

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Job retry queue table created!';
    RAISE NOTICE '   Table: job_retry_queue';
    RAISE NOTICE '   Indexes: 4 created';
    RAISE NOTICE '';
    RAISE NOTICE 'This table will track:';
    RAISE NOTICE '  - Failed jobs that need retry';
    RAISE NOTICE '  - Jobs interrupted by container restart';
    RAISE NOTICE '  - Days with missing data (validation failures)';
    RAISE NOTICE '';
    RAISE NOTICE 'Watchdog job will:';
    RAISE NOTICE '  - Process pending retries';
    RAISE NOTICE '  - Retry up to 3 times';
    RAISE NOTICE '  - Mark as abandoned after max retries';
END $$;

