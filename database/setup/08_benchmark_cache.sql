-- Create benchmark_data table for caching market index data
-- This avoids repeated API calls to Yahoo Finance

CREATE TABLE IF NOT EXISTS public.benchmark_data (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,  -- e.g., '^GSPC', 'QQQ', '^RUT', 'VTI'
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT,
    adjusted_close DECIMAL(12, 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure no duplicate entries for same ticker/date
    UNIQUE(ticker, date)
);

-- Index for fast lookups by ticker and date range
CREATE INDEX IF NOT EXISTS idx_benchmark_ticker_date ON public.benchmark_data(ticker, date DESC);

-- Enable RLS (Row Level Security) - benchmarks are public data
ALTER TABLE public.benchmark_data ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all authenticated users to read benchmark data
CREATE POLICY "Allow authenticated users to read benchmark data"
    ON public.benchmark_data
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Allow service role to insert/update benchmark data
CREATE POLICY "Allow service role to manage benchmark data"
    ON public.benchmark_data
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE public.benchmark_data IS 'Cached market benchmark/index data from Yahoo Finance to reduce API calls';
COMMENT ON COLUMN public.benchmark_data.ticker IS 'Yahoo Finance ticker symbol (e.g., ^GSPC for S&P 500)';
COMMENT ON COLUMN public.benchmark_data.date IS 'Trading date';
COMMENT ON COLUMN public.benchmark_data.close IS 'Closing price for the day';
