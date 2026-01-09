-- =====================================================
-- FIX DUPLICATE USER PREFERENCE FUNCTIONS
-- =====================================================
-- There are duplicate versions of get_user_preference and set_user_preference
-- causing Supabase RPC to fail with PGRST203 error.
-- This script drops the duplicates and ensures only the correct versions exist.
-- =====================================================

-- Drop ALL existing versions of both functions
DROP FUNCTION IF EXISTS public.get_user_preference(TEXT, UUID);
DROP FUNCTION IF EXISTS public.get_user_preference(TEXT);
DROP FUNCTION IF EXISTS public.set_user_preference(TEXT, TEXT, UUID);
DROP FUNCTION IF EXISTS public.set_user_preference(TEXT, TEXT);

-- Recreate get_user_preference (takes only pref_key, uses auth.uid() internally)
CREATE OR REPLACE FUNCTION public.get_user_preference(pref_key TEXT)
RETURNS JSONB AS $$
DECLARE
    user_uuid UUID;
    pref_value JSONB;
BEGIN
    user_uuid := auth.uid();
    
    IF user_uuid IS NULL THEN
        RETURN NULL;
    END IF;
    
    SELECT preferences->pref_key INTO pref_value
    FROM user_profiles
    WHERE user_id = user_uuid;
    
    RETURN pref_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- Recreate set_user_preference with optional UUID parameter
-- If user_uuid is NULL, uses auth.uid() internally
CREATE OR REPLACE FUNCTION public.set_user_preference(
    pref_key TEXT, 
    pref_value TEXT,
    user_uuid UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_uuid UUID;
    rows_updated INTEGER;
    pref_value_jsonb JSONB;
    profile_exists BOOLEAN;
BEGIN
    -- Use provided user_uuid or fall back to auth.uid()
    IF user_uuid IS NULL THEN
        target_user_uuid := auth.uid();
    ELSE
        target_user_uuid := user_uuid;
    END IF;
    
    IF target_user_uuid IS NULL THEN
        RAISE WARNING 'set_user_preference: target_user_uuid is NULL (user_uuid param was NULL and auth.uid() returned NULL)';
        RETURN FALSE;
    END IF;
    
    -- Check if profile exists (for debugging)
    SELECT EXISTS(
        SELECT 1 FROM user_profiles 
        WHERE user_id = target_user_uuid
    ) INTO profile_exists;
    
    IF NOT profile_exists THEN
        RAISE WARNING 'set_user_preference: Profile does not exist for user_id: %', target_user_uuid;
        RETURN FALSE;
    END IF;
    
    -- Convert TEXT to JSONB
    BEGIN
        pref_value_jsonb := pref_value::jsonb;
    EXCEPTION WHEN OTHERS THEN
        -- If conversion fails, wrap as a JSON string
        pref_value_jsonb := to_jsonb(pref_value);
    END;
    
    -- Update the preference using jsonb_set
    UPDATE user_profiles
    SET 
        preferences = jsonb_set(
            COALESCE(preferences, '{}'::jsonb),
            ARRAY[pref_key],
            pref_value_jsonb,
            true  -- create if missing
        ),
        updated_at = NOW()
    WHERE user_id = target_user_uuid;
    
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    
    IF rows_updated = 0 THEN
        RAISE WARNING 'set_user_preference: UPDATE returned 0 rows for user_id: %, pref_key: %, profile_exists: %', target_user_uuid, pref_key, profile_exists;
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
DECLARE
    get_func_count INTEGER;
    set_func_count INTEGER;
BEGIN
    -- Count how many get_user_preference functions exist
    SELECT COUNT(*) INTO get_func_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
    AND p.proname = 'get_user_preference';
    
    -- Count how many set_user_preference functions exist
    SELECT COUNT(*) INTO set_func_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
    AND p.proname = 'set_user_preference';
    
    IF get_func_count = 1 AND set_func_count = 1 THEN
        RAISE NOTICE 'Successfully fixed: Only one of each function exists';
    ELSE
        RAISE WARNING 'Warning: Found % get_user_preference and % set_user_preference functions. Manual cleanup may be needed.', get_func_count, set_func_count;
    END IF;
END $$;
