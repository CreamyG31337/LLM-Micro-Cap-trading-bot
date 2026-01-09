-- =====================================================
-- USER PREFERENCES SCHEMA
-- =====================================================
-- Adds preferences column to user_profiles for storing
-- user-specific settings like timezone, display options, etc.
-- =====================================================

-- Add preferences column to user_profiles (JSONB for flexibility)
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- Create index on preferences for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_preferences ON user_profiles USING GIN (preferences);

-- Add comment explaining the preferences structure
COMMENT ON COLUMN user_profiles.preferences IS 'User preferences stored as JSON. Common keys: timezone (e.g., "America/Los_Angeles"), date_format, etc.';

-- =====================================================
-- HELPER FUNCTIONS FOR PREFERENCES
-- =====================================================

-- Function to get a user preference value
-- Returns the JSONB value for the given key, or NULL if not found
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
    
    -- Use -> operator to get the JSONB value for the key
    -- This returns NULL if the key doesn't exist
    SELECT preferences->pref_key INTO pref_value
    FROM user_profiles
    WHERE user_id = user_uuid;
    
    -- Return the value (could be NULL if key doesn't exist, or the actual JSONB value)
    RETURN pref_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to set a user preference value
-- Accepts TEXT and converts to JSONB (for RPC calls from Python)
-- UUID parameter is optional - if NULL, uses auth.uid() internally
CREATE OR REPLACE FUNCTION set_user_preference(
    pref_key TEXT, 
    pref_value TEXT,
    user_uuid UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_uuid UUID;
    rows_updated INTEGER;
    pref_value_jsonb JSONB;
BEGIN
    -- Use provided user_uuid or fall back to auth.uid()
    IF user_uuid IS NULL THEN
        target_user_uuid := auth.uid();
    ELSE
        target_user_uuid := user_uuid;
    END IF;
    
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

-- Function to get all user preferences
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
    
    RETURN user_prefs;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SCHEMA COMPLETE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ User preferences schema created successfully!';
    RAISE NOTICE '📝 Added preferences JSONB column to user_profiles';
    RAISE NOTICE '🔧 Helper functions created: get_user_preference, set_user_preference, get_user_preferences';
END $$;

