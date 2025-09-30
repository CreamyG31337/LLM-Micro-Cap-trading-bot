# 🔍 Deployment Debugging Guide

## 🚨 Common Deployment Issues & Solutions

### 1. **Vercel Deployment Issues**

#### **Build Failures**
```bash
# Check Vercel build logs
vercel logs --follow

# Common build issues:
# - Missing dependencies in requirements.txt
# - Python version mismatch
# - Import errors
# - Environment variables not set
```

#### **Runtime Errors**
```bash
# Check function logs
vercel logs --follow --function=app

# Common runtime issues:
# - Supabase connection failures
# - Missing environment variables
# - Database schema not set up
# - Authentication errors
```

### 2. **Supabase Connection Issues**

#### **Test Supabase Connection**
```bash
cd web_dashboard
python -c "
from supabase_client import SupabaseClient
try:
    client = SupabaseClient()
    if client.test_connection():
        print('✅ Supabase connection successful')
    else:
        print('❌ Supabase connection failed')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

#### **Check Environment Variables**
```bash
# Verify environment variables are set
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Or check in Vercel dashboard:
# Settings → Environment Variables
```

#### **Database Schema Issues**
```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check if data exists
SELECT COUNT(*) FROM portfolio_positions;
SELECT COUNT(*) FROM trade_log;
SELECT COUNT(*) FROM cash_balances;
```

### 3. **Authentication Issues**

#### **User Registration Problems**
```bash
# Check if users can register
# Visit: https://your-app.vercel.app/auth
# Try to register a new user
```

#### **Fund Access Issues**
```sql
-- Check user fund assignments
SELECT * FROM list_users_with_funds();

-- Check if user has access to specific fund
SELECT * FROM get_user_funds('user-uuid-here');
```

### 4. **Data Migration Issues**

#### **Check Data Migration**
```bash
cd web_dashboard
python migrate.py

# Should show:
# ✅ Connected to Supabase
# 📊 Found X funds with data
# ✅ MIGRATION SUCCESSFUL!
```

#### **Manual Data Check**
```sql
-- Check if data was migrated
SELECT fund, COUNT(*) as positions 
FROM portfolio_positions 
GROUP BY fund;

SELECT fund, COUNT(*) as trades 
FROM trade_log 
GROUP BY fund;

SELECT fund, currency, amount 
FROM cash_balances;
```

### 5. **Frontend Issues**

#### **Browser Console Errors**
1. Open browser developer tools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab for failed API calls
4. Look for CORS errors or 404s

#### **Common Frontend Issues**
- **Charts not loading**: Check Plotly CDN
- **Empty dashboard**: Check API endpoints
- **Authentication loops**: Check JWT tokens
- **Styling issues**: Check CSS loading

### 6. **Performance Issues**

#### **Slow Loading**
```bash
# Check Vercel Analytics
# Go to Vercel dashboard → Analytics

# Common performance issues:
# - Large data sets
# - Inefficient queries
# - Missing indexes
# - No caching
```

#### **Database Performance**
```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM portfolio_positions WHERE fund = 'Project Chimera';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes WHERE tablename = 'portfolio_positions';
```

## 🛠️ Debugging Steps

### Step 1: Check Deployment Status
```bash
# Check Vercel deployment status
vercel ls
vercel inspect [deployment-url]

# Check if environment variables are set
vercel env ls
```

### Step 2: Test Local Environment
```bash
cd web_dashboard
python app.py

# Should start without errors
# Visit: http://localhost:5000
```

### Step 3: Test Database Connection
```bash
cd web_dashboard
python -c "
import os
from supabase_client import SupabaseClient

print('Environment variables:')
print(f'SUPABASE_URL: {bool(os.getenv(\"SUPABASE_URL\"))}')
print(f'SUPABASE_ANON_KEY: {bool(os.getenv(\"SUPABASE_ANON_KEY\"))}')

try:
    client = SupabaseClient()
    print('✅ Supabase client created')
    if client.test_connection():
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### Step 4: Check Data Migration
```bash
cd web_dashboard
python migrate.py

# Look for:
# ✅ Connected to Supabase
# 📊 Found X funds with data
# ✅ MIGRATION SUCCESSFUL!
```

### Step 5: Test API Endpoints
```bash
# Test portfolio data endpoint
curl https://your-app.vercel.app/api/portfolio

# Test authentication endpoint
curl https://your-app.vercel.app/api/auth/status
```

## 🔧 Quick Fixes

### **Fix 1: Environment Variables**
```bash
# Add to Vercel dashboard → Settings → Environment Variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
FLASK_SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
```

### **Fix 2: Database Schema**
```sql
-- Run in Supabase SQL Editor
-- Copy and paste contents of schema/00_complete_setup.sql
```

### **Fix 3: Data Migration**
```bash
cd web_dashboard
python migrate.py
```

### **Fix 4: Redeploy**
```bash
vercel --prod
```

## 📊 Monitoring & Logs

### **Vercel Logs**
```bash
# Real-time logs
vercel logs --follow

# Specific function logs
vercel logs --follow --function=app

# Build logs
vercel logs --build
```

### **Supabase Logs**
1. Go to Supabase dashboard
2. Click "Logs" in sidebar
3. Check for errors or slow queries

### **Browser DevTools**
1. Open F12
2. Check Console for errors
3. Check Network for failed requests
4. Check Application → Local Storage for auth tokens

## 🚨 Emergency Fixes

### **Complete Reset**
```bash
# 1. Delete Vercel deployment
vercel remove --yes

# 2. Reset Supabase database
# Go to Supabase → Settings → Database → Reset

# 3. Re-run schema
# Copy schema/00_complete_setup.sql to Supabase SQL Editor

# 4. Re-deploy
vercel --prod

# 5. Re-migrate data
cd web_dashboard
python migrate.py
```

### **Fallback to Local Development**
```bash
cd web_dashboard
python app.py

# Use local development while fixing deployment
# Data stays in CSV files
```

## 📞 Getting Help

### **Vercel Support**
- Check Vercel dashboard for error messages
- Review build logs for specific errors
- Check Vercel documentation

### **Supabase Support**
- Check Supabase dashboard for database errors
- Review API logs for connection issues
- Check Supabase documentation

### **Debug Information to Collect**
1. Vercel deployment URL
2. Error messages from browser console
3. Vercel build logs
4. Supabase connection test results
5. Environment variables status
6. Database schema status
7. Data migration results

---

## 🎯 Success Checklist

- [ ] Vercel deployment successful
- [ ] Environment variables set correctly
- [ ] Supabase database schema created
- [ ] Data migration completed
- [ ] Authentication working
- [ ] Dashboard loads without errors
- [ ] Charts display correctly
- [ ] User registration works
- [ ] Fund access control working
- [ ] Performance acceptable

