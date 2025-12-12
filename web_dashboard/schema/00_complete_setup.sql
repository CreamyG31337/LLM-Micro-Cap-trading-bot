-- =====================================================
-- PORTFOLIO DASHBOARD - COMPLETE DATABASE SETUP
-- =====================================================
-- This is the ONE FILE to rule them all
-- Copy and paste this entire file into Supabase SQL editor
-- =====================================================

-- =====================================================
-- PART 1: MAIN SCHEMA (Core Portfolio Tables)
-- =====================================================

-- Drop everything first (clean slate)
DROP VIEW IF EXISTS current_positions CASCADE;
DROP TABLE IF EXISTS portfolio_positions CASCADE;
DROP TABLE IF EXISTS trade_log CASCADE;
DROP TABLE IF EXISTS cash_balances CASCADE;
DROP TABLE IF EXISTS performance_metrics CASCADE;
DROP TABLE IF EXISTS user_funds CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS calculate_daily_performance(DATE, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_user_funds(UUID) CASCADE;
DROP FUNCTION IF EXISTS user_has_fund_access(UUID, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_user_accessible_funds() CASCADE;
DROP FUNCTION IF EXISTS create_user_profile() CASCADE;
DROP FUNCTION IF EXISTS assign_fund_to_user(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS list_users_with_funds() CASCADE;
DROP TABLE IF EXISTS exchange_rates CASCADE;
DROP FUNCTION IF EXISTS get_exchange_rate_for_date(TIMESTAMPTZ, VARCHAR, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_latest_exchange_rate(VARCHAR, VARCHAR) CASCADE;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Portfolio positions table
CREATE TABLE portfolio_positions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_value DECIMAL(10, 2) GENERATED ALWAYS AS (shares * price) STORED,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trade log table
CREATE TABLE trade_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cash balances table
CREATE TABLE cash_balances (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(fund, currency)
);

-- Performance metrics table for caching
CREATE TABLE performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_value DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    unrealized_pnl DECIMAL(10, 2) NOT NULL,
    performance_pct DECIMAL(5, 2) NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(fund, date)
);

-- =====================================================
-- PART 2: AUTHENTICATION TABLES
-- =====================================================

-- User fund assignments table
CREATE TABLE user_funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    fund_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, fund_name)
);

-- User profiles table for additional user info
CREATE TABLE user_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- =====================================================
-- PART 3: INDEXES FOR PERFORMANCE
-- =====================================================

-- Portfolio positions indexes
CREATE INDEX idx_portfolio_positions_fund ON portfolio_positions(fund);
CREATE INDEX idx_portfolio_positions_ticker ON portfolio_positions(ticker);
CREATE INDEX idx_portfolio_positions_date ON portfolio_positions(date);
CREATE INDEX idx_portfolio_positions_fund_ticker ON portfolio_positions(fund, ticker);

-- Trade log indexes
CREATE INDEX idx_trade_log_fund ON trade_log(fund);
CREATE INDEX idx_trade_log_ticker ON trade_log(ticker);
CREATE INDEX idx_trade_log_date ON trade_log(date);

-- Cash balances indexes
CREATE INDEX idx_cash_balances_fund ON cash_balances(fund);

-- Performance metrics indexes
CREATE INDEX idx_performance_metrics_fund ON performance_metrics(fund);
CREATE INDEX idx_performance_metrics_date ON performance_metrics(date);

-- User funds indexes
CREATE INDEX idx_user_funds_user_id ON user_funds(user_id);
CREATE INDEX idx_user_funds_fund_name ON user_funds(fund_name);

-- User profiles indexes
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);

-- =====================================================
-- PART 4: TRIGGERS AND FUNCTIONS
-- =====================================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_portfolio_positions_updated_at
    BEFORE UPDATE ON portfolio_positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_performance_metrics_updated_at
    BEFORE UPDATE ON performance_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- PART 5: VIEWS
-- =====================================================

-- Current positions view (shares > 0)
CREATE VIEW current_positions AS
SELECT
    fund,
    ticker,
    currency,
    SUM(shares) as total_shares,
    AVG(price) as avg_price,
    SUM(cost_basis) as total_cost_basis,
    SUM(pnl) as total_pnl,
    SUM(total_value) as total_market_value,
    MAX(date) as last_updated
FROM portfolio_positions
WHERE shares > 0
GROUP BY fund, ticker, currency;

-- =====================================================
-- PART 6: UTILITY FUNCTIONS
-- =====================================================

-- Function to calculate daily performance by fund
CREATE OR REPLACE FUNCTION calculate_daily_performance(target_date DATE, fund_name VARCHAR(50) DEFAULT NULL)
RETURNS TABLE (
    fund VARCHAR(50),
    total_value DECIMAL(10, 2),
    cost_basis DECIMAL(10, 2),
    unrealized_pnl DECIMAL(10, 2),
    performance_pct DECIMAL(5, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.fund,
        COALESCE(SUM(p.total_value), 0) as total_value,
        COALESCE(SUM(p.cost_basis), 0) as cost_basis,
        COALESCE(SUM(p.pnl), 0) as unrealized_pnl,
        CASE
            WHEN SUM(p.cost_basis) > 0 THEN (SUM(p.pnl) / SUM(p.cost_basis)) * 100
            ELSE 0
        END as performance_pct
    FROM portfolio_positions p
    WHERE p.date::date = target_date
      AND p.shares > 0
      AND (fund_name IS NULL OR p.fund = fund_name)
    GROUP BY p.fund;
END;
$$ LANGUAGE plpgsql;

-- Function to get user's assigned funds
CREATE OR REPLACE FUNCTION get_user_funds(user_uuid UUID)
RETURNS TABLE(fund_name VARCHAR(50)) AS $$
BEGIN
    RETURN QUERY
    SELECT uf.fund_name
    FROM user_funds uf
    WHERE uf.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user has access to fund
CREATE OR REPLACE FUNCTION user_has_fund_access(user_uuid UUID, fund_name VARCHAR(50))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_funds 
        WHERE user_id = user_uuid AND fund_name = user_has_fund_access.fund_name
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's accessible funds (for API)
CREATE OR REPLACE FUNCTION get_user_accessible_funds()
RETURNS TABLE(fund_name VARCHAR(50)) AS $$
BEGIN
    RETURN QUERY
    SELECT uf.fund_name
    FROM user_funds uf
    WHERE uf.user_id = auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create user profile on signup
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
DECLARE
    user_count INTEGER;
    user_role VARCHAR(50);
BEGIN
    -- Check if this is the first user (admin)
    SELECT COUNT(*) INTO user_count FROM user_profiles;
    
    IF user_count = 0 THEN
        user_role := 'admin';
    ELSE
        user_role := 'user';
    END IF;
    
    INSERT INTO user_profiles (user_id, email, full_name, role)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        user_role
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create user profile
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- =====================================================
-- ADMIN FUNCTIONS AND POLICIES
-- =====================================================

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Admin policies for user management
CREATE POLICY "Admins can view all user profiles" ON user_profiles
    FOR SELECT USING (is_admin(auth.uid()));

CREATE POLICY "Admins can view all user funds" ON user_funds
    FOR SELECT USING (is_admin(auth.uid()));

CREATE POLICY "Admins can manage user funds" ON user_funds
    FOR ALL USING (is_admin(auth.uid()));

-- =====================================================
-- FUND ASSIGNMENT FUNCTIONS
-- =====================================================

-- Function to assign fund to user (admin only)
CREATE OR REPLACE FUNCTION assign_fund_to_user(user_email TEXT, fund_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
BEGIN
    -- Get user ID by email
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
    
    -- Insert fund assignment
    INSERT INTO user_funds (user_id, fund_name)
    VALUES (target_user_id, fund_name)
    ON CONFLICT (user_id, fund_name) DO NOTHING;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to list all users with their fund assignments
CREATE OR REPLACE FUNCTION list_users_with_funds()
RETURNS TABLE(
    user_id UUID,
    email TEXT,
    full_name TEXT,
    funds TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        up.user_id,
        up.email,
        up.full_name,
        ARRAY_AGG(uf.fund_name) as funds
    FROM user_profiles up
    LEFT JOIN user_funds uf ON up.user_id = uf.user_id
    GROUP BY up.user_id, up.email, up.full_name
    ORDER BY up.email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- PART 7: ROW LEVEL SECURITY
-- =====================================================

-- Enable Row Level Security
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_funds ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- User funds policies
CREATE POLICY "Users can view their own fund assignments" ON user_funds
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own fund assignments" ON user_funds
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own fund assignments" ON user_funds
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own fund assignments" ON user_funds
    FOR DELETE USING (auth.uid() = user_id);

-- User profiles policies
CREATE POLICY "Users can view their own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

-- Fund-based access policies for portfolio data
CREATE POLICY "Users can view portfolio positions for their funds" ON portfolio_positions
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view trades for their funds" ON trade_log
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view cash balances for their funds" ON cash_balances
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view performance metrics for their funds" ON performance_metrics
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );

-- =====================================================
-- PART 8: INITIAL DATA SETUP
-- =====================================================

-- Insert initial cash balances for common funds
INSERT INTO cash_balances (fund, currency, amount) VALUES
    ('Project Chimera', 'CAD', 0.00),
    ('Project Chimera', 'USD', 0.00),
    ('RRSP Lance Webull', 'CAD', 0.00),
    ('RRSP Lance Webull', 'USD', 0.00),
    ('TEST', 'CAD', 0.00),
    ('TEST', 'USD', 0.00),
    ('TFSA', 'CAD', 0.00),
    ('TFSA', 'USD', 0.00)
ON CONFLICT (fund, currency) DO NOTHING;

-- =====================================================
-- PART 9: FUND CONTRIBUTIONS (HOLDERS/INVESTORS)
-- =====================================================

-- Fund contributions table (for tracking investors/contributors)
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

-- Indexes for fund_contributions
CREATE INDEX idx_fund_contributions_fund ON fund_contributions(fund);
CREATE INDEX idx_fund_contributions_contributor ON fund_contributions(contributor);
CREATE INDEX idx_fund_contributions_timestamp ON fund_contributions(timestamp);
CREATE INDEX idx_fund_contributions_fund_contributor ON fund_contributions(fund, contributor);

-- Trigger for updated_at on fund_contributions
CREATE TRIGGER update_fund_contributions_updated_at
    BEFORE UPDATE ON fund_contributions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Contributor ownership view
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

-- Fund contributor summary view
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

-- Enable RLS for fund_contributions
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
-- PART 10: EXCHANGE RATES
-- =====================================================

-- Exchange rates table for currency conversion
CREATE TABLE IF NOT EXISTS exchange_rates (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, timestamp)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies ON exchange_rates(from_currency, to_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_timestamp ON exchange_rates(timestamp);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies_timestamp ON exchange_rates(from_currency, to_currency, timestamp);

-- Enable Row Level Security
ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Allow public read access to exchange_rates" ON exchange_rates
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated users to manage exchange_rates" ON exchange_rates
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow service role full access to exchange_rates" ON exchange_rates
    FOR ALL USING (auth.role() = 'service_role');

-- Helper function to get exchange rate for a specific date
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

-- Helper function to get latest exchange rate
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
-- SETUP COMPLETE!
-- =====================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '🎉 COMPLETE DATABASE SETUP FINISHED!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ All tables created successfully';
    RAISE NOTICE '🔐 Authentication system ready';
    RAISE NOTICE '🛡️ Row Level Security enabled';
    RAISE NOTICE '👥 User management ready';
    RAISE NOTICE '💰 Portfolio tracking ready';
    RAISE NOTICE '👥 Fund contributors/holders tracking ready';
    RAISE NOTICE '💱 Exchange rates tracking ready';
    RAISE NOTICE '========================================';
    RAISE NOTICE '📋 Next steps:';
    RAISE NOTICE '1. Run: python web_dashboard/migrate_all_funds.py';
    RAISE NOTICE '2. Run: python web_dashboard/migrate_contributors.py';
    RAISE NOTICE '3. Test user registration on the dashboard';
    RAISE NOTICE '4. Assign funds to users with: python admin_assign_funds.py';
    RAISE NOTICE '5. Start using your secure portfolio dashboard!';
    RAISE NOTICE '========================================';
END $$;
