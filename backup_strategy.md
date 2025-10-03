# 🔄 Backup Strategy for Trading Bot

## 🛡️ **Current Data Protection**

### **1. CSV Data Backups (Already in Place)**
- **Location**: `trading_data/funds/Project Chimera/backups/`
- **Automatic**: System creates backups before major operations
- **Retention**: Multiple timestamped backups available
- **Status**: ✅ **PROTECTED** - Original CSV data is safe

### **2. Supabase Data Backup**
- **Database**: PostgreSQL with built-in backup capabilities
- **RLS**: Row Level Security protects data access
- **Replication**: Supabase handles automatic backups
- **Status**: ✅ **PROTECTED** - Cloud database has redundancy

## 🔄 **Recovery Procedures**

### **If Supabase Issues Occur:**
```bash
# 1. Switch back to CSV immediately
python simple_repository_switch.py csv

# 2. Verify CSV data is intact
python trading_script.py --validate-only

# 3. Continue with local CSV operations
```

### **If CSV Data Issues Occur:**
```bash
# 1. Check backup directory
ls trading_data/funds/Project\ Chimera/backups/

# 2. Restore from most recent backup
cp trading_data/funds/Project\ Chimera/backups/llm_portfolio_update.csv.backup_YYYYMMDD_HHMMSS.csv trading_data/funds/Project\ Chimera/llm_portfolio_update.csv

# 3. Verify restoration
python trading_script.py --validate-only
```

### **If Both Systems Have Issues:**
```bash
# 1. Check git history for data files
git log --oneline trading_data/funds/Project\ Chimera/

# 2. Restore from git if needed
git checkout HEAD~1 -- trading_data/funds/Project\ Chimera/llm_portfolio_update.csv

# 3. Re-run migration if needed
python simple_migrate.py
```

## 🚨 **Emergency Recovery Commands**

### **Quick Data Verification:**
```bash
# Check CSV data integrity
python trading_script.py --validate-only

# Check Supabase data
python simple_repository_switch.py test

# Compare data between systems
python web_dashboard/verify_migration.py
```

### **Full System Reset:**
```bash
# 1. Switch to CSV (safe mode)
python simple_repository_switch.py csv

# 2. Verify CSV data
python trading_script.py --validate-only

# 3. If CSV is good, re-migrate to Supabase
python simple_migrate.py

# 4. Switch back to Supabase
python simple_repository_switch.py supabase
```

## 📊 **Data Integrity Checks**

### **Before Any Major Changes:**
1. ✅ Verify CSV data is valid
2. ✅ Create timestamped backup
3. ✅ Test repository switch works
4. ✅ Verify Supabase connection
5. ✅ Run data validation

### **After Any Changes:**
1. ✅ Test both CSV and Supabase modes
2. ✅ Verify data consistency
3. ✅ Run full system validation
4. ✅ Document any issues found

## 🎯 **Risk Mitigation**

### **Low Risk Operations:**
- ✅ Reading data (both CSV and Supabase)
- ✅ Switching between repositories
- ✅ Running validation checks

### **Medium Risk Operations:**
- ⚠️ Data migration (backup first)
- ⚠️ Web dashboard deployment (test locally)
- ⚠️ Schema changes (verify compatibility)

### **High Risk Operations:**
- 🚨 Modifying production CSV files
- 🚨 Database schema changes
- 🚨 Authentication changes

## 🔧 **Monitoring Commands**

```bash
# Check current repository status
python simple_repository_switch.py status

# Test current setup
python simple_repository_switch.py test

# Validate data integrity
python trading_script.py --validate-only

# Check Supabase connection
python web_dashboard/simple_migration_test.py
```

---

**Remember: CSV data is always the source of truth. Supabase is a copy for web dashboard access.**
