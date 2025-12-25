-- Migration: Domain Health Tracking for Auto-Blacklisting
-- Description: Track domain extraction health to auto-blacklist problematic sites
-- Author: AI Assistant
-- Date: 2025-12-25

-- Create domain health tracking table
CREATE TABLE IF NOT EXISTS research_domain_health (
    domain TEXT PRIMARY KEY,
    total_attempts INTEGER DEFAULT 0,
    total_successes INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_failure_reason TEXT,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    auto_blacklisted BOOLEAN DEFAULT FALSE,
    auto_blacklisted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for finding unhealthy domains
CREATE INDEX IF NOT EXISTS idx_domain_health_consecutive 
    ON research_domain_health(consecutive_failures DESC, domain);

-- Add index for auto-blacklisted domains
CREATE INDEX IF NOT EXISTS idx_domain_health_blacklisted
    ON research_domain_health(auto_blacklisted, domain)
    WHERE auto_blacklisted = TRUE;

-- Enable RLS (read-only for authenticated users)
ALTER TABLE research_domain_health ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone authenticated can view domain health stats
CREATE POLICY "Anyone can view domain health stats"
    ON research_domain_health
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Only service role can modify (background jobs)
CREATE POLICY "Service role can modify domain health"
    ON research_domain_health
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Add auto-blacklist threshold setting
INSERT INTO system_settings (key, value, description, updated_by)
VALUES (
    'auto_blacklist_threshold',
    '4'::jsonb,
    'Number of consecutive failures before auto-blacklisting a domain',
    NULL
)
ON CONFLICT (key) DO NOTHING;

-- Add comment
COMMENT ON TABLE research_domain_health IS 'Tracks domain extraction health for auto-blacklisting problematic news sources. Consecutive failures trigger automatic blacklisting.';
