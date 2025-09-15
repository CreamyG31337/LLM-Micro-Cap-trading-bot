-- Supabase Database Schema for Portfolio Dashboard
-- Run this in your Supabase SQL editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create portfolio_positions table
CREATE TABLE portfolio_positions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_value DECIMAL(10, 2) GENERATED ALWAYS AS (shares * price) STORED,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trade_log table
CREATE TABLE trade_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create cash_balances table
CREATE TABLE cash_balances (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    currency VARCHAR(3) NOT NULL UNIQUE,
    amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance_metrics table for caching
CREATE TABLE performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_value DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    unrealized_pnl DECIMAL(10, 2) NOT NULL,
    performance_pct DECIMAL(5, 2) NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_portfolio_positions_ticker ON portfolio_positions(ticker);
CREATE INDEX idx_portfolio_positions_date ON portfolio_positions(date);
CREATE INDEX idx_trade_log_ticker ON trade_log(ticker);
CREATE INDEX idx_trade_log_date ON trade_log(date);
CREATE INDEX idx_performance_metrics_date ON performance_metrics(date);

-- Create updated_at trigger function
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

-- Insert initial cash balances
INSERT INTO cash_balances (currency, amount) VALUES 
    ('CAD', 0.00),
    ('USD', 0.00)
ON CONFLICT (currency) DO NOTHING;

-- Enable Row Level Security (RLS)
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (allow all for now - you can restrict later)
CREATE POLICY "Allow all operations on portfolio_positions" ON portfolio_positions
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on trade_log" ON trade_log
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on cash_balances" ON cash_balances
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on performance_metrics" ON performance_metrics
    FOR ALL USING (true);

-- Create a view for current positions (shares > 0)
CREATE VIEW current_positions AS
SELECT 
    ticker,
    SUM(shares) as total_shares,
    AVG(price) as avg_price,
    SUM(cost_basis) as total_cost_basis,
    SUM(pnl) as total_pnl,
    SUM(total_value) as total_market_value,
    MAX(date) as last_updated
FROM portfolio_positions 
WHERE shares > 0
GROUP BY ticker;

-- Create a function to calculate daily performance
CREATE OR REPLACE FUNCTION calculate_daily_performance(target_date DATE)
RETURNS TABLE (
    total_value DECIMAL(10, 2),
    cost_basis DECIMAL(10, 2),
    unrealized_pnl DECIMAL(10, 2),
    performance_pct DECIMAL(5, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(p.total_value), 0) as total_value,
        COALESCE(SUM(p.cost_basis), 0) as cost_basis,
        COALESCE(SUM(p.pnl), 0) as unrealized_pnl,
        CASE 
            WHEN SUM(p.cost_basis) > 0 THEN (SUM(p.pnl) / SUM(p.cost_basis)) * 100
            ELSE 0
        END as performance_pct
    FROM portfolio_positions p
    WHERE p.date::date = target_date AND p.shares > 0;
END;
$$ LANGUAGE plpgsql;
