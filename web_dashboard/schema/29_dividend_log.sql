-- =====================================================
-- DIVIDEND LOG TABLE
-- =====================================================
-- Tracks automated dividend reinvestment (DRIP) transactions
-- Created by: Automated Dividend Estimator service
-- =====================================================

CREATE TABLE IF NOT EXISTS dividend_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL REFERENCES funds(name) ON UPDATE CASCADE ON DELETE RESTRICT,
    ticker VARCHAR(20) NOT NULL,
    ex_date DATE NOT NULL,
    pay_date DATE NOT NULL,
    gross_amount DECIMAL(15, 6) NOT NULL,
    withholding_tax DECIMAL(15, 6) NOT NULL DEFAULT 0,
    net_amount DECIMAL(15, 6) NOT NULL,
    reinvested_shares DECIMAL(15, 6) NOT NULL,
    drip_price DECIMAL(10, 2) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    trade_log_id UUID REFERENCES trade_log(id),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(fund, ticker, ex_date)  -- Prevent duplicate processing
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_dividend_log_fund ON dividend_log(fund);
CREATE INDEX IF NOT EXISTS idx_dividend_log_ticker ON dividend_log(ticker);
CREATE INDEX IF NOT EXISTS idx_dividend_log_ex_date ON dividend_log(ex_date);
CREATE INDEX IF NOT EXISTS idx_dividend_log_pay_date ON dividend_log(pay_date);
CREATE INDEX IF NOT EXISTS idx_dividend_log_trade_log_id ON dividend_log(trade_log_id);

-- Trigger for updated_at
CREATE TRIGGER update_dividend_log_updated_at
    BEFORE UPDATE ON dividend_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE dividend_log ENABLE ROW LEVEL SECURITY;

-- Basic RLS policy (allow all for now - will be restricted by auth schema)
CREATE POLICY "Allow all operations on dividend_log" ON dividend_log
    FOR ALL USING (true);

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Dividend log table created successfully!';
END $$;

