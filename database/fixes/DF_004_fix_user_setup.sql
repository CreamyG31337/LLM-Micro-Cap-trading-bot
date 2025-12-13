-- =====================================================
-- FIX USER PROFILE AUTO-CREATION
-- =====================================================
-- This fixes the user profile creation to properly:
-- 1. Create profile on signup
-- 2. Make first user admin
-- 3. Auto-assign admin to all available funds
-- =====================================================

-- Drop existing trigger and function
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS create_user_profile();

-- Recreated improved function
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
DECLARE
    user_count INTEGER;
    user_role VARCHAR(50);
    fund_record RECORD;
BEGIN
    -- Check if this is the first user (admin)
    SELECT COUNT(*) INTO user_count FROM user_profiles;
    
    IF user_count = 0 THEN
        user_role := 'admin';
    ELSE
        user_role := 'user';
    END IF;
    
    -- Create user profile
    INSERT INTO user_profiles (user_id, email, full_name, role)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        user_role
    );
    
    -- If admin, auto-assign to all funds
    IF user_role = 'admin' THEN
        -- Get all unique funds from portfolio_positions
        FOR fund_record IN 
            SELECT DISTINCT fund FROM portfolio_positions WHERE fund IS NOT NULL
        LOOP
            INSERT INTO user_funds (user_id, fund_name)
            VALUES (NEW.id, fund_record.fund)
            ON CONFLICT (user_id, fund_name) DO NOTHING;
        END LOOP;
        
        -- Also add default funds if portfolio is empty
        INSERT INTO user_funds (user_id, fund_name)
        VALUES 
            (NEW.id, 'Project Chimera'),
            (NEW.id, 'RRSP Lance Webull'),
            (NEW.id, 'TFSA'),
            (NEW.id, 'TEST')
        ON CONFLICT (user_id, fund_name) DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recreate trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile();

-- =====================================================
-- ALSO FIX EXISTING USER IF NEEDED
-- =====================================================
-- This will fix any existing user that doesn't have a profile

DO $$
DECLARE
    auth_user RECORD;
    user_count INTEGER;
    fund_record RECORD;
BEGIN
    -- Check each auth user
    FOR auth_user IN SELECT * FROM auth.users LOOP
        -- Check if profile exists
        IF NOT EXISTS (SELECT 1 FROM user_profiles WHERE user_id = auth_user.id) THEN
            -- Get current profile count to determine role
            SELECT COUNT(*) INTO user_count FROM user_profiles;
            
            -- Create profile
            INSERT INTO user_profiles (user_id, email, full_name, role)
            VALUES (
                auth_user.id,
                auth_user.email,
                COALESCE(auth_user.raw_user_meta_data->>'full_name', ''),
                CASE WHEN user_count = 0 THEN 'admin' ELSE 'user' END
            );
            
            -- If this is the first user (admin), assign all funds
            IF user_count = 0 THEN
                -- Assign funds from portfolio
                FOR fund_record IN 
                    SELECT DISTINCT fund FROM portfolio_positions WHERE fund IS NOT NULL
                LOOP
                    INSERT INTO user_funds (user_id, fund_name)
                    VALUES (auth_user.id, fund_record.fund)
                    ON CONFLICT (user_id, fund_name) DO NOTHING;
                END LOOP;
                
                -- Also add default funds
                INSERT INTO user_funds (user_id, fund_name)
                VALUES 
                    (auth_user.id, 'Project Chimera'),
                    (auth_user.id, 'RRSP Lance Webull'),
                    (auth_user.id, 'TFSA'),
                    (auth_user.id, 'TEST')
                ON CONFLICT (user_id, fund_name) DO NOTHING;
                
                RAISE NOTICE 'Created admin profile and assigned funds for: %', auth_user.email;
            ELSE
                RAISE NOTICE 'Created user profile for: %', auth_user.email;
            END IF;
        END IF;
    END LOOP;
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ User setup fixed!';
    RAISE NOTICE '📋 First user is automatically admin with all funds assigned';
    RAISE NOTICE '👥 New users will need manual fund assignment';
END $$;
