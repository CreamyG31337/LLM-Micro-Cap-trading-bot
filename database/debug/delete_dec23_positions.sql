-- Delete Dec 23, 2025 portfolio positions for Project Chimera
-- Run this in Supabase SQL Editor, then re-run the rebuild job

DELETE FROM portfolio_positions
WHERE fund = 'Project Chimera'
  AND date >= '2025-12-23 00:00:00+00'
  AND date <= '2025-12-23 23:59:59+00';

-- Check how many were deleted
SELECT 
    'Remaining Dec 23 positions' as check_name,
    COUNT(*) as count
FROM portfolio_positions
WHERE fund = 'Project Chimera'
  AND date >= '2025-12-23 00:00:00+00'
  AND date <= '2025-12-23 23:59:59+00';
