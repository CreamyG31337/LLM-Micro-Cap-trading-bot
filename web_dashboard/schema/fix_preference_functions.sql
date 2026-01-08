-- Fix set_user_preference to accept user_uuid parameter (like is_admin does)
-- This allows Flask to pass the user ID explicitly instead of relying on auth.uid()

CREATE OR REPLACE FUNCTION set_user_preference(pref_key TEXT, pref_value TEXT, user_uuid UUID DEFAULT NULL)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_uuid UUID;
    rows_updated INTEGER;
    pref_value_jsonb JSONB;
BEGIN
    -- Use provided user_uuid, fall back to auth.uid()
    target_user_uuid := COALESCE(user_uuid, auth.uid());
    
    IF target_user_uuid IS NULL THEN
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
    
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Also fix get_user_preference to accept user_uuid parameter
CREATE OR REPLACE FUNCTION get_user_preference(pref_key TEXT, user_uuid UUID DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    target_user_uuid UUID;
    pref_value JSONB;
BEGIN
    -- Use provided user_uuid, fall back to auth.uid()
    target_user_uuid := COALESCE(user_uuid, auth.uid());
    
    IF target_user_uuid IS NULL THEN
        RETURN NULL;
    END IF;
    
    SELECT preferences->pref_key INTO pref_value
    FROM user_profiles
    WHERE user_id = target_user_uuid;
    
    RETURN pref_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
