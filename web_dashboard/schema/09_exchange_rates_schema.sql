-- =====================================================
-- EXCHANGE RATES SCHEMA
-- =====================================================
-- This schema adds the exchange_rates table for storing
-- historical currency conversion rates (primarily USD/CAD)
-- =====================================================

-- Drop table if exists (for clean migrations)
DROP TABLE IF EXISTS exchange_rates CASCADE;

-- Exchange rates table
CREATE TABLE exchange_rates (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, timestamp)
);

-- Indexes for efficient queries
CREATE INDEX idx_exchange_rates_currencies ON exchange_rates(from_currency, to_currency);
CREATE INDEX idx_exchange_rates_timestamp ON exchange_rates(timestamp);
CREATE INDEX idx_exchange_rates_currencies_timestamp ON exchange_rates(from_currency, to_currency, timestamp);

-- Enable Row Level Security
ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Allow public read access (exchange rates are not sensitive)
CREATE POLICY "Allow public read access to exchange_rates" ON exchange_rates
    FOR SELECT USING (true);

-- Allow authenticated users to insert/update (for web dashboard updates)
CREATE POLICY "Allow authenticated users to manage exchange_rates" ON exchange_rates
    FOR ALL USING (auth.role() = 'authenticated');

-- Allow service role (admin) full access
CREATE POLICY "Allow service role full access to exchange_rates" ON exchange_rates
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to get exchange rate for a specific date
-- Returns the most recent rate on or before the target date
CREATE OR REPLACE FUNCTION get_exchange_rate_for_date(
    target_date TIMESTAMP WITH TIME ZONE,
    from_curr VARCHAR(3) DEFAULT 'USD',
    to_curr VARCHAR(3) DEFAULT 'CAD'
)
RETURNS DECIMAL(10, 6) AS $$
DECLARE
    result_rate DECIMAL(10, 6);
BEGIN
    SELECT rate INTO result_rate
    FROM exchange_rates
    WHERE from_currency = from_curr
      AND to_currency = to_curr
      AND timestamp <= target_date
    ORDER BY timestamp DESC
    LIMIT 1;
    
    RETURN COALESCE(result_rate, 1.35); -- Default fallback rate
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get latest exchange rate
CREATE OR REPLACE FUNCTION get_latest_exchange_rate(
    from_curr VARCHAR(3) DEFAULT 'USD',
    to_curr VARCHAR(3) DEFAULT 'CAD'
)
RETURNS DECIMAL(10, 6) AS $$
DECLARE
    result_rate DECIMAL(10, 6);
BEGIN
    SELECT rate INTO result_rate
    FROM exchange_rates
    WHERE from_currency = from_curr
      AND to_currency = to_curr
    ORDER BY timestamp DESC
    LIMIT 1;
    
    RETURN COALESCE(result_rate, 1.35); -- Default fallback rate
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SCHEMA COMPLETE
-- =====================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Exchange rates schema created successfully!';
    RAISE NOTICE '📊 Table: exchange_rates';
    RAISE NOTICE '🔍 Indexes created for efficient queries';
    RAISE NOTICE '🔐 RLS policies configured (public read, authenticated write)';
END $$;

