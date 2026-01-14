-- =====================================================
-- Datafix: Populate Missing User Full Names
-- =====================================================
-- This datafix populates user_profiles.full_name from contributors.name
-- where the user's email matches a contributor's email and full_name is NULL.
--
-- This handles the case where users were created without full_name but
-- their contributor record has a name (which is NOT NULL).
--
-- Note: If multiple users match the same contributor email, they will all
-- get the same name. Manual review needed for those cases.
--
-- IMPORTANT: If RLS policies block the UPDATE, run via Supabase service role
-- or use the Python script approach. The SECURITY DEFINER function should
-- bypass RLS, but if it doesn't work, use Supabase client with service role key.
-- =====================================================

-- Step 0a: DIAGNOSTIC - Check what emails exist in both tables
SELECT 
    'Users with NULL full_name' as check_type,
    up.email as email,
    up.full_name as name,
    'user_profiles' as source_table
FROM user_profiles up
WHERE up.full_name IS NULL
  AND up.email IS NOT NULL

UNION ALL

SELECT 
    'Contributors' as check_type,
    c.email as email,
    c.name as name,
    'contributors' as source_table
FROM contributors c
WHERE c.email IS NOT NULL

ORDER BY email, check_type;

-- Step 0b: DRY RUN - See what will be updated (run this to verify matches)
SELECT 
    up.email as user_email,
    up.full_name as current_full_name,
    c.name as contributor_name,
    c.email as contributor_email,
    'Will update to: ' || c.name as action
FROM user_profiles up
JOIN contributors c ON LOWER(TRIM(up.email)) = LOWER(TRIM(c.email))
WHERE up.full_name IS NULL
  AND up.email IS NOT NULL
  AND c.email IS NOT NULL
ORDER BY up.email;

-- Step 1: Create a SECURITY DEFINER function to bypass RLS for this update
CREATE OR REPLACE FUNCTION populate_user_full_names()
RETURNS TABLE(
    updated_count INTEGER,
    message TEXT
) AS $$
DECLARE
    update_count INTEGER;
BEGIN
    -- Update user_profiles.full_name from contributors.name where emails match
    -- Use case-insensitive email matching
    UPDATE user_profiles up
    SET full_name = c.name,
        updated_at = NOW()
    FROM contributors c
    WHERE up.full_name IS NULL
      AND up.email IS NOT NULL
      AND c.email IS NOT NULL
      AND LOWER(TRIM(up.email)) = LOWER(TRIM(c.email));
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    
    RETURN QUERY SELECT 
        update_count,
        format('Updated %s user profiles with names from contributors', update_count);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 1b: Run the function
SELECT * FROM populate_user_full_names();

-- Step 1c: Drop the function (cleanup)
DROP FUNCTION IF EXISTS populate_user_full_names();

-- Step 2: Show summary of updates
SELECT 
    '📊 Datafix Summary' as section,
    'Users updated' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM user_profiles
WHERE full_name IS NOT NULL
  AND updated_at >= NOW() - INTERVAL '1 minute'

UNION ALL

SELECT 
    '📊 Datafix Summary' as section,
    'Users still NULL' as metric,
    COUNT(*)::text as value,
    NULL::text as detail
FROM user_profiles
WHERE full_name IS NULL

UNION ALL

-- Show users that might need manual review (multiple users per contributor)
SELECT 
    '⚠️ Manual Review Needed' as section,
    c.name as metric,
    COUNT(*)::text as value,
    string_agg(up.email, ', ') as detail
FROM contributors c
JOIN user_profiles up ON LOWER(TRIM(c.email)) = LOWER(TRIM(up.email))
GROUP BY c.name, c.email
HAVING COUNT(*) > 1;

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Show all users with their names (for verification)
SELECT 
    up.email,
    up.full_name as user_full_name,
    c.name as contributor_name,
    c.email as contributor_email,
    CASE 
        WHEN up.full_name IS NULL AND c.name IS NOT NULL THEN '❌ Missing (will update)'
        WHEN up.full_name IS NULL AND c.name IS NULL THEN '❌ Missing (no contributor)'
        WHEN up.full_name = c.name THEN '✅ Matched'
        WHEN up.full_name IS NOT NULL AND c.name IS NOT NULL AND up.full_name != c.name THEN '⚠️ Different'
        ELSE '❓ Unknown'
    END as status
FROM user_profiles up
LEFT JOIN contributors c ON LOWER(TRIM(up.email)) = LOWER(TRIM(c.email))
ORDER BY 
    CASE WHEN up.full_name IS NULL THEN 0 ELSE 1 END,
    up.email;
