-- ETF Holdings Log Schema for Supabase
-- ======================================
-- Daily snapshot of ETF holdings to enable "Diff Engine" tracking.
-- Migrated from PostgreSQL research database to enable portfolio overlap detection.

-- Create table
CREATE TABLE IF NOT EXISTS public.etf_holdings_log (
    date DATE NOT NULL,
    etf_ticker VARCHAR(10) NOT NULL,
    holding_ticker VARCHAR(50) NOT NULL,
    holding_name TEXT,
    shares_held NUMERIC,           -- Key metric for diffing
    weight_percent NUMERIC,        -- Subject to price drift, less reliable
    market_value NUMERIC,          -- Optional: for context
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, etf_ticker, holding_ticker)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_etf_holdings_date ON public.etf_holdings_log(date DESC);
CREATE INDEX IF NOT EXISTS idx_etf_holdings_ticker ON public.etf_holdings_log(holding_ticker);
CREATE INDEX IF NOT EXISTS idx_etf_holdings_etf ON public.etf_holdings_log(etf_ticker, date DESC);

-- Comments
COMMENT ON TABLE public.etf_holdings_log IS 'Daily snapshot of ETF holdings from CSV downloads (iShares, ARK, etc.)';
COMMENT ON COLUMN public.etf_holdings_log.shares_held IS 'Share count - primary signal for buy/sell detection';
COMMENT ON COLUMN public.etf_holdings_log.weight_percent IS 'Portfolio weight % - noisy due to price changes';

-- Enable Row Level Security
ALTER TABLE public.etf_holdings_log ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to read
CREATE POLICY "Allow authenticated read access" ON public.etf_holdings_log
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Allow service role full access (for ETF job writes)
CREATE POLICY "Allow service role full access" ON public.etf_holdings_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
