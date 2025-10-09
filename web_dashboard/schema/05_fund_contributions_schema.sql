-- =====================================================
-- FUND CONTRIBUTIONS SCHEMA
-- =====================================================
-- This table stores individual contributions and withdrawals
-- for fund contributors (investors), NOT dashboard users
-- =====================================================

-- Drop existing table if it exists
DROP TABLE IF EXISTS fund_contributions CASCADE;

-- Fund contributions table
CREATE TABLE fund_contributions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    contributor VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    contribution_type VARCHAR(20) NOT NULL, -- CONTRIBUTION or WITHDRAWAL
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_fund_contributions_fund ON fund_contributions(fund);
CREATE INDEX idx_fund_contributions_contributor ON fund_contributions(contributor);
CREATE INDEX idx_fund_contributions_timestamp ON fund_contributions(timestamp);
CREATE INDEX idx_fund_contributions_fund_contributor ON fund_contributions(fund, contributor);

-- Trigger for updated_at
CREATE TRIGGER update_fund_contributions_updated_at
    BEFORE UPDATE ON fund_contributions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- VIEWS FOR CONTRIBUTORS
-- =====================================================

-- Current contributor ownership view
CREATE OR REPLACE VIEW contributor_ownership AS
SELECT 
    fund,
    contributor,
    email,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_contribution,
    COUNT(*) as transaction_count,
    MIN(timestamp) as first_contribution,
    MAX(timestamp) as last_transaction
FROM fund_contributions
GROUP BY fund, contributor, email
HAVING SUM(CASE 
    WHEN contribution_type = 'CONTRIBUTION' THEN amount 
    WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
    ELSE 0 
END) > 0
ORDER BY fund, net_contribution DESC;

-- Fund summary by contributors
CREATE OR REPLACE VIEW fund_contributor_summary AS
SELECT 
    fund,
    COUNT(DISTINCT contributor) as total_contributors,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_capital,
    MIN(timestamp) as fund_inception,
    MAX(timestamp) as last_activity
FROM fund_contributions
GROUP BY fund;

-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================

-- Enable RLS
ALTER TABLE fund_contributions ENABLE ROW LEVEL SECURITY;

-- Users can view contributions for their assigned funds
CREATE POLICY "Users can view contributions for their funds" ON fund_contributions
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );

-- Admins can manage all contributions
CREATE POLICY "Admins can manage all contributions" ON fund_contributions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Fund contributions schema created successfully';
    RAISE NOTICE '📊 Views created: contributor_ownership, fund_contributor_summary';
    RAISE NOTICE '🔐 Row Level Security enabled';
END $$;

