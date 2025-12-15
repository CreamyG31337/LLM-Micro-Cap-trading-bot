-- =====================================================
-- Migration: Update contributor_ownership view to use new schema
-- =====================================================
-- This updates the contributor_ownership view to optionally use
-- the new contributors and funds tables for better data integrity.
-- 
-- Run this AFTER DF_009 (creates contributors table)
-- This is OPTIONAL - the view works fine with old columns too
-- =====================================================

-- Drop and recreate contributor_ownership view
-- Uses contributor_id if available, falls back to contributor string
DROP VIEW IF EXISTS contributor_ownership CASCADE;

CREATE OR REPLACE VIEW contributor_ownership AS
SELECT 
    fc.fund,
    COALESCE(c.name, fc.contributor) as contributor,  -- Use contributors.name if available
    COALESCE(c.email, fc.email) as email,  -- Use contributors.email if available
    SUM(CASE WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN fc.contribution_type = 'WITHDRAWAL' THEN fc.amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
        WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
        ELSE 0 
    END) as net_contribution,
    COUNT(*) as transaction_count,
    MIN(fc.timestamp) as first_contribution,
    MAX(fc.timestamp) as last_transaction
FROM fund_contributions fc
LEFT JOIN contributors c ON fc.contributor_id = c.id  -- Join with contributors table if available
GROUP BY fc.fund, COALESCE(c.name, fc.contributor), COALESCE(c.email, fc.email)
HAVING SUM(CASE 
    WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
    WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
    ELSE 0 
END) > 0
ORDER BY fc.fund, net_contribution DESC;

-- Update fund_contributor_summary view similarly
DROP VIEW IF EXISTS fund_contributor_summary CASCADE;

CREATE OR REPLACE VIEW fund_contributor_summary AS
SELECT 
    fc.fund,
    COUNT(DISTINCT COALESCE(c.id::text, fc.contributor)) as total_contributors,  -- Count unique contributors
    SUM(CASE WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN fc.contribution_type = 'WITHDRAWAL' THEN fc.amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
        WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
        ELSE 0 
    END) as net_capital,
    MIN(fc.timestamp) as fund_inception,
    MAX(fc.timestamp) as last_activity
FROM fund_contributions fc
LEFT JOIN contributors c ON fc.contributor_id = c.id  -- Join with contributors table if available
GROUP BY fc.fund;

-- Verification query
SELECT 
    '✅ Views Updated' as status,
    'contributor_ownership' as view_name,
    (SELECT COUNT(*) FROM contributor_ownership)::text as row_count,
    'Uses contributors table when available' as note

UNION ALL

SELECT 
    '✅ Views Updated' as status,
    'fund_contributor_summary' as view_name,
    (SELECT COUNT(*) FROM fund_contributor_summary)::text as row_count,
    'Uses contributors table when available' as note;

