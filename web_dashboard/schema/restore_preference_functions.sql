-- =====================================================
-- RESTORE ORIGINAL PREFERENCE FUNCTIONS (NO PARAMETERS)
-- =====================================================

-- 1. Restore get_user_preference (Singular)
CREATE OR REPLACE FUNCTION get_user_preference(pref_key TEXT)
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
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 2. Restore set_user_preference
CREATE OR REPLACE FUNCTION set_user_preference(pref_key TEXT, pref_value TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    user_uuid UUID;
    rows_updated INTEGER;
    pref_value_jsonb JSONB;
BEGIN
    user_uuid := auth.uid();
    
    IF user_uuid IS NULL THEN
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
    WHERE user_id = user_uuid;
    
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 3. Restore get_user_preferences (Plural)
CREATE OR REPLACE FUNCTION get_user_preferences()
RETURNS JSONB AS $$
DECLARE
    user_uuid UUID;
    user_prefs JSONB;
BEGIN
    user_uuid := auth.uid();
    
    IF user_uuid IS NULL THEN
        RETURN '{}'::jsonb;
    END IF;
    
    SELECT COALESCE(preferences, '{}'::jsonb) INTO user_prefs
    FROM user_profiles
    WHERE user_id = user_uuid;
    
    RETURN COALESCE(user_prefs, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
