-- =====================================================
-- FIX: Add fund_thesis_with_pillars view
-- =====================================================
-- Description: Creates a view that joins fund_thesis with fund_thesis_pillars
--              for convenient querying. Returns one row per pillar.
-- Date: 2025-01-27
-- =====================================================

-- Drop existing view if it exists
DROP VIEW IF EXISTS fund_thesis_with_pillars CASCADE;

-- Create view that joins fund_thesis with fund_thesis_pillars
CREATE VIEW fund_thesis_with_pillars AS
SELECT 
    ft.id as thesis_id,
    ft.fund,
    ft.title,
    ft.overview,
    ft.created_at as thesis_created_at,
    ft.updated_at as thesis_updated_at,
    ftp.id as pillar_id,
    ftp.name as pillar_name,
    ftp.allocation,
    ftp.thesis as pillar_thesis,
    ftp.pillar_order,
    ftp.created_at as pillar_created_at,
    ftp.updated_at as pillar_updated_at
FROM fund_thesis ft
LEFT JOIN fund_thesis_pillars ftp ON ft.id = ftp.thesis_id
ORDER BY ft.fund, ftp.pillar_order NULLS LAST;

-- Grant permissions on the view
GRANT SELECT ON fund_thesis_with_pillars TO authenticated;
GRANT SELECT ON fund_thesis_with_pillars TO service_role;

-- Add comment
COMMENT ON VIEW fund_thesis_with_pillars IS 'Joined view of fund_thesis and fund_thesis_pillars. Returns one row per pillar (or one row with NULL pillars if no pillars exist). Ordered by fund and pillar_order.';

