-- Create the is_admin() function in Supabase
-- Run this in Supabase Dashboard > SQL Editor

CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles 
        WHERE user_id = user_uuid AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Refresh PostgREST schema cache (optional, usually happens automatically)
-- NOTIFY pgrst, 'reload schema';
