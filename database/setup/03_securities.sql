-- Migration: Create Securities Table
-- Description: Normalize database by extracting ticker metadata into separate table
-- Date: 2025-12-13

-- Create securities table
CREATE TABLE IF NOT EXISTS securities (
    ticker VARCHAR(20) PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    country VARCHAR(10),
    market_cap TEXT,
    currency VARCHAR(3),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities(sector);
CREATE INDEX IF NOT EXISTS idx_securities_industry ON securities(industry);
CREATE INDEX IF NOT EXISTS idx_securities_currency ON securities(currency);

-- Populate with distinct tickers from portfolio_positions
-- This gets basic ticker and currency info
INSERT INTO securities (ticker, company_name, currency)
SELECT DISTINCT 
    ticker,
    company,  -- Temporary - will be updated from yfinance
    currency
FROM portfolio_positions
ON CONFLICT (ticker) DO NOTHING;

-- Add comment for documentation
COMMENT ON TABLE securities IS 'Normalized ticker metadata table storing company, sector, and industry information';
COMMENT ON COLUMN securities.ticker IS 'Stock ticker symbol (primary key)';
COMMENT ON COLUMN securities.company_name IS 'Full company name from yfinance';
COMMENT ON COLUMN securities.sector IS 'Business sector (e.g., Technology, Healthcare)';
COMMENT ON COLUMN securities.industry IS 'Specific industry within sector';
COMMENT ON COLUMN securities.country IS 'Country code (e.g., US, CA)';
COMMENT ON COLUMN securities.market_cap IS 'Market capitalization category';
COMMENT ON COLUMN securities.last_updated IS 'Timestamp when metadata was last refreshed from yfinance';
