# Web Dashboard Known Issues and Solutions

## 🐛 Performance Chart Issues

### Issue: Chart Shows "No Data" When Fund is Selected

**Problem**: Performance chart works when no fund is selected but shows "no data" when a specific fund is selected.

**Root Cause**: The web dashboard has two different data loading modes:
- **No fund selected**: Uses fallback CSV calculation (works)
- **Fund selected**: Queries `performance_metrics` table in Supabase (fails if table is empty)

**Solution Options**:

1. **Quick Fix** - Populate the performance_metrics table:
   ```bash
   cd web_dashboard
   python calculate_real_performance.py
   ```

2. **Code Fix** - Modify `create_performance_chart()` in `app.py` to calculate directly from `portfolio_positions` instead of relying on `performance_metrics` table.

**Prevention**: Ensure `performance_metrics` table is populated whenever new portfolio data is added to Supabase.

**Files Affected**: 
- `web_dashboard/app.py` (lines 316-427)
- `web_dashboard/supabase_client.py` (lines 229-266)

---

## 🐛 Graph Normalization Issues

### Issue: Fund Performance Doesn't Start at 100 Like Benchmarks

**Problem**: Python graph generator shows fund performance starting "down a bit" while benchmarks correctly start at 100.

**Root Cause**: 
- Benchmarks normalized to start at 100 on first **trading day**
- Fund performance normalized to start at 100 on **baseline day** (day before first data)
- Result: Fund appears to underperform when it's actually performing well

**Solution**: Normalize both fund and benchmarks to start at 100 on the same reference day (first trading day).

**Code Changes Made**:
- Modified `Scripts and CSV Files/Generate_Graph.py` lines 523-537
- Updated `docs/GRAPH_NORMALIZATION_LOGIC.md`
- Added comprehensive fix documentation in `PERFORMANCE_GRAPH_FIX_SUMMARY.md`

**Prevention**: Always use consistent baseline dates for both fund and benchmark normalization.

---

## 🐛 Fund Dropdown Issues

### Issue: Dropdown Doesn't Change Displayed Data

**Problem**: Selecting a fund from the dropdown doesn't update the dashboard to show that fund's data.

**Root Cause**: 
- Race condition in initialization - `initDashboard()` loaded all functions in parallel
- Circular reload logic - changing fund called `initDashboard()` which reloaded funds list
- No separation between initial load and data reload

**Solution**: 
1. **Sequential Loading**: Load funds first, then load data in parallel
2. **Separate Reload Function**: Created `reloadDashboardData()` that doesn't reload funds
3. **Debug Logging**: Added console logs to track dropdown events

**Code Changes Made**:
- Modified `setupFundSelection()` to call `reloadDashboardData()` instead of `initDashboard()`
- Modified `initDashboard()` to load funds sequentially before other data
- Added `reloadDashboardData()` function for fund-specific reloads
- Added console logging for debugging

**Testing**: 
- Use browser console (F12) to verify logs appear
- Check URL updates when fund selected
- Verify data changes for each fund selection

**Prevention**: Use sequential loading for dependencies, separate init from reload logic.

---

## 📊 Data Analysis Findings

### Portfolio Spike Analysis (September 2nd)

**Finding**: Large portfolio value increase on 2025-09-02 was legitimate trading activity, not a data error.

**Cause**: 
- Added 4 ATYR shares at $5.44 (+$21.76 investment)
- ATYR market price appreciation to $5.65
- Closed IINN position (small loss)
- **Total legitimate increase**: $2.32 in portfolio value

**Documentation**: Portfolio movements should always be cross-referenced with trade log for verification.

---

## 🔧 Investigation Priorities

### High Priority
- [ ] **Audit all web dashboard API endpoints** for similar data source inconsistencies
- [ ] **Document web dashboard data flow** from Supabase tables to UI components
- [ ] **Create integration tests** for fund-specific data filtering

### Medium Priority  
- [ ] **Performance metrics automation** - Auto-populate performance_metrics when new data is added
- [ ] **Data validation checks** - Ensure portfolio_positions and performance_metrics stay in sync
- [ ] **Better error handling** - Graceful fallbacks when Supabase queries fail

### Low Priority
- [ ] **Chart performance optimization** - Cache chart data for faster loading
- [ ] **Real-time updates** - WebSocket integration for live portfolio updates

---

## 🛡️ Prevention Strategies

1. **Automated Testing**: Add tests that verify fund-specific queries return data
2. **Data Pipeline Monitoring**: Monitor Supabase table population
3. **Documentation**: Keep API endpoint documentation updated
4. **Validation**: Regular data consistency checks between tables

---

## 📝 Related Files

- `web_dashboard/app.py` - Main Flask application
- `web_dashboard/supabase_client.py` - Database client
- `Scripts and CSV Files/Generate_Graph.py` - Python graph generator
- `docs/GRAPH_NORMALIZATION_LOGIC.md` - Graph calculation documentation
- `PERFORMANCE_GRAPH_FIX_SUMMARY.md` - Complete fix documentation