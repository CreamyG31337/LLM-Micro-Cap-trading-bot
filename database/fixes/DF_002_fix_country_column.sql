-- Fix: Expand country column size
-- The country column was too small (VARCHAR(10)) causing errors for longer country names
-- like "Switzerland" (11 chars)

ALTER TABLE securities ALTER COLUMN country TYPE VARCHAR(50);
