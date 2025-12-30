-- =====================================================
-- MIGRATION: Add duration_ms column to job_executions
-- =====================================================
-- Adds duration_ms column to store actual calculated execution duration
-- This fixes incorrect duration calculations from timestamp differences
-- =====================================================

-- Add duration_ms column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'job_executions' 
        AND column_name = 'duration_ms'
    ) THEN
        ALTER TABLE job_executions 
        ADD COLUMN duration_ms INTEGER;
        
        COMMENT ON COLUMN job_executions.duration_ms IS 
            'Execution duration in milliseconds, calculated by the job using time.time()';
        
        RAISE NOTICE '✅ Added duration_ms column to job_executions table';
    ELSE
        RAISE NOTICE 'ℹ️  duration_ms column already exists in job_executions table';
    END IF;
END $$;

