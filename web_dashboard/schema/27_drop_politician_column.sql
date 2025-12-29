-- Migration 27: Drop Redundant Politician Text Column
-- Purpose: Complete the normalization by removing the 'politician' text column
-- ensuring the politicians table is the single source of truth.

-- Pre-requisites:
-- 1. Ensure all code references are updated to use 'congress_trades_enriched' view
-- 2. Ensure view is created (Migration 26)
-- 3. Ensure 'politician_id' is populated for all rows (Migration 25 + Backfill)

-- Drop the column
ALTER TABLE congress_trades DROP COLUMN politician;

