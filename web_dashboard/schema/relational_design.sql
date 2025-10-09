-- =====================================================
-- PROPER RELATIONAL DATABASE DESIGN
-- =====================================================
-- This is how the database SHOULD be structured
-- =====================================================

-- Drop existing tables (clean slate)
DROP VIEW IF EXISTS current_positions CASCADE;
DROP TABLE IF EXISTS portfolio_positions CASCADE;
DROP TABLE IF EXISTS trade_log CASCADE;
DROP TABLE IF EXISTS cash_balances CASCADE;
DROP TABLE IF EXISTS performance_metrics CASCADE;
DROP TABLE IF EXISTS securities CASCADE;
DROP TABLE IF EXISTS funds CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- CORE ENTITIES
-- =====================================================

-- Users table
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Funds table (investment accounts)
CREATE TABLE funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    currency VARCHAR(10) NOT NULL DEFAULT 'CAD',
    fund_type VARCHAR(50) NOT NULL DEFAULT 'investment', -- investment, retirement, tfsa, etc.
    tax_status VARCHAR(50) NOT NULL DEFAULT 'taxable',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Securities table (stocks, ETFs, etc.)
CREATE TABLE securities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    security_type VARCHAR(50) NOT NULL DEFAULT 'stock', -- stock, etf, bond, etc.
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    exchange VARCHAR(50), -- NYSE, NASDAQ, TSX, etc.
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User-Fund relationships (many-to-many)
CREATE TABLE user_funds (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'owner', -- owner, viewer, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, fund_id)
);

-- =====================================================
-- TRANSACTIONAL DATA
-- =====================================================

-- Portfolio positions (current holdings)
CREATE TABLE portfolio_positions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    security_id UUID REFERENCES securities(id) ON DELETE CASCADE,
    shares DECIMAL(15, 6) NOT NULL,
    avg_price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    market_value DECIMAL(10, 2) GENERATED ALWAYS AS (shares * COALESCE(current_price, avg_price)) STORED,
    unrealized_pnl DECIMAL(10, 2) GENERATED ALWAYS AS (shares * COALESCE(current_price, avg_price) - cost_basis) STORED,
    stop_loss DECIMAL(10, 2),
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(fund_id, security_id, date) -- One position per security per day
);

-- Trade log (buy/sell transactions)
CREATE TABLE trade_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    security_id UUID REFERENCES securities(id) ON DELETE CASCADE,
    trade_date TIMESTAMP WITH TIME ZONE NOT NULL,
    action VARCHAR(10) NOT NULL, -- BUY, SELL, DIVIDEND, etc.
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cash balances
CREATE TABLE cash_balances (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund_id UUID REFERENCES funds(id) ON DELETE CASCADE,
    currency VARCHAR(10) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(fund_id, currency)
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);

-- Funds indexes
CREATE INDEX idx_funds_name ON funds(name);

-- Securities indexes
CREATE INDEX idx_securities_ticker ON securities(ticker);
CREATE INDEX idx_securities_company ON securities(company_name);
CREATE INDEX idx_securities_type ON securities(security_type);

-- Portfolio positions indexes
CREATE INDEX idx_portfolio_positions_fund ON portfolio_positions(fund_id);
CREATE INDEX idx_portfolio_positions_security ON portfolio_positions(security_id);
CREATE INDEX idx_portfolio_positions_date ON portfolio_positions(date);

-- Trade log indexes
CREATE INDEX idx_trade_log_fund ON trade_log(fund_id);
CREATE INDEX idx_trade_log_security ON trade_log(security_id);
CREATE INDEX idx_trade_log_date ON trade_log(trade_date);

-- Cash balances indexes
CREATE INDEX idx_cash_balances_fund ON cash_balances(fund_id);

-- =====================================================
-- VIEWS
-- =====================================================

-- Current positions view (with proper joins)
CREATE VIEW current_positions AS
SELECT
    f.name as fund_name,
    s.ticker,
    s.company_name,
    s.security_type,
    s.currency as security_currency,
    pp.shares,
    pp.avg_price,
    pp.current_price,
    pp.cost_basis,
    pp.market_value,
    pp.unrealized_pnl,
    pp.date as last_updated
FROM portfolio_positions pp
JOIN funds f ON pp.fund_id = f.id
JOIN securities s ON pp.security_id = s.id
WHERE pp.shares > 0
  AND pp.date = (
    SELECT MAX(date) 
    FROM portfolio_positions pp2 
    WHERE pp2.fund_id = pp.fund_id 
      AND pp2.security_id = pp.security_id
  );

-- =====================================================
-- TRIGGERS
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
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_funds_updated_at
    BEFORE UPDATE ON funds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_securities_updated_at
    BEFORE UPDATE ON securities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolio_positions_updated_at
    BEFORE UPDATE ON portfolio_positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cash_balances_updated_at
    BEFORE UPDATE ON cash_balances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA
-- =====================================================

-- Insert sample users
INSERT INTO users (email, name) VALUES
    ('user1@example.com', 'John Doe'),
    ('user2@example.com', 'Jane Smith');

-- Insert sample funds
INSERT INTO funds (name, description, currency, fund_type, tax_status) VALUES
    ('Project Chimera', 'Main investment fund', 'CAD', 'investment', 'taxable'),
    ('RRSP Lance Webull', 'Retirement savings', 'CAD', 'retirement', 'tax_deferred'),
    ('TFSA', 'Tax-free savings account', 'CAD', 'tfsa', 'tax_free');

-- Insert sample securities
INSERT INTO securities (ticker, company_name, security_type, currency, exchange, sector) VALUES
    ('AAPL', 'Apple Inc.', 'stock', 'USD', 'NASDAQ', 'Technology'),
    ('MSFT', 'Microsoft Corporation', 'stock', 'USD', 'NASDAQ', 'Technology'),
    ('CNR.TO', 'Canadian National Railway Company', 'stock', 'CAD', 'TSX', 'Transportation'),
    ('SHOP.TO', 'Shopify Inc.', 'stock', 'CAD', 'TSX', 'Technology'),
    ('VTI', 'Vanguard Total Stock Market ETF', 'etf', 'USD', 'NYSE', 'Diversified');

-- Assign funds to users
INSERT INTO user_funds (user_id, fund_id, role) VALUES
    ((SELECT id FROM users WHERE email = 'user1@example.com'), (SELECT id FROM funds WHERE name = 'Project Chimera'), 'owner'),
    ((SELECT id FROM users WHERE email = 'user1@example.com'), (SELECT id FROM funds WHERE name = 'RRSP Lance Webull'), 'owner'),
    ((SELECT id FROM users WHERE email = 'user2@example.com'), (SELECT id FROM funds WHERE name = 'TFSA'), 'owner');

-- =====================================================
-- USAGE EXAMPLES
-- =====================================================

-- Get all positions for a fund with company names
/*
SELECT 
    f.name as fund,
    s.ticker,
    s.company_name,
    pp.shares,
    pp.current_price,
    pp.market_value
FROM portfolio_positions pp
JOIN funds f ON pp.fund_id = f.id
JOIN securities s ON pp.security_id = s.id
WHERE f.name = 'Project Chimera'
  AND pp.shares > 0;
*/

-- Get all trades for a security
/*
SELECT 
    f.name as fund,
    s.ticker,
    s.company_name,
    tl.trade_date,
    tl.action,
    tl.shares,
    tl.price
FROM trade_log tl
JOIN funds f ON tl.fund_id = f.id
JOIN securities s ON tl.security_id = s.id
WHERE s.ticker = 'AAPL'
ORDER BY tl.trade_date DESC;
*/

-- Get portfolio performance by fund
/*
SELECT 
    f.name as fund,
    COUNT(DISTINCT pp.security_id) as num_positions,
    SUM(pp.market_value) as total_value,
    SUM(pp.cost_basis) as total_cost,
    SUM(pp.unrealized_pnl) as total_pnl,
    ROUND(SUM(pp.unrealized_pnl) / SUM(pp.cost_basis) * 100, 2) as pnl_percentage
FROM portfolio_positions pp
JOIN funds f ON pp.fund_id = f.id
WHERE pp.shares > 0
GROUP BY f.id, f.name
ORDER BY total_value DESC;
*/
