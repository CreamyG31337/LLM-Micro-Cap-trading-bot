-- =====================================================
-- Verification: Check if contributors table exists and is accessible
-- =====================================================
-- Run this to verify the contributors table was created successfully
-- =====================================================

-- Check if table exists
SELECT 
    'Table Exists Check' as check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'contributors'
        ) THEN '✅ Contributors table exists'
        ELSE '❌ Contributors table NOT found'
    END as status,
    NULL::text as detail

UNION ALL

-- Check table structure
SELECT 
    'Table Structure' as check_type,
    column_name as status,
    data_type || COALESCE('(' || character_maximum_length::text || ')', '') as detail
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'contributors'
ORDER BY ordinal_position

UNION ALL

-- Check row count
SELECT 
    'Data Check' as check_type,
    'Total contributors' as status,
    COUNT(*)::text as detail
FROM contributors

UNION ALL

-- Check contributor_access table
SELECT 
    'Table Exists Check' as check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'contributor_access'
        ) THEN '✅ Contributor_access table exists'
        ELSE '❌ Contributor_access table NOT found'
    END as status,
    NULL::text as detail

UNION ALL

-- Check contributor_access row count
SELECT 
    'Data Check' as check_type,
    'Total access records' as status,
    COUNT(*)::text as detail
FROM contributor_access

UNION ALL

-- Check RLS status
SELECT 
    'RLS Status' as check_type,
    tablename as status,
    CASE WHEN rowsecurity THEN 'RLS Enabled' ELSE 'RLS Disabled' END as detail
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('contributors', 'contributor_access')
ORDER BY tablename;

