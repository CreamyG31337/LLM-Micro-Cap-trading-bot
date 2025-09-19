# Database Schema Setup Guide

This directory contains all database schema files for the Portfolio Dashboard.

## 🚀 Quick Setup (One Command)

Run the main setup script to create everything:

```sql
-- Copy and paste the entire content of 01_main_schema.sql into Supabase SQL editor
```

## 📁 Schema Files (Run in Order)

### 1. `01_main_schema.sql` - **START HERE**
- **Purpose**: Core portfolio tables and basic setup
- **Contains**: 
  - Portfolio positions, trade log, cash balances, performance metrics
  - Basic indexes and triggers
  - Initial data setup
- **Run First**: This is the foundation

### 2. `02_auth_schema.sql` - **RUN SECOND**
- **Purpose**: User authentication and permissions
- **Contains**:
  - User profiles and fund assignments
  - Row Level Security (RLS) policies
  - Access control functions
- **Run After**: Main schema is created

### 3. `03_sample_data.sql` - **OPTIONAL**
- **Purpose**: Sample users and fund assignments for testing
- **Contains**:
  - Test user accounts
  - Sample fund assignments
- **Run Last**: Only if you want test data

## 🔧 Manual Setup (If Needed)

If you prefer to run files individually:

1. **First**: Run `01_main_schema.sql`
2. **Second**: Run `02_auth_schema.sql` 
3. **Optional**: Run `03_sample_data.sql`

## ⚠️ Important Notes

- **Order Matters**: Always run files in numerical order
- **Backup First**: Consider backing up your database before running
- **Test Environment**: Test on a development database first
- **RLS Policies**: The auth schema enables Row Level Security - users will only see their assigned funds

## 🐛 Troubleshooting

- **"Table already exists"**: You can safely ignore these errors
- **"Function already exists"**: You can safely ignore these errors  
- **Permission errors**: Make sure you're running as a database admin
- **RLS issues**: Check that user_funds table has proper assignments

## 📋 Post-Setup Checklist

After running all schemas:

1. ✅ Verify tables exist: `portfolio_positions`, `trade_log`, `cash_balances`, `performance_metrics`
2. ✅ Verify auth tables exist: `user_profiles`, `user_funds`
3. ✅ Test RLS: Create a test user and assign them a fund
4. ✅ Run migration: `python migrate.py` to populate with your data
5. ✅ Test dashboard: Visit the web dashboard and verify login works

## 🔐 Security

- All portfolio data is protected by Row Level Security
- Users can only access funds assigned to them
- No "All Funds" access - each user sees only their assigned funds
- JWT tokens expire after 24 hours
