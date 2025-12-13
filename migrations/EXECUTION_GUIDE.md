# Database Normalization - Execution Guide

## Files Created

### Migrations (SQL):
1. `migrations/001_create_securities_table.sql` - Creates securities table
2. `migrations/002_update_views_with_securities.sql` - Updates views to JOIN
3. `migrations/003_remove_company_from_positions.sql` - Removes company column (⚠️ FINAL STEP)

### Scripts (Python):
1. `scripts/populate_securities_metadata.py` - Fetches yfinance data

---

## Execution Steps

### Step 1: Run Migration 001
```bash
# In Supabase SQL Editor, execute:
migrations/001_create_securities_table.sql
```

**Expected Result:** 
- Securities table created
- Populated with distinct tickers from portfolio_positions
- Indexes created

### Step 2: Populate Metadata
```bash
cd "c:\Users\cream\OneDrive\Documents\LLM-Micro-Cap-trading-bot"
python scripts/populate_securities_metadata.py
```

**Expected Result:**
- All tickers updated with company name, sector, industry
- Summary shows success/error counts

### Step 3: Run Migration 002
```bash
# In Supabase SQL Editor, execute:
migrations/002_update_views_with_securities.sql
```

**Expected Result:**
- `latest_positions` view updated to JOIN securities

### Step 4: Test Dashboard
Navigate to web dashboard and verify:
- [ ] Holdings Info table shows sector/industry
- [ ] Positions table displays correctly
- [ ] No errors in console

### Step 5: Update Code
Find and update all code that inserts into `portfolio_positions`:
- Remove `company` from INSERT statements
- Tickers should be in securities table first

### Step 6: Remove Company Column (⚠️ IRREVERSIBLE)
```bash
# BACKUP FIRST!
# Then in Supabase SQL Editor, execute:
migrations/003_remove_company_from_positions.sql
```

---

## Verification Queries

```sql
-- Check securities table
SELECT COUNT(*), 
       COUNT(sector) as with_sector,
       COUNT(industry) as with_industry
FROM securities;

-- Check view works
SELECT * FROM latest_positions LIMIT 5;

-- Find tickers missing metadata
SELECT ticker, company_name, sector, industry
FROM securities
WHERE sector IS NULL OR industry IS NULL;
```

---

## Rollback (if needed)

If issues after Step 6:
```sql
-- Restore company column
ALTER TABLE portfolio_positions ADD COLUMN company TEXT;

UPDATE portfolio_positions p
SET company = s.company_name
FROM securities s
WHERE p.ticker = s.ticker;
```
