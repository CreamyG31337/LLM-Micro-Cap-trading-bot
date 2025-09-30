# 📈 Portfolio Performance Dashboard

A secure, multi-user web dashboard for tracking trading bot portfolio performance with Supabase backend.

## 🚀 Quick Start

### 1. Database Setup (One Command)
```sql
-- Copy and paste the entire content of schema/00_complete_setup.sql into Supabase SQL editor
-- This creates everything: tables, auth, permissions, RLS policies
```

### 2. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your Supabase credentials
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_ANON_KEY=your-anon-key
# JWT_SECRET=your-super-secret-jwt-key
# FLASK_SECRET_KEY=your-flask-secret-key
```

### 3. Migrate Your Data
```bash
python migrate.py
```

### 4. Deploy to Vercel
```bash
vercel --prod
```

## 🔐 User Authentication

- **Secure Login/Register** - Professional UI with Supabase Auth
- **Fund-Based Access** - Users only see their assigned funds
- **No "All Funds"** - Each user has specific fund access
- **Row Level Security** - Database-level access control

## 📁 Project Structure

```
web_dashboard/
├── schema/                    # 🗄️ Database schema files
│   ├── 00_complete_setup.sql  # 🎯 ONE FILE TO RULE THEM ALL
│   ├── 01_main_schema.sql     # Core portfolio tables
│   ├── 02_auth_schema.sql     # User authentication & permissions
│   ├── 03_sample_data.sql     # Test data (optional)
│   └── README.md             # Detailed schema documentation
├── templates/                 # 🎨 HTML templates
│   ├── index.html            # Main dashboard
│   └── auth.html             # Login/register page
├── app.py                    # 🚀 Flask application
├── auth.py                   # 🔐 Authentication system
├── supabase_client.py        # 📊 Database client
├── migrate.py                # 📦 Data migration script
├── admin_assign_funds.py     # 👥 User management
├── requirements.txt          # 📋 Dependencies
├── env.example               # 🔧 Environment template (safe to commit)
├── credentials.example.txt   # 🔑 Credentials template (safe to commit)
├── .gitignore               # 🛡️ Protects sensitive files
└── SETUP_GUIDE.md           # 📖 Detailed setup instructions
```

## 🔧 Example Files (Safe to Commit)

### **Environment Template (`env.example`)**
```bash
# Copy this to .env and fill in your values
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
JWT_SECRET=your-super-secret-jwt-key-here
FLASK_SECRET_KEY=your-flask-secret-key-here
```

### **Credentials Template (`credentials.example.txt`)**
```bash
# Copy this to supabase_credentials.txt and fill in your values
Database Password: [CHANGE_THIS_PASSWORD]
Project URL: https://your-project-id.supabase.co
Anon Key: your-anon-key-here
```

**See `SETUP_GUIDE.md` for detailed setup instructions.**

## 🛠️ Features

### Portfolio Tracking
- **Multi-Fund Support** - Separate tracking for different funds
- **Real-Time Data** - Live portfolio positions and performance
- **Performance Charts** - Interactive Plotly charts
- **Trade History** - Complete transaction log
- **Cash Balances** - Multi-currency cash tracking

### Security & Permissions
- **User Authentication** - Secure login/registration
- **Fund Access Control** - Users only see assigned funds
- **Row Level Security** - Database-level permissions
- **Session Management** - JWT tokens with expiration

### Admin Tools
- **Fund Assignment** - Assign funds to users
- **User Management** - List and manage users
- **Data Migration** - Import from CSV files

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

### Database Management
```bash
# Assign funds to users
python admin_assign_funds.py assign user@example.com "Project Chimera"

# List users and their funds
python admin_assign_funds.py
```

### Migration
```bash
# Migrate data from CSV files
python migrate.py
```

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout

### Portfolio Data
- `GET /api/funds` - Get user's assigned funds
- `GET /api/portfolio?fund=<name>` - Get portfolio data
- `GET /api/performance-chart?fund=<name>` - Get performance chart
- `GET /api/recent-trades?fund=<name>` - Get recent trades

## 🔐 Security Model

- **No "All Funds" Access** - Users only see their assigned funds
- **Fund-Based Permissions** - Each fund is assigned to specific users
- **Database-Level Security** - RLS policies enforce access control
- **JWT Authentication** - Secure session management
- **Automatic Redirects** - Unauthenticated users sent to login

### 🔒 Admin-Only Features
- **SQL Interface** (`/dev/sql`) - Direct database query access
- **Data Export APIs** (`/api/export/*`) - LLM data access
- **Developer Dashboard** (`/dev/dashboard`) - Visual data overview
- **User Management** - Assign funds to users

### 🛡️ Security Measures
- **First User = Admin** - Only the first registered user gets admin access
- **No Hardcoded Credentials** - All sensitive data in environment variables
- **Database-Level Security** - Row Level Security (RLS) policies
- **JWT Token Security** - Secure session management with expiration
- **Gitignore Protection** - Credentials files are never committed to git

**See `SECURITY_GUIDE.md` for detailed security information.**

## 📋 Setup Checklist

- [ ] Supabase project created
- [ ] Database schema run (`schema/00_complete_setup.sql`)
- [ ] Environment variables set (`.env`)
- [ ] Data migrated (`python migrate.py`)
- [ ] Users registered on dashboard
- [ ] Funds assigned to users (`admin_assign_funds.py`)
- [ ] Dashboard deployed to Vercel
- [ ] Login/authentication working
- [ ] Fund access control verified

## 🐛 Troubleshooting

### Common Issues

**"Authentication required" errors:**
- Users need to register and have funds assigned
- Check that `user_funds` table has proper assignments

**"Access denied to this fund" errors:**
- User doesn't have access to the requested fund
- Use `admin_assign_funds.py` to assign funds

**Empty dashboard:**
- Run `python migrate.py` to populate with data
- Check that funds are assigned to the user

### Verification Commands

```sql
-- Check if all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- List users and their fund assignments
SELECT * FROM list_users_with_funds();

-- Test fund access for a user
SELECT * FROM get_user_funds('user-uuid-here');
```

## 📚 Documentation

- **Database Setup**: See `DATABASE_SETUP.md`
- **Schema Details**: See `schema/README.md`
- **API Reference**: See code comments in `app.py`

## 🚀 Deployment

The dashboard is designed to deploy easily to Vercel:

```bash
# Deploy to Vercel
vercel --prod

# Your dashboard will be live at:
# https://your-project.vercel.app
```

## 🎯 Key Benefits

- **Secure Multi-User** - Each user sees only their assigned funds
- **Professional UI** - Clean, modern dashboard interface
- **Real-Time Data** - Live portfolio tracking
- **Easy Management** - Simple admin tools for user/fund management
- **Scalable** - Built on Supabase for reliability and performance

---

**Your secure, multi-user portfolio dashboard is ready! 🎉**
