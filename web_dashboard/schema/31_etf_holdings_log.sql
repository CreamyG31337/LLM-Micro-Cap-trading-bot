-- ETF Holdings Log Schema
-- ========================
-- Daily snapshot of ETF holdings to enable "Diff Engine" tracking.
-- Detect institutional accumulation/distribution by comparing daily changes.

CREATE TABLE IF NOT EXISTS etf_holdings_log (
    date DATE NOT NULL,
    etf_ticker VARCHAR(10) NOT NULL,
    holding_ticker VARCHAR(20) NOT NULL,
    holding_name TEXT,
    shares_held NUMERIC,           -- Key metric for diffing
    weight_percent NUMERIC,        -- Subject to price drift, less reliable
    market_value NUMERIC,          -- Optional: for context
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, etf_ticker, holding_ticker)
);

-- Index for efficient date-range queries
CREATE INDEX IF NOT EXISTS idx_etf_holdings_date ON etf_holdings_log(date DESC);

-- Index for ticker-specific lookups
CREATE INDEX IF NOT EXISTS idx_etf_holdings_ticker ON etf_holdings_log(holding_ticker);

-- Index for ETF-specific queries
CREATE INDEX IF NOT EXISTS idx_etf_holdings_etf ON etf_holdings_log(etf_ticker, date DESC);

COMMENT ON TABLE etf_holdings_log IS 'Daily snapshot of ETF holdings from CSV downloads (iShares, ARK, etc.)';
COMMENT ON COLUMN etf_holdings_log.shares_held IS 'Share count - primary signal for buy/sell detection';
COMMENT ON COLUMN etf_holdings_log.weight_percent IS 'Portfolio weight % - noisy due to price changes';
