# Investigation: Why 44 Politicians Were Never Added to Database

## Summary
Found **445 analysis records** with committee assignment issues across **44 politicians**. All have invalid `politician_id` foreign keys pointing to non-existent politicians.

## Key Findings

### 1. **All Trades Created on Same Day**
- **Date**: December 29, 2025 (2025-12-29)
- All problematic trades were created within a short time window (04:42:25 - 04:42:27 UTC)
- This suggests a **batch import or backfill operation** rather than individual trade imports

### 2. **Invalid Foreign Keys**
- All 44 politicians have `politician_id` values that **do not exist** in the `politicians` table
- Example IDs: 5411, 5414, 5434, 5453, 5449, 5489, etc.
- These IDs are within a reasonable range (5400-5500), suggesting they might have existed at some point

### 3. **Politicians Don't Exist by Name Either**
- None of the 44 politicians exist in the database by name
- Examples: Joshua Gottheimer, Thomas Kean Jr, William Keating, Michael Burgess, etc.
- This means they were **never properly synced** to the database

### 4. **No NULL politician_id Values**
- There are **0 trades** with `politician_id = NULL` in the database
- This suggests that either:
  - A backfill script set invalid IDs instead of leaving them NULL
  - The import process set invalid IDs directly

## Root Cause Analysis

### Possible Scenarios:

#### Scenario A: Backfill Script Bug
- A backfill script (like `backfill_politician_ids_legacy.py`) may have:
  1. Created politicians with these IDs
  2. Set `politician_id` on trades
  3. Then the politicians were deleted (or never properly committed)
  
**Evidence**: The backfill script uses `get_or_create_politician()` which could create politicians, but if the transaction failed or politicians were deleted, the trades would be left with orphaned IDs.

#### Scenario B: Import Process Bug
- The `fetch_congress_trades_job()` sets `politician_id = None` when politician is not found
- But something else might have set invalid IDs later
  
**Evidence**: The current import code correctly sets `politician_id = None` when politician not found (line 3486-3503 in jobs.py)

#### Scenario C: Staging Migration Issue
- The `full_migration_staging_to_prod.py` script does **NOT** copy `politician_id` from staging
- It only copies the text `politician` field
- If staging had invalid `politician_id` values, they wouldn't be copied anyway

**Evidence**: The migration script (lines 169-186) doesn't include `politician_id` in the insert

#### Scenario D: Politicians Were Deleted
- Politicians might have been created with these IDs
- Then deleted from the database (perhaps during a cleanup or re-seed)
- But the foreign key constraint has `ON DELETE SET NULL`, so this shouldn't leave invalid IDs

**Evidence**: The schema (migration 25) has `ON DELETE SET NULL`, so deleted politicians should set `politician_id` to NULL, not leave invalid IDs.

## Most Likely Cause (UPDATED)

**Name Mismatch + Backfill Script Issue**:

1. **Politicians seeded from YAML**: The `seed_committees.py` script loads politicians from `legislators-current.yaml` with names in a specific format
2. **Trades have different names**: Trade data from FMP API uses different name formats (e.g., "Thomas Kean Jr" vs what's in YAML)
3. **Backfill script ran with `create_if_missing=True`**: 
   - Backfill script tried to look up politicians by trade name
   - Didn't find them (name mismatch)
   - Created new politicians with trade names, got IDs (5400-5500 range)
   - Set `politician_id` on trades to these new IDs
4. **Politicians later replaced**: When `seed_committees.py` ran, it inserted politicians from YAML with different names
   - The politicians created by backfill script were either:
     - Replaced by upsert (if bioguide_id matched)
     - Or left as duplicates with different names
   - But the trades still had the old IDs pointing to politicians that no longer exist

**Key Evidence**:
- All 44 politicians don't exist in database (not even with different names)
- Invalid IDs are in 5400-5500 range (suggesting they were auto-generated)
- Database was created "a few days ago" - timing matches backfill → seed sequence
- No name mappings exist for these politicians in `POLITICIAN_ALIASES`

## Affected Politicians (Top 10)

1. **Joshua Gottheimer** - 52 trades (politician_id: 5411)
2. **Thomas Kean Jr** - 42 trades (politician_id: 5414)
3. **William Keating** - 40 trades (politician_id: 5434)
4. **Michael Burgess** - 37 trades (politician_id: 5453)
5. **Earl Blumenauer** - 36 trades (politician_id: 5449)
6. **Valerie Hoyle** - 27 trades (politician_id: 5489)
7. **Thomas Carper** - 22 trades (politician_id: 5446)
8. **Peter Sessions** - 18 trades (politician_id: 5447)
9. **Lisa McClain** - 15 trades (politician_id: 5487)
10. **Kathy Manning** - 14 trades (politician_id: 5456)

## Impact

- **445 trades** have invalid `politician_id` references
- **AI analysis** correctly reports "no committee assignments found" because politicians don't exist
- **Conflict scores** are likely incorrect (defaulting to 0.0 or low scores)
- **Data integrity** issue: Foreign key constraint should prevent this, but it's not enforced or was bypassed

## Next Steps (When Ready to Fix)

1. **Run `sync_missing_politicians.py`** to add missing politicians to database
2. **Create a fix script** to:
   - Look up correct politician IDs by name
   - Update `politician_id` in `congress_trades` table
   - Set to NULL if politician truly doesn't exist
3. **Re-run analysis** on affected trades to get accurate conflict scores
4. **Investigate why foreign key constraint didn't prevent this** (check if constraint is active)

## Files Created for Investigation

- `web_dashboard/scripts/debug_committee_assignments.py` - Finds trades with committee assignment errors
- `web_dashboard/scripts/investigate_politician_ids.py` - Investigates invalid politician_id values
- `web_dashboard/scripts/check_missing_politicians.py` - Checks if politician IDs exist
- `web_dashboard/scripts/find_politicians_by_name.py` - Searches for politicians by name

