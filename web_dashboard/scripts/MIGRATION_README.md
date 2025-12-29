# Congress Trades Migration Scripts

## ✅ Recommended Script

**`safe_migrate_staging_to_production.py`** - Safe migration that preserves AI analysis

### Usage:
```bash
# Dry run (see what would change)
python web_dashboard/scripts/safe_migrate_staging_to_production.py --dry-run

# Real migration
python web_dashboard/scripts/safe_migrate_staging_to_production.py
```

### How it works:
1. **UPDATE** existing trades (preserves IDs → AI analysis stays valid)
2. **INSERT** new trades (auto-generates new IDs)
3. No data loss, AI analysis foreign keys remain intact

### Safe for:
- ✅ Incremental updates
- ✅ Preserving AI analysis
- ✅ Production use

---

## ⚠️ Deprecated Scripts

**`full_migration_supabase_only.py`** - DANGEROUS, causes data loss

### Why deprecated:
- ❌ Deletes ALL production data
- ❌ Reloads without preserving IDs
- ❌ BREAKS AI analysis foreign keys
- ❌ Loses hours of GPU computation time

### When to use:
- Only if you want to completely wipe and start fresh
- You must delete AI analysis manually afterward
- **Not recommended for normal operations**

---

## Migration Workflow

1. **Scrape to staging:**
   ```bash
   python web_dashboard/scripts/seed_congress_trades_staging.py
   ```

2. **Validate staging:**
   ```bash
   python web_dashboard/scripts/validate_staging_batch.py <batch-id>
   ```

3. **Migrate safely:**
   ```bash
   python web_dashboard/scripts/safe_migrate_staging_to_production.py
   ```

4. **Verify:**
   - Check production count
   - Verify AI analysis still works (0/N shouldn't be 0/N anymore)

---

## AI Analysis Notes

AI analysis is stored in PostgreSQL `congress_trades_analysis` table with foreign key to `congress_trades.id`.

If migration breaks AI analysis:
```bash
python web_dashboard/scripts/fix_ai_analysis_references.py
```

This deletes orphaned analyses - they'll regenerate on next AI run.
