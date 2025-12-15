-- =====================================================
-- DF_007: FIX UNREGISTERED CONTRIBUTORS
-- =====================================================
-- Updates list_unregistered_contributors function to include
-- contributors who don't have an email address set
-- =====================================================

-- Redefine the function to allow null/empty emails
CREATE OR REPLACE FUNCTION list_unregistered_contributors()
RETURNS TABLE(
    contributor TEXT,
    email TEXT,
    funds TEXT[],
    total_contribution DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fc.contributor::TEXT,
        COALESCE(fc.email, '')::TEXT as email,
        ARRAY_AGG(DISTINCT fc.fund)::TEXT[] as funds,
        SUM(CASE 
            WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
            WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
            ELSE 0 
        END) as total_contribution
    FROM fund_contributions fc
    WHERE 
      -- Include if email is null/empty
      (fc.email IS NULL OR fc.email = '')
      OR 
      -- OR if email exists but doesn't match a user
      (
          fc.email IS NOT NULL 
          AND fc.email != '' 
          AND NOT EXISTS (
              SELECT 1 FROM auth.users au 
              WHERE normalize_email(au.email) = normalize_email(fc.email)
          )
      )
    GROUP BY fc.contributor, fc.email
    HAVING SUM(CASE 
        WHEN fc.contribution_type = 'CONTRIBUTION' THEN fc.amount 
        WHEN fc.contribution_type = 'WITHDRAWAL' THEN -fc.amount 
        ELSE 0 
    END) > 0
    ORDER BY fc.contributor;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ DF_007: Unregistered contributors function updated to include missing emails';
END $$;
