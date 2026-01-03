-- Securities Metadata Table
-- ========================
-- Central repository for security metadata (Name, Sector, Industry, etc.)
-- Populated by ETF Watchtower (high quality data from iShares/ARK) and other jobs.
-- Reduces dependency on slow yfinance calls for display names.

CREATE TABLE IF NOT EXISTS securities (
    ticker VARCHAR(20) PRIMARY KEY,
    name TEXT,
    sector TEXT,
    industry TEXT,
    asset_class VARCHAR(50),  -- e.g., 'Equity', 'Cash', 'Money Market'
    exchange VARCHAR(50),     -- e.g., 'NASDAQ', 'New York Stock Exchange Inc.'
    currency VARCHAR(10) DEFAULT 'USD',
    description TEXT,         -- Long description if available
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    -- Source tracking (who detected this ticker?)
    first_detected_by VARCHAR(50)  -- e.g., 'iShares IVV', 'ARK ARKK', 'User'
);

-- Index for searching companies by name
CREATE INDEX IF NOT EXISTS idx_securities_name ON securities USING gin(to_tsvector('english', name));

-- Index for sector/industry grouping
CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities(sector);
CREATE INDEX IF NOT EXISTS idx_securities_industry ON securities(industry);

COMMENT ON TABLE securities IS 'Metadata for tickers (Name, Sector, etc.) to optimize UI performance';
