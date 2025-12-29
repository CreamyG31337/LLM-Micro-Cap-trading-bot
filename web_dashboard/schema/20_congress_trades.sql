-- =====================================================
-- CREATE CONGRESS TRADES TABLE (Supabase)
-- =====================================================
-- Stores congressional stock trading disclosures from Financial Modeling Prep API
-- Part of Congress Trading Module
-- 
-- Purpose: Track and analyze congressional stock trades for potential conflicts of interest
-- =====================================================

-- CURRENT SCHEMA STATE (Updated 2025-12-28)
-- Reflects migrations 23 (remove representative) and 25 (add politician_id FK)

CREATE TABLE IF NOT EXISTS congress_trades (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    politician VARCHAR(200) NOT NULL,       -- DEPRECATED: Use politician_id instead (will be dropped in future)
    politician_id INTEGER REFERENCES politicians(id), -- NEW: Foreign Key to politicians table
    chamber VARCHAR(20) NOT NULL CHECK (chamber IN ('House', 'Senate')),
    transaction_date DATE NOT NULL,
    disclosure_date DATE NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('Purchase', 'Sale', 'Exchange', 'Received')),
    amount VARCHAR(100),                    -- Store as string range like "$1,001 - $15,000"
    price NUMERIC(10, 2) DEFAULT NULL,      -- Asset price at time of trade
    asset_type VARCHAR(50) CHECK (asset_type IN ('Stock', 'Crypto')),
    party VARCHAR(50) CHECK (party IN ('Republican', 'Democrat', 'Independent')),
    state VARCHAR(2),                       -- Two-letter state code (CA, NY, TX, etc.)
    owner VARCHAR(100),                     -- Who owns the asset (Self, Spouse, Dependent Child, Joint)
    -- representative column was REMOVED (Migration 23)
    conflict_score FLOAT,                   -- 0.0 to 1.0 from AI analysis
    notes TEXT,                             -- AI reasoning/analysis or tooltip from source
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments...
COMMENT ON TABLE congress_trades IS 
  'Congressional stock trading disclosures from FMP API. Analyzed for potential conflicts of interest.';
-- ... (rest of comments)
