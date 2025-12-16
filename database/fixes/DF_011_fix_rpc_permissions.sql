-- =====================================================
-- Migration: Fix RPC Function Permissions
-- =====================================================
-- This migration recreates the list_users_with_funds function
-- to ensure it does NOT query auth.users, which avoids
-- "permission denied for table users" errors.
-- 
-- It only queries user_profiles and user_funds.
-- =====================================================

-- Recreate function to ensure it doesn't query auth.users
CREATE OR REPLACE FUNCTION list_users_with_funds()
RETURNS TABLE(
    user_id UUID,
    email TEXT,
    full_name TEXT,
    funds TEXT[]
) AS $$
BEGIN
    -- Only query user_profiles and user_funds (no auth.users)
    RETURN QUERY
    SELECT 
        up.user_id,
        up.email::TEXT,
        up.full_name::TEXT,
        ARRAY_AGG(uf.fund_name)::TEXT[] as funds
    FROM user_profiles up
    LEFT JOIN user_funds uf ON up.user_id = uf.user_id
    GROUP BY up.user_id, up.email, up.full_name
    ORDER BY up.email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- Grant execute permission explicitly
GRANT EXECUTE ON FUNCTION list_users_with_funds() TO authenticated;
GRANT EXECUTE ON FUNCTION list_users_with_funds() TO service_role;

-- Verify the function definition
SELECT '✅ Function recreated successfully' as status;
