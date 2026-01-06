-- =====================================================
-- READ-ONLY ADMIN ROLE SUPPORT
-- =====================================================
-- Migration 38: Add readonly_admin role with view-only access
-- Allows readonly_admin users to view admin pages but not modify data
-- =====================================================

-- Update is_admin() function to include readonly_admin role
-- This allows readonly_admin users to access admin pages
CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role IN ('admin', 'readonly_admin')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- New function to check if user can modify data (admin only)
-- This is used to protect write operations from readonly_admin users
CREATE OR REPLACE FUNCTION can_modify_data(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 38 complete: Read-only admin role support added';
    RAISE NOTICE '📋 Functions updated/added:';
    RAISE NOTICE '   - is_admin() now includes readonly_admin role (for page access)';
    RAISE NOTICE '   - can_modify_data() added (admin only, for write operations)';
    RAISE NOTICE '🔐 Role levels:';
    RAISE NOTICE '   - user: Standard user, no admin access';
    RAISE NOTICE '   - readonly_admin: Can view admin pages but cannot modify data';
    RAISE NOTICE '   - admin: Full admin access with all write permissions';
END $$;

