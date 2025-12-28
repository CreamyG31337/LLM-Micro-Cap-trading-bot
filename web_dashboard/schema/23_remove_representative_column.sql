-- MIGRATION: Remove redundant representative column
-- The representative field is redundant (duplicates politician) and unused in the application.

ALTER TABLE congress_trades
DROP COLUMN IF EXISTS representative;
