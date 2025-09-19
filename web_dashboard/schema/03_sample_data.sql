-- =====================================================
-- PORTFOLIO DASHBOARD - SAMPLE DATA
-- =====================================================
-- This creates sample users and fund assignments for testing
-- Run this LAST (optional) after 01_main_schema.sql and 02_auth_schema.sql
-- =====================================================

-- =====================================================
-- SAMPLE USERS (for testing)
-- =====================================================

-- Note: In a real setup, users would register through the web interface
-- This is just for testing/demo purposes

-- Create sample user profiles (these would normally be created by Supabase Auth)
-- You'll need to replace these with actual user IDs from auth.users after users register

-- Example user assignments (uncomment and modify as needed):
/*
-- Assign funds to users (replace with actual user IDs)
INSERT INTO user_funds (user_id, fund_name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Project Chimera'),
    ('00000000-0000-0000-0000-000000000001', 'RRSP Lance Webull'),
    ('00000000-0000-0000-0000-000000000002', 'TFSA'),
    ('00000000-0000-0000-0000-000000000002', 'TEST')
ON CONFLICT (user_id, fund_name) DO NOTHING;
*/

-- =====================================================
-- SAMPLE PORTFOLIO DATA (for testing)
-- =====================================================

-- Sample portfolio positions
INSERT INTO portfolio_positions (fund, ticker, shares, price, cost_basis, pnl, currency, date) VALUES
    ('Project Chimera', 'AAPL', 10.000000, 150.00, 1400.00, 100.00, 'USD', NOW() - INTERVAL '1 day'),
    ('Project Chimera', 'MSFT', 5.000000, 300.00, 1400.00, 100.00, 'USD', NOW() - INTERVAL '1 day'),
    ('RRSP Lance Webull', 'TSLA', 2.000000, 200.00, 350.00, 50.00, 'USD', NOW() - INTERVAL '1 day'),
    ('TFSA', 'SHOP.TO', 100.000000, 50.00, 4500.00, 500.00, 'CAD', NOW() - INTERVAL '1 day'),
    ('TEST', 'GOOGL', 1.000000, 100.00, 95.00, 5.00, 'USD', NOW() - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

-- Sample trade log
INSERT INTO trade_log (fund, date, ticker, shares, price, cost_basis, pnl, reason, currency) VALUES
    ('Project Chimera', NOW() - INTERVAL '2 days', 'AAPL', 10.000000, 140.00, 1400.00, 0.00, 'BUY - Strong fundamentals', 'USD'),
    ('Project Chimera', NOW() - INTERVAL '2 days', 'MSFT', 5.000000, 280.00, 1400.00, 0.00, 'BUY - Cloud growth', 'USD'),
    ('RRSP Lance Webull', NOW() - INTERVAL '3 days', 'TSLA', 2.000000, 175.00, 350.00, 0.00, 'BUY - EV leader', 'USD'),
    ('TFSA', NOW() - INTERVAL '4 days', 'SHOP.TO', 100.000000, 40.00, 4000.00, 0.00, 'BUY - E-commerce growth', 'CAD'),
    ('TEST', NOW() - INTERVAL '5 days', 'GOOGL', 1.000000, 95.00, 95.00, 0.00, 'BUY - Search dominance', 'USD')
ON CONFLICT DO NOTHING;

-- Sample cash balances
UPDATE cash_balances SET amount = 1000.00 WHERE fund = 'Project Chimera' AND currency = 'USD';
UPDATE cash_balances SET amount = 500.00 WHERE fund = 'RRSP Lance Webull' AND currency = 'USD';
UPDATE cash_balances SET amount = 2000.00 WHERE fund = 'TFSA' AND currency = 'CAD';
UPDATE cash_balances SET amount = 100.00 WHERE fund = 'TEST' AND currency = 'USD';

-- =====================================================
-- USAGE INSTRUCTIONS
-- =====================================================

-- To assign funds to real users after they register:
-- 1. Get the user ID from auth.users table
-- 2. Run: SELECT assign_fund_to_user('user@example.com', 'Project Chimera');
-- 3. Or use the admin script: python admin_assign_funds.py assign user@example.com "Project Chimera"

-- To list all users and their fund assignments:
-- SELECT * FROM list_users_with_funds();

-- To test fund access for a specific user:
-- SELECT * FROM get_user_funds('user-uuid-here');

-- =====================================================
-- SAMPLE DATA COMPLETE
-- =====================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Sample data created successfully!';
    RAISE NOTICE '📊 Sample portfolio positions, trades, and cash balances added';
    RAISE NOTICE '👥 Remember to assign funds to real users after they register';
    RAISE NOTICE '🔧 Use admin_assign_funds.py script for fund assignments';
    RAISE NOTICE '🚀 Your dashboard is ready to use!';
END $$;
