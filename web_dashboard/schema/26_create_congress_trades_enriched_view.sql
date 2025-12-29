-- Migration 26: Create Enriched Congress Trades View (Verified Check)
-- Purpose: Provide a normalized view that JOINs trades with politician metadata
-- CORRECTED: Removed non-existent columns (representative, asset_description, etc.)

CREATE OR REPLACE VIEW congress_trades_enriched AS
SELECT 
    -- Verified existing columns
    ct.id,
    ct.politician_id,
    ct.ticker,
    ct.chamber,
    ct.transaction_date,
    ct.disclosure_date,
    ct.type,
    ct.amount,
    ct.asset_type,
    ct.price,
    ct.party,
    ct.state,
    ct.owner,
    ct.conflict_score,
    ct.notes,
    ct.created_at,
    
    -- Enriched politician data from politicians table
    p.name as politician,
    p.bioguide_id as politician_bioguide_id
    
FROM congress_trades ct
INNER JOIN politicians p ON ct.politician_id = p.id;

-- Add comment
COMMENT ON VIEW congress_trades_enriched IS 
'Enriched view of congress trades with politician metadata resolved via FK. 
Matches schema of congress_trades table but overrides politician name with normalized version.';
