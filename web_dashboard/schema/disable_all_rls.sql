-- Disable ALL RLS completely for debugging
ALTER TABLE portfolio_positions DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE cash_balances DISABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_funds DISABLE ROW LEVEL SECURITY;

-- Also check if there's RLS on the view
-- Views inherit RLS from underlying tables, but let's be explicit
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
