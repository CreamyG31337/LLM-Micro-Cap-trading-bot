# Backfill Script Analysis

## Found Script
**Location**: `web_dashboard/scripts/archive/backfill_politician_ids_legacy.py`

## Issues Found

### Issue 1: No Validation of Created Politician IDs
**Lines 84-91**: The script calls `get_or_create_politician()` which can create new politicians, but:
- If politician creation fails silently, `politician_id` could be `None` but the script continues
- If politician is created but transaction rolls back, trades get invalid IDs
- No validation that the returned `politician_id` actually exists in database

**Problem Code**:
```python
politician_id = get_or_create_politician(
    client,
    politician_name,
    party=party,
    state=state,
    chamber=chamber,
    create_if_missing=not dry_run  # Creates politicians if missing!
)

if politician_id:
    trade_to_update['politician_id'] = politician_id
    updates_batch.append(trade_to_update)
```

### Issue 2: No Foreign Key Validation
**Lines 96-99**: The script sets `politician_id` without verifying:
- The ID exists in the `politicians` table
- The foreign key constraint is satisfied
- The politician wasn't deleted between lookup and update

### Issue 3: Bulk Upsert Without Validation
**Lines 108-118**: The script does bulk upsert without checking:
- If any `politician_id` values are invalid
- If foreign key constraints will fail
- If politicians exist before updating trades

**Problem Code**:
```python
if updates_batch and not dry_run:
    client.supabase.table('congress_trades').upsert(updates_batch).execute()
    # No validation that politician_id values are valid!
```

### Issue 4: Only Processes NULL Values
**Line 52**: The script only processes trades where `politician_id IS NULL`:
```python
.is_('politician_id', 'null')
```

This means:
- It wouldn't have created the invalid IDs we found (those trades already have IDs)
- **BUT**: If a previous version of this script ran without the NULL check, it could have set invalid IDs
- Or if politicians were deleted after IDs were set, we'd have orphaned IDs

## Root Cause Hypothesis

The invalid IDs (5400-5500 range) were likely set by:

1. **Version of script without NULL check**: An earlier version that processed ALL trades, not just NULL ones
2. **Politicians created then deleted**: Script created politicians, set IDs on trades, then politicians were deleted (but FK constraint didn't fire)
3. **Transaction rollback**: Politicians were created in a transaction that rolled back, but trades were updated in a separate transaction

## Fixes Needed

### Fix 1: Add Validation Before Setting politician_id
```python
# After getting politician_id, validate it exists
if politician_id:
    # Validate politician exists
    validation = client.supabase.table('politicians')\
        .select('id')\
        .eq('id', politician_id)\
        .limit(1)\
        .execute()
    
    if not validation.data:
        # Politician doesn't exist - skip this trade
        failed.append({
            'trade_id': trade['id'],
            'politician': politician_name,
            'reason': f'Politician ID {politician_id} does not exist in database'
        })
        continue
```

### Fix 2: Add Validation Before Bulk Upsert
```python
# Before upsert, validate all politician_ids exist
valid_politician_ids = set()
for trade in updates_batch:
    pid = trade.get('politician_id')
    if pid:
        valid_politician_ids.add(pid)

if valid_politician_ids:
    # Check all IDs exist
    validation = client.supabase.table('politicians')\
        .select('id')\
        .in_('id', list(valid_politician_ids))\
        .execute()
    
    valid_ids = {p['id'] for p in validation.data}
    invalid_trades = [t for t in updates_batch if t.get('politician_id') not in valid_ids]
    
    if invalid_trades:
        print(f"   [WARNING] {len(invalid_trades)} trades have invalid politician_id - skipping")
        updates_batch = [t for t in updates_batch if t.get('politician_id') in valid_ids]
```

### Fix 3: Don't Create Politicians Automatically
Instead of `create_if_missing=True`, the script should:
1. Only set `politician_id` if politician already exists
2. Log missing politicians for manual review
3. Run `sync_missing_politicians.py` first to ensure all politicians exist

### Fix 4: Add Foreign Key Constraint Check
Before updating, verify the foreign key constraint is active and will prevent invalid IDs.

## Recommended Fix Strategy

1. **Fix the backfill script** to add validation
2. **Create a new safe backfill script** that:
   - Only processes NULL values (current behavior is correct)
   - Validates all politician_ids before setting them
   - Doesn't create politicians automatically
   - Requires running `sync_missing_politicians.py` first
3. **Add a validation script** to check for invalid politician_ids before running backfill

