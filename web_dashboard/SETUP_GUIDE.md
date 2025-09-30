# 🚀 Setup Guide - Trading Bot Dashboard

## 📋 Quick Setup Checklist

### 1. **Environment Setup**
```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your actual values
# NEVER commit .env to git - it's protected by .gitignore
```

### 2. **Supabase Setup**
```bash
# Copy the example credentials file
cp credentials.example.txt supabase_credentials.txt

# Edit supabase_credentials.txt with your actual values
# NEVER commit supabase_credentials.txt to git - it's protected by .gitignore
```

### 3. **Database Setup**
```sql
-- Copy and paste the entire content of schema/00_complete_setup.sql
-- into your Supabase SQL editor
-- This creates everything: tables, auth, permissions, RLS policies
```

### 4. **Data Migration**
```bash
# Migrate your CSV data to Supabase
python migrate.py
```

### 5. **Deploy to Vercel**
```bash
# Deploy to Vercel
vercel --prod

# Set environment variables in Vercel dashboard
# Go to Settings > Environment Variables
```

## 🔐 Security Setup

### **Environment Variables Required:**

#### **Local Development (.env file):**
```bash
# Copy from env.example
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
JWT_SECRET=your-super-secret-jwt-key-here
FLASK_SECRET_KEY=your-flask-secret-key-here
```

#### **Vercel Deployment (Environment Variables):**
1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings > Environment Variables
4. Add each variable with its value

### **Credentials Files:**

#### **supabase_credentials.txt (Local Only):**
```bash
# Copy from credentials.example.txt
Database Password: [YOUR_ACTUAL_PASSWORD]
Project URL: https://your-project-id.supabase.co
Anon Key: your-anon-key-here
```

## 🛡️ Security Measures

### **What's Protected:**
- ✅ `.env` files are gitignored
- ✅ `supabase_credentials.txt` is gitignored
- ✅ All credentials in environment variables
- ✅ No hardcoded secrets in code
- ✅ Admin-only access to dev tools

### **What's Safe to Commit:**
- ✅ `env.example` - Template file with placeholders
- ✅ `credentials.example.txt` - Template file with placeholders
- ✅ All source code (no secrets)
- ✅ Documentation files

## 📁 File Structure

```
web_dashboard/
├── .env                    # ❌ NEVER COMMIT (gitignored)
├── .env.example           # ✅ Safe to commit (template)
├── supabase_credentials.txt # ❌ NEVER COMMIT (gitignored)
├── credentials.example.txt  # ✅ Safe to commit (template)
├── .gitignore             # ✅ Protects sensitive files
└── ... (other files)
```

## 🔧 Development Workflow

### **1. First Time Setup:**
```bash
# 1. Copy example files
cp env.example .env
cp credentials.example.txt supabase_credentials.txt

# 2. Edit with real values
# Edit .env with your Supabase credentials
# Edit supabase_credentials.txt with your database password

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run locally
python app.py
```

### **2. Deploy to Vercel:**
```bash
# 1. Deploy
vercel --prod

# 2. Set environment variables in Vercel dashboard
# Go to Settings > Environment Variables
# Add: SUPABASE_URL, SUPABASE_ANON_KEY, JWT_SECRET, FLASK_SECRET_KEY

# 3. Redeploy
vercel --prod
```

### **3. Test Security:**
```bash
# 1. Register as first user (becomes admin)
# 2. Test admin access to /dev, /dev/sql, /dev/dashboard
# 3. Test data export APIs work
# 4. Verify regular users can't access dev tools
```

## 🚨 Security Checklist

### **Before Committing:**
- [ ] No real credentials in any files
- [ ] `.env` file is gitignored
- [ ] `supabase_credentials.txt` is gitignored
- [ ] Only example files are committed
- [ ] All sensitive data in environment variables

### **Before Deployment:**
- [ ] Environment variables set in Vercel
- [ ] Strong JWT_SECRET generated
- [ ] Strong FLASK_SECRET_KEY generated
- [ ] Supabase database password is secure
- [ ] Admin access works correctly

### **After Deployment:**
- [ ] Register as first user (becomes admin)
- [ ] Test all dev tools work
- [ ] Test data export APIs work
- [ ] Verify no one else can access dev tools
- [ ] Check database admin status

## 🎯 Key Points

### **✅ Safe to Commit:**
- `env.example` - Template with placeholders
- `credentials.example.txt` - Template with placeholders
- All source code (no secrets)
- Documentation files

### **❌ Never Commit:**
- `.env` files (contains real credentials)
- `supabase_credentials.txt` (contains real credentials)
- Any file with real passwords or keys
- Log files with sensitive data

### **🔒 Security Features:**
- **Admin-only access** to dev tools
- **Environment variable protection**
- **Database-level security**
- **JWT token authentication**
- **Row-level security policies**

---

**Your dashboard is secure and ready! 🎉🔒**
