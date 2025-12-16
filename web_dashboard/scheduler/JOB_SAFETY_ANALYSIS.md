# Portfolio Price Update Job - Safety Analysis

## Overview
This document outlines potential issues with the `update_portfolio_prices_job` and how they are addressed.

**Last Updated:** 2025-01-27

---

## ✅ Issues Addressed

### 1. **Exchange Rate Dependency** ✅ RESOLVED
**Issue:** Job might run before exchange rates are fetched, causing currency conversion issues.

**Analysis:**
- **NOT AN ISSUE**: Portfolio positions are stored in their **native currency** (USD or CAD)
- Exchange rates are only used for **display/calculation** purposes, not for saving positions
- The job saves positions with their original currency from trade log
- Currency conversion happens at display time, not storage time

**Resolution:** No changes needed - exchange rates are not required for this job.

---

### 2. **Concurrent Execution** ✅ RESOLVED
**Issue:** Job might run multiple times simultaneously, causing race conditions or duplicate data.

**Protection Layers:**
1. **APScheduler `max_instances=1`**: Prevents scheduler from starting multiple instances
2. **Global Lock (`_update_prices_job_running`)**: Backup protection in case scheduler fails
3. **Job Coalescing**: Multiple missed executions combined into one

**Resolution:** Triple-layer protection ensures only one instance runs at a time.

---

### 3. **Duplicate Data Prevention** ✅ RESOLVED
**Issue:** Multiple runs could create duplicate snapshots for the same day.

**Protection:**
- **Comprehensive Delete**: Deletes ALL positions for target date before inserting
- **Batch Deletion**: Handles large datasets (1000 records at a time)
- **Date Range Filtering**: Uses precise date range to catch all records
- **Atomic Per Fund**: Delete+insert happens per fund (if insert fails, next run fixes it)

**Resolution:** Ensures only one snapshot per day per fund.

---

### 4. **Partial Failures** ✅ RESOLVED
**Issue:** Some tickers might fail to fetch prices while others succeed.

**Handling:**
- **Skip Failed Tickers**: Continues with successful ones
- **Log Warnings**: Records which tickers failed for debugging
- **Skip Fund if All Fail**: If ALL tickers fail, skips the fund entirely (no empty snapshot)
- **Continue Processing**: Other funds continue even if one fund fails

**Resolution:** Graceful degradation - partial updates are better than no updates.

---

### 5. **Transaction Safety** ✅ RESOLVED
**Issue:** Delete might succeed but insert fail, leaving missing data.

**Handling:**
- **Per-Fund Atomicity**: Delete+insert happens per fund
- **Error Recovery**: If insert fails, next run (15 min) will fix it
- **Historical Data Preserved**: Only target date is affected
- **Logging**: Errors are logged for monitoring

**Note:** Supabase doesn't support multi-table transactions easily, so we rely on:
- Fast recovery (next run fixes it)
- Historical data preservation (only one day affected)
- Comprehensive error logging

**Resolution:** Acceptable trade-off - missing data for 15 minutes is better than blocking all updates.

---

### 6. **Job Overlap** ✅ RESOLVED
**Issue:** Job might take longer than 15 minutes, causing overlapping executions.

**Protection:**
- **`max_instances=1`**: APScheduler won't start new instance if one is running
- **Global Lock**: Additional safety check
- **Coalescing**: Missed executions combined into one

**Resolution:** Job will complete before next execution starts.

---

### 7. **Market Holiday Logic** ✅ RESOLVED
**Issue:** Job might skip updates when only one market is closed.

**Logic:**
- **"any" Market Check**: Updates if EITHER US or Canadian market is open
- **Only Skip if Both Closed**: Skips only when BOTH markets are closed
- **Last Trading Day Fallback**: If both closed today, updates last trading day

**Examples:**
- ✅ Canada Day (US open) → Updates
- ✅ US Independence Day (Canada open) → Updates
- ❌ Christmas (both closed) → Skips
- ❌ Weekend (both closed) → Skips

**Resolution:** Updates whenever possible, only skips when both markets closed.

---

### 8. **Empty Portfolio Handling** ✅ RESOLVED
**Issue:** Job might fail or create empty snapshots for funds with no positions.

**Handling:**
- **Early Return**: If no trades found, skips fund gracefully
- **No Empty Snapshots**: If no active positions, skips update
- **All Tickers Failed**: If all price fetches fail, skips fund (no empty snapshot)

**Resolution:** Handles empty portfolios gracefully without errors.

---

### 9. **Database Connection Loss** ✅ RESOLVED
**Issue:** Database connection might be lost mid-update.

**Handling:**
- **Per-Fund Try/Catch**: Each fund processed independently
- **Continue on Error**: One fund failure doesn't stop others
- **Comprehensive Logging**: All errors logged with context
- **Job Completion**: Job always completes (logs success/failure)

**Resolution:** Resilient to connection issues - continues with other funds.

---

### 10. **Target Date Calculation** ✅ RESOLVED
**Issue:** Target date might be calculated incorrectly.

**Logic:**
- **Today if Any Market Open**: Uses today if at least one market is open
- **Last Trading Day Fallback**: If both closed, finds last trading day (up to 7 days back)
- **Skip if No Trading Day**: If no trading day found in 7 days, skips gracefully
- **Logging**: Target date is logged for debugging

**Resolution:** Robust date calculation with fallbacks and validation.

---

## 🔄 Job Execution Flow

```
1. Check if already running → Skip if yes
2. Determine target date (today or last trading day)
3. Get all funds from database
4. For each fund:
   a. Rebuild positions from trade log (source of truth)
   b. Fetch current prices for all tickers
   c. Skip failed tickers, continue with successful ones
   d. Delete ALL existing positions for target date
   e. Insert updated positions
   f. Log results
5. Log overall job completion
6. Release lock
```

---

## 📊 Monitoring & Debugging

### Log Messages
- `Starting portfolio price update job...` - Job started
- `Target date for price update: YYYY-MM-DD` - Date being updated
- `Processing fund: FundName` - Fund being processed
- `Found N active positions` - Positions found
- `Successfully fetched prices for N/M tickers` - Price fetch summary
- `Deleted N existing positions` - Cleanup summary
- `✅ Updated N positions` - Success per fund
- `❌ Error processing fund` - Error per fund (continues with others)
- `✅ Updated N positions across M fund(s)` - Overall success

### Job Status
- Check scheduler admin UI for job status
- View execution logs for each job run
- Monitor for repeated failures

---

## ⚠️ Known Limitations

1. **No True Transactions**: Supabase doesn't easily support multi-table transactions
   - **Impact**: If insert fails after delete, data missing until next run (15 min)
   - **Mitigation**: Fast recovery, comprehensive logging

2. **Price Fetch Failures**: Some tickers might fail to fetch prices
   - **Impact**: Those positions won't be updated
   - **Mitigation**: Continues with successful ones, logs failures

3. **Network Issues**: API calls might timeout or fail
   - **Impact**: Price fetches might fail
   - **Mitigation**: Uses cache as fallback, continues with available data

---

## 🎯 Best Practices

1. **Monitor Job Logs**: Check scheduler admin UI regularly
2. **Watch for Failures**: Investigate repeated ticker failures
3. **Verify Data**: Spot-check dashboard to ensure prices are updating
4. **Check Exchange Rates**: Ensure exchange rate job is running (for display, not storage)

---

## 🔧 Troubleshooting

### Job Not Running
- Check scheduler status in admin UI
- Verify job is enabled (`enabled_by_default=True`)
- Check for errors in logs

### Prices Not Updating
- Check if job is running (scheduler admin)
- Verify market is open (or use last trading day)
- Check for API failures in logs
- Verify funds exist in database

### Duplicate Data
- Should not happen (comprehensive delete)
- If it does, check delete query logic
- Verify date range filtering is correct

### Missing Data
- Check if insert failed after delete
- Wait for next run (15 min) - should auto-fix
- Check error logs for specific failures

