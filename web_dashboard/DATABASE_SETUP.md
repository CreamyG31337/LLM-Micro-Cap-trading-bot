# 🗄️ Database Setup Guide

## 🚀 Quick Start (Recommended)

**One Command Setup:**
1. Copy the entire content of `schema/00_complete_setup.sql`
2. Paste it into your Supabase SQL editor
3. Run it
4. Done! Your database is ready

## 📁 Schema Organization

All database files are organized in the `schema/` directory:

```
schema/
├── 00_complete_setup.sql    # 🎯 ONE FILE TO RULE THEM ALL
├── 01_main_schema.sql       # Core portfolio tables
├── 02_auth_schema.sql       # User authentication & permissions  
├── 03_sample_data.sql       # Test data (optional)
└── README.md               # Detailed documentation
```

## 🔢 Execution Order

If you prefer to run files individually:

1. **`01_main_schema.sql`** - Core portfolio tables, indexes, triggers
2. **`02_auth_schema.sql`** - User management, RLS policies, access control
3. **`03_sample_data.sql`** - Sample data for testing (optional)

## ⚡ What Gets Created

### Core Tables
- `portfolio_positions` - Stock positions with fund separation
- `trade_log` - All trading transactions
- `cash_balances` - Cash holdings per fund/currency
- `performance_metrics` - Cached performance data

### Authentication Tables
- `user_profiles` - User information and metadata
- `user_funds` - Fund assignments per user
- `auth.users` - Supabase auth users (managed by Supabase)

### Security Features
- **Row Level Security (RLS)** - Users only see their assigned funds
- **Access Control Functions** - Check fund access permissions
- **Auto User Profile Creation** - Profiles created on signup

## 🔐 Security Model

- **No "All Funds" Access** - Users only see their assigned funds
- **Fund-Based Permissions** - Each fund is assigned to specific users
- **Database-Level Security** - RLS policies enforce access control
- **JWT Authentication** - Secure session management

## 🛠️ Post-Setup Steps

1. **Migrate Your Data:**
   ```bash
   python migrate.py
   ```

2. **Test User Registration:**
   - Visit your dashboard
   - Register a new user
   - Verify they're redirected to login

3. **Assign Funds to Users:**
   ```bash
   # List available users and funds
   python admin_assign_funds.py
   
   # Assign funds to specific users
   python admin_assign_funds.py assign user@example.com "Project Chimera"
   python admin_assign_funds.py assign user@example.com "RRSP Lance Webull"
   ```

4. **Test the System:**
   - Login with assigned user
   - Verify they only see their assigned funds
   - Test fund switching in the dropdown

## 🐛 Troubleshooting

### Common Issues

**"Table already exists" errors:**
- ✅ Safe to ignore - the script handles existing tables

**"Function already exists" errors:**
- ✅ Safe to ignore - functions are replaced with new versions

**Permission errors:**
- ❌ Make sure you're running as database admin
- ❌ Check Supabase project permissions

**RLS blocking data access:**
- ❌ Users need fund assignments in `user_funds` table
- ❌ Check that `auth.uid()` is working correctly

### Verification Commands

```sql
-- Check if all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';

-- List users and their fund assignments
SELECT * FROM list_users_with_funds();

-- Test fund access for a user
SELECT * FROM get_user_funds('user-uuid-here');
```

## 📋 Checklist

After running the setup:

- [ ] All tables created successfully
- [ ] RLS policies enabled
- [ ] User management functions working
- [ ] Fund assignment system ready
- [ ] Migration script runs without errors
- [ ] Dashboard login/registration works
- [ ] Users can only see assigned funds
- [ ] Fund switching works in dropdown

## 🚨 Important Notes

- **Backup First**: Always backup your database before running schema changes
- **Test Environment**: Test on a development database first
- **User Management**: Users must register through the web interface first
- **Fund Assignments**: Use the admin script to assign funds after users register
- **No "All Funds"**: This is intentionally removed for security

## 🆘 Need Help?

1. Check the `schema/README.md` for detailed documentation
2. Verify all tables exist with the verification commands above
3. Test with sample data first before migrating real data
4. Check Supabase logs for any error messages

---

**Your secure, multi-user portfolio dashboard is ready! 🎉**
