# 🚀 Supabase + Vercel Setup Guide

This guide will help you set up your portfolio dashboard with Supabase database and Vercel hosting, keeping your trading data secure and private.

## 📋 Prerequisites

1. **GitHub Account** - For hosting your code
2. **Supabase Account** - For database hosting (free tier available)
3. **Vercel Account** - For web hosting (free tier available)
4. **Your Trading Data** - CSV files in `trading_data/prod/`

## 🗄️ Step 1: Set Up Supabase Database

### 1.1 Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Choose your organization
5. Enter project details:
   - **Name**: `portfolio-dashboard`
   - **Database Password**: (generate a strong password)
   - **Region**: Choose closest to you
6. Click "Create new project"
7. Wait for project to be ready (2-3 minutes)

### 1.2 Set Up Database Schema
1. Go to your Supabase project dashboard
2. Click "SQL Editor" in the left sidebar
3. Click "New query"
4. Copy and paste the contents of `supabase_setup.sql`
5. Click "Run" to execute the schema
6. Verify tables were created in "Table Editor"

### 1.3 Get API Keys
1. Go to "Settings" → "API" in your Supabase project
2. Copy the following values:
   - **Project URL** (looks like: `https://your-project.supabase.co`)
   - **anon public** key (starts with `eyJ...`)

## 🌐 Step 2: Set Up Vercel Deployment

### 2.1 Prepare Your Repository
1. Make sure your code is in a GitHub repository
2. The `web_dashboard` folder should be in your repository root

### 2.2 Deploy to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Sign in with GitHub
3. Click "New Project"
4. Import your repository
5. Configure the project:
   - **Framework Preset**: Other
   - **Root Directory**: `web_dashboard`
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)
6. Click "Deploy"

### 2.3 Set Environment Variables
1. In your Vercel project dashboard, go to "Settings" → "Environment Variables"
2. Add the following variables:
   - **SUPABASE_URL**: Your Supabase project URL
   - **SUPABASE_ANON_KEY**: Your Supabase anon key
3. Click "Save"
4. Go to "Deployments" and redeploy your project

## 📊 Step 3: Migrate Your Data

### 3.1 Set Up Local Environment
```bash
cd web_dashboard
pip install -r requirements.txt
```

### 3.2 Create Environment File
Create a `.env` file in the `web_dashboard` directory:
```env
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

### 3.3 Run Data Migration
```bash
python migrate_to_supabase.py
```

This will:
- Load your CSV data from `trading_data/prod/`
- Upload it to Supabase
- Verify the migration was successful

## 🔄 Step 4: Set Up Data Synchronization

### 4.1 Manual Sync (Recommended for now)
After running your trading bot and updating CSV files, run:
```bash
cd web_dashboard
python sync_to_supabase.py
```

### 4.2 Automated Sync (Optional)
Create a GitHub Action to sync data automatically:

1. Create `.github/workflows/sync-data.yml` in your repository:
```yaml
name: Sync Data to Supabase
on:
  schedule:
    - cron: '0 18 * * 1-5'  # 6 PM EST on weekdays
  workflow_dispatch:  # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd web_dashboard
          pip install -r requirements.txt
      - name: Sync data
        run: |
          cd web_dashboard
          python sync_to_supabase.py --data-dir ../trading_data/prod
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
```

2. Add secrets to your GitHub repository:
   - Go to repository "Settings" → "Secrets and variables" → "Actions"
   - Add `SUPABASE_URL` and `SUPABASE_ANON_KEY`

## 🎉 Step 5: Test Your Dashboard

1. **Visit your Vercel URL** (e.g., `https://your-project.vercel.app`)
2. **Verify data is loading** correctly
3. **Check all features**:
   - Portfolio metrics
   - Performance chart
   - Current positions
   - Recent trades
   - Cash balances

## 🔒 Security & Privacy

### ✅ What's Secure
- **Trading data stored in Supabase** (not in GitHub)
- **Database access controlled** by API keys
- **Row Level Security** enabled on all tables
- **HTTPS encryption** for all data transmission

### ⚠️ What to Consider
- **API keys are in environment variables** (secure)
- **Database is accessible** via API (but protected by keys)
- **Consider adding authentication** if you want to restrict access

## 🛠️ Troubleshooting

### Common Issues

1. **"Supabase client not available"**
   - Install dependencies: `pip install -r requirements.txt`
   - Check environment variables are set

2. **"Failed to connect to Supabase"**
   - Verify your Supabase URL and key
   - Check if your Supabase project is active

3. **"No data showing"**
   - Run the migration script: `python migrate_to_supabase.py`
   - Check if data exists in Supabase tables

4. **"Chart not loading"**
   - Check browser console for errors
   - Verify Plotly CDN is loading

### Debug Mode
```bash
# Run with debug logging
FLASK_DEBUG=1 python app.py
```

## 📈 Next Steps

1. **Customize the dashboard** - Modify colors, layout, etc.
2. **Add authentication** - Restrict access to specific users
3. **Set up monitoring** - Track performance and errors
4. **Add more features** - Additional charts, metrics, etc.

## 🎯 Success!

Your portfolio dashboard is now:
- ✅ **Hosted on Vercel** (free, fast, reliable)
- ✅ **Data stored in Supabase** (secure, scalable)
- ✅ **No sensitive data in GitHub** (privacy protected)
- ✅ **Automatically updating** (when you sync data)
- ✅ **Shareable with friends** (via Vercel URL)

Share your dashboard URL with friends to show off your trading performance! 🚀
