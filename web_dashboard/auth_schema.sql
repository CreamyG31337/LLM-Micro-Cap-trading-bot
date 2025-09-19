-- Authentication and User Management Schema
-- Run this in your Supabase SQL editor

-- Enable Row Level Security
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;

-- Create user_funds table to assign funds to users
CREATE TABLE IF NOT EXISTS user_funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    fund_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, fund_name)
);

-- Create user_profiles table for additional user info
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_funds_user_id ON user_funds(user_id);
CREATE INDEX IF NOT EXISTS idx_user_funds_fund_name ON user_funds(fund_name);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- RLS Policies for user_funds
ALTER TABLE user_funds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own fund assignments" ON user_funds
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own fund assignments" ON user_funds
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own fund assignments" ON user_funds
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own fund assignments" ON user_funds
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for user_profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policies for portfolio data (users can only see their assigned funds)
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

-- Create function to get user's assigned funds
CREATE OR REPLACE FUNCTION get_user_funds(user_uuid UUID)
RETURNS TABLE(fund_name VARCHAR(50)) AS $$
BEGIN
    RETURN QUERY
    SELECT uf.fund_name
    FROM user_funds uf
    WHERE uf.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check if user has access to fund
CREATE OR REPLACE FUNCTION user_has_fund_access(user_uuid UUID, fund_name VARCHAR(50))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_funds 
        WHERE user_id = user_uuid AND fund_name = user_has_fund_access.fund_name
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Insert some sample fund assignments (replace with real user IDs)
-- You'll need to get actual user IDs from auth.users after users register
-- INSERT INTO user_funds (user_id, fund_name) VALUES 
--     ('user-uuid-here', 'Project Chimera'),
--     ('user-uuid-here', 'RRSP Lance Webull'),
--     ('another-user-uuid', 'TFSA');
