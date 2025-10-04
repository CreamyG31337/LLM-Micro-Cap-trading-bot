# Web Dashboard Testing Checklist

## 🧪 Pre-Deployment Testing

### Performance Chart Testing
- [ ] Chart loads without fund selected
- [ ] Chart loads with each available fund selected
- [ ] Chart displays correct date range
- [ ] Chart shows performance starting at 100 baseline
- [ ] Chart handles empty data gracefully
- [ ] Chart displays correct fund name in title

### API Endpoint Testing
- [ ] `/api/portfolio` works without fund parameter
- [ ] `/api/portfolio?fund=X` works for each fund
- [ ] `/api/performance-chart` works without fund parameter  
- [ ] `/api/performance-chart?fund=X` works for each fund
- [ ] `/api/funds` returns correct list of available funds
- [ ] `/api/recent-trades?fund=X` filters correctly by fund

### Data Consistency Testing
- [ ] `portfolio_positions` table has data for each fund
- [ ] `performance_metrics` table is populated (not empty)
- [ ] Fund names consistent across all tables
- [ ] Dates are properly formatted and timezone-aware
- [ ] Currency conversions working correctly

### Authentication Testing
- [ ] Fund access control working (users see only assigned funds)
- [ ] Unauthorized fund access properly blocked
- [ ] Admin functions require admin privileges
- [ ] Login/logout flow working correctly

## 🐛 Known Issue Verification

### Performance Chart Issue
Test the specific bug we found:

1. **Test No Fund Selected**:
   - Navigate to dashboard
   - Don't select any fund
   - Verify chart shows data
   
2. **Test Fund Selection**:
   - Select "RRSP Lance Webull" from dropdown
   - Verify chart shows data (not "no data")
   - Select "Project Chimera" from dropdown  
   - Verify chart shows data (not "no data")

### Fund Dropdown Issue
Test the dropdown functionality:

1. **Test Dropdown Populates**:
   - Page loads successfully
   - Dropdown shows "Select Fund" default option
   - Dropdown shows all available fund names
   - Open browser console (F12) - should see "Initializing dashboard..." and "Dashboard initialized successfully"

2. **Test Fund Selection Changes Data**:
   - Select a fund from dropdown
   - Console should show "Fund changed to: [fund name]"
   - Console should show "Reloading dashboard data for selected fund..."
   - URL should update with `?fund=[fund name]`
   - Dashboard metrics should update
   - Positions should show only that fund's data
   - Chart should update for selected fund

3. **Test Fund Switching**:
   - Select first fund → verify data updates
   - Select different fund → verify data changes
   - Select "Select Fund" option → verify shows all funds data

### Graph Normalization Issue
Test the Python graph generator:

1. **Run Graph Generator**:
   ```bash
   cd "Scripts and CSV Files"
   python Generate_Graph.py --fund "RRSP Lance Webull"
   ```
   
2. **Verify Normalization**:
   - Both fund and benchmark lines start at same baseline (around 100)
   - No "fund starts down a bit" issue
   - Performance comparison is fair and accurate

## 🔍 Data Quality Checks

### Database Health Check
```bash
# Check if tables have data
cd web_dashboard
python -c "
import os
import requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_ANON_KEY')
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

# Check each table
for table in ['portfolio_positions', 'performance_metrics', 'trade_log']:
    resp = requests.get(f'{url}/rest/v1/{table}', 
                       headers=headers, 
                       params={'limit': '1'})
    count = len(resp.json()) if resp.status_code == 200 else 0
    print(f'{table}: {\"✅ Has data\" if count > 0 else \"❌ Empty\"}')
"
```

### Fund Data Consistency
```bash
# Verify all funds have data in all required tables
cd web_dashboard  
python -c "
# Similar check but grouped by fund
# Lists which funds have data in which tables
"
```

## 📊 Performance Monitoring

### Load Time Checks
- [ ] Dashboard loads within 3 seconds
- [ ] Chart renders within 2 seconds of fund selection
- [ ] API responses under 1 second
- [ ] No timeout errors during normal usage

### Error Handling
- [ ] Graceful handling of network failures
- [ ] Proper error messages for users
- [ ] Fallback behavior when Supabase unavailable
- [ ] No crashes when unexpected data formats encountered

## 🚀 Deployment Verification

After deploying changes:

1. **Smoke Test**: Verify basic functionality works
2. **Regression Test**: Re-run all tests from this checklist
3. **User Acceptance**: Test with actual user workflow
4. **Monitor Logs**: Check for new errors in production logs

## 📝 Testing Notes

Date: ___________
Tester: ___________
Environment: [ ] Local [ ] Staging [ ] Production
Version/Commit: ___________

### Issues Found:
- [ ] No issues found
- [ ] Issues found (document below):

### Test Results:
- Performance Chart: [ ] Pass [ ] Fail
- API Endpoints: [ ] Pass [ ] Fail  
- Data Consistency: [ ] Pass [ ] Fail
- Authentication: [ ] Pass [ ] Fail

### Notes:
___________________________________________
___________________________________________
___________________________________________