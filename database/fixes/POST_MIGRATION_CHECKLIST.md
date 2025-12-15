# Post-Migration Checklist

## ✅ Completed
- [x] Database migrations (DF_008, DF_009, DF_010)
- [x] Admin panel contributor access tab
- [x] RLS policies updated
- [x] Auto-grant access on signup

## 🔄 Code Updates Needed (Backward Compatible - Can Do Gradually)

### High Priority (Should Update Soon)

1. **Admin Panel - Contributions Tab** (`web_dashboard/pages/admin.py`)
   - Currently inserts using `fund` and `contributor` strings
   - Should also populate `fund_id` and `contributor_id`
   - **Status**: Works but not using new schema

2. **Contributor Ownership View** (`database/setup/05_contributions.sql`)
   - View still uses `fund` and `contributor` strings
   - Could be updated to join with `funds` and `contributors` tables
   - **Status**: Works but could be improved

### Medium Priority (Can Wait)

3. **Migration Script** (`web_dashboard/migrate_contributors.py`)
   - Still uses old format
   - Should be updated to create contributors and link properly
   - **Status**: Only needed if re-migrating

4. **Streamlit Utils** (`web_dashboard/streamlit_utils.py`)
   - Uses `contributor` string from fund_contributions
   - Could use `contributor_id` to join with contributors table
   - **Status**: Works fine, just not optimized

### Low Priority (Nice to Have)

5. **Console App** (`trading_script.py`, `portfolio/contributor_manager.py`)
   - Still writes to CSV files
   - Could be updated to write to database
   - **Status**: CSV is fine for now, backward compatible

## 🧪 Testing Checklist

### Database Tests
- [ ] Verify contributors table has all contributors
- [ ] Verify contributor_access has auto-granted records
- [ ] Verify fund_contributions has contributor_id populated
- [ ] Verify fund_contributions has fund_id populated
- [ ] Test RLS: User can only see their accessible contributors
- [ ] Test RLS: Admin can see all contributors

### Admin Panel Tests
- [ ] Grant access to a user for a contributor
- [ ] Revoke access from a user
- [ ] View current access relationships
- [ ] Add new contribution (should work with old columns)
- [ ] Edit contributor info

### Login/Auth Tests
- [ ] New user with matching email gets auto-granted access
- [ ] User can view their own contributor data
- [ ] User cannot view other contributors' data (unless granted)

### Application Tests
- [ ] Dashboard shows correct contributor data
- [ ] Investment metrics calculate correctly
- [ ] Ownership percentages calculate correctly

## 📝 Documentation Updates

- [x] Migration guide created
- [x] Design documents created
- [ ] Update main README if needed
- [ ] Update API documentation if needed

## 🚀 Optional Improvements (Future)

1. **Update Views** to use new foreign keys
2. **Add Database Triggers** to auto-populate contributor_id when inserting with contributor string
3. **Create Helper Functions** for common contributor operations
4. **Add Contributor Management UI** (beyond just access)
5. **Add Contributor Metadata** (KYC status, contact info, etc.)

## ⚠️ Important Notes

- **Old columns are kept** for backward compatibility
- **Existing code will continue to work** using `fund` and `contributor` strings
- **New code should use** `fund_id` and `contributor_id` for better performance
- **RLS policies work** with both old and new columns (fallback to email matching)

## 🐛 Known Issues / Limitations

1. **Contributions Tab** still uses old format - works but not optimal
2. **Views** still use string columns - could be optimized
3. **CSV files** still primary source for console app - database is secondary

## 📞 Support

If you encounter issues:
1. Check RLS policies are correct
2. Verify contributor_access records exist
3. Check that fund_id and contributor_id are populated
4. Review migration verification queries

