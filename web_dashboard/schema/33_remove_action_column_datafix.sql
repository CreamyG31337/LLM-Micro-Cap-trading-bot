-- Migration: Remove action column dependency and datafix Webull imports
-- This migration:
-- 1. Updates all rows with "Imported from Webull" to append " BUY" to the reason field
-- 2. Optionally drops the action column if it exists (commented out for safety)
-- Run this in Supabase Dashboard > SQL Editor

-- Step 1: Datafix - Append " BUY" to all Webull import reasons
-- This ensures action can be inferred correctly from reason field
UPDATE trade_log 
SET reason = reason || ' BUY' 
WHERE reason LIKE '%Imported from Webull%'
  AND reason NOT LIKE '% BUY%';  -- Avoid appending multiple times

-- Step 2: (Optional) Drop the action column if it exists
-- Uncomment the following lines if you want to remove the column entirely
-- Note: Only do this if you're sure no other systems depend on it
-- ALTER TABLE trade_log DROP COLUMN IF EXISTS action;

-- Verification query (run separately to check)
-- SELECT 
--     COUNT(*) as total_rows,
--     COUNT(CASE WHEN reason LIKE '%Imported from Webull%' THEN 1 END) as webull_imports,
--     COUNT(CASE WHEN reason LIKE '%Imported from Webull% BUY%' THEN 1 END) as webull_fixed
-- FROM trade_log;

