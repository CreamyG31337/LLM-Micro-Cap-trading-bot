# 🚀 Portfolio Dashboard Deployment Guide

This guide will help you deploy your trading bot's portfolio dashboard to share performance with friends.

## 📋 Prerequisites

1. **GitHub Account** - For hosting your code
2. **Trading Data** - Your CSV files in `trading_data/prod/`
3. **Python 3.11+** - For local development

## 🎯 Quick Start Options

### Option 1: Vercel (Recommended - Easiest)

**Best for:** Quick deployment with automatic updates

1. **Prepare your repository:**
   ```bash
   # Copy your trading data to the web dashboard
   cd web_dashboard
   python sync_data.py
   
   # Commit everything to GitHub
   git add .
   git commit -m "Add portfolio dashboard"
   git push
   ```

2. **Deploy to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Sign in with GitHub
   - Click "New Project"
   - Import your repository
   - Set root directory to `web_dashboard`
   - Deploy!

3. **Set up automatic updates:**
   - Add a GitHub Action to sync data daily
   - Or manually run `python sync_data.py` and push changes

**Cost:** Free (100GB bandwidth/month)

---

### Option 2: Railway (Best for persistent storage)

**Best for:** Apps that need file storage and database

1. **Prepare your app:**
   ```bash
   cd web_dashboard
   python sync_data.py
   ```

2. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Set root directory to `web_dashboard`
   - Deploy!

3. **Set up data persistence:**
   - Railway will keep your data between deployments
   - Use their file system for CSV storage

**Cost:** $5/month free credit (effectively free for small apps)

---

### Option 3: Netlify (Static site with functions)

**Best for:** Simple portfolio displays

1. **Convert to static site:**
   - Use GitHub Actions to generate static HTML
   - Deploy the static files to Netlify

2. **Deploy:**
   - Go to [netlify.com](https://netlify.com)
   - Connect your GitHub repository
   - Set build command: `python generate_static.py`
   - Deploy!

**Cost:** Free (100GB bandwidth/month)

---

## 🔧 Local Development

1. **Set up the environment:**
   ```bash
   cd web_dashboard
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Sync your data:**
   ```bash
   python sync_data.py
   ```

3. **Run the dashboard:**
   ```bash
   python app.py
   ```

4. **View at:** http://localhost:5000

---

## 📊 Features Included

### Dashboard Features:
- 📈 **Real-time Performance Chart** - Interactive Plotly charts
- 💰 **Portfolio Metrics** - Total value, P&L, performance %
- 💼 **Current Positions** - Live position tracking
- 📋 **Recent Trades** - Trade history display
- 💵 **Cash Balances** - CAD/USD balance tracking
- 📱 **Mobile Responsive** - Works on all devices

### Data Sources:
- `llm_portfolio_update.csv` - Current positions
- `llm_trade_log.csv` - Trade history
- `cash_balances.json` - Cash balances

---

## 🔄 Keeping Data Updated

### Manual Updates:
```bash
cd web_dashboard
python sync_data.py
git add .
git commit -m "Update portfolio data"
git push
```

### Automated Updates (GitHub Actions):
Create `.github/workflows/update-dashboard.yml`:

```yaml
name: Update Dashboard Data
on:
  schedule:
    - cron: '0 18 * * 1-5'  # 6 PM EST on weekdays
  workflow_dispatch:  # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Sync data
        run: |
          cd web_dashboard
          python sync_data.py
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "Auto-update dashboard data" || exit 0
          git push
```

---

## 🌐 Custom Domain Setup

### Vercel:
1. Go to your project settings
2. Add your domain in "Domains" section
3. Update DNS records as instructed

### Railway:
1. Go to project settings
2. Add custom domain
3. Update DNS records

---

## 🔒 Security Considerations

1. **Data Privacy:**
   - Your trading data is public on GitHub
   - Consider using environment variables for sensitive data
   - Or use a private repository

2. **Access Control:**
   - Add basic authentication if needed
   - Use Vercel's password protection feature

3. **Rate Limiting:**
   - Add rate limiting to prevent abuse
   - Use caching for expensive operations

---

## 🐛 Troubleshooting

### Common Issues:

1. **Data not updating:**
   - Check if `sync_data.py` ran successfully
   - Verify file paths are correct
   - Check GitHub Actions logs

2. **Chart not displaying:**
   - Check browser console for errors
   - Verify Plotly CDN is loading
   - Check if data exists in CSV files

3. **Deployment fails:**
   - Check `requirements.txt` versions
   - Verify all files are committed
   - Check platform-specific logs

### Debug Mode:
```bash
# Run with debug logging
FLASK_DEBUG=1 python app.py
```

---

## 📈 Performance Optimization

1. **Caching:**
   - Add Redis for data caching
   - Cache expensive calculations
   - Use CDN for static assets

2. **Data Processing:**
   - Pre-process CSV data
   - Use pandas efficiently
   - Minimize API calls

3. **Frontend:**
   - Optimize images and assets
   - Use lazy loading
   - Minimize JavaScript bundles

---

## 🎉 Success!

Once deployed, your friends can view your portfolio performance at:
- **Vercel:** `https://your-project.vercel.app`
- **Railway:** `https://your-project.railway.app`
- **Netlify:** `https://your-project.netlify.app`

Share the URL and let them see your trading success! 🚀
