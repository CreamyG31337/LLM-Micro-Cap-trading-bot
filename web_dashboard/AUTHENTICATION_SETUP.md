# 🔐 Authentication Setup Guide

## 🚨 Important: Email Confirmation Required

Your Supabase project has **email confirmation enabled**. This means:

1. ✅ Users can register successfully
2. ❌ Users **cannot login** until they confirm their email
3. 📧 A confirmation email is sent to each new user
4. 🔗 Users must click the confirmation link in the email

## 🛠️ Setup Steps

### 1. Database Schema
First, make sure you've run the database schema:
```sql
-- Copy and paste schema/00_complete_setup.sql into Supabase SQL editor
```

### 2. Supabase Auth Settings
You have two options:

#### Option A: Disable Email Confirmation (Recommended for Development)
1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Settings**
3. Under **Email**, disable **Enable email confirmations**
4. Save changes

#### Option B: Keep Email Confirmation (Production Ready)
1. Users will receive confirmation emails
2. They must click the link to activate their account
3. Only then can they login

### 3. Test User Creation
After setting up the database, create a test user:

1. **Register a user** through the web dashboard
2. **Check your email** for the confirmation link
3. **Click the confirmation link** to activate the account
4. **Login** with the confirmed account

### 4. Assign Funds to Users
After users are confirmed, assign them funds:

```bash
# List available users and funds
python admin_assign_funds.py

# Assign funds to a specific user
python admin_assign_funds.py assign user@example.com "Project Chimera"
python admin_assign_funds.py assign user@example.com "RRSP Lance Webull"
```

## 🧪 Testing the System

### 1. Test Registration
1. Visit your dashboard: `https://webdashboard-hazel.vercel.app`
2. Click "Sign up"
3. Enter a **valid email address** (e.g., `yourname@gmail.com`)
4. Enter a password (at least 6 characters)
5. Enter your full name
6. Click "Create Account"

### 2. Test Email Confirmation
1. Check your email inbox
2. Look for an email from Supabase
3. Click the confirmation link
4. You should see a success message

### 3. Test Login
1. Go back to the dashboard
2. Click "Sign in"
3. Enter your email and password
4. You should be logged in successfully

### 4. Test Fund Assignment
1. After logging in, you should see "Select Fund" dropdown
2. If empty, assign funds using the admin script
3. Select a fund to see portfolio data

## 🐛 Troubleshooting

### "Email not confirmed" Error
- **Solution**: Check your email and click the confirmation link
- **Alternative**: Disable email confirmation in Supabase settings

### "Invalid email address" Error
- **Solution**: Use a real email address (e.g., `yourname@gmail.com`)
- **Avoid**: `test@example.com`, `admin@test.com`, etc.

### "Access denied to this fund" Error
- **Solution**: Assign funds to the user using admin script
- **Command**: `python admin_assign_funds.py assign user@example.com "Fund Name"`

### Empty Dashboard
- **Solution**: Run data migration: `python migrate.py`
- **Check**: Ensure funds are assigned to the user

### "Authentication required" Error
- **Solution**: Login first, then access the dashboard
- **Check**: Ensure you clicked the email confirmation link

## 📋 Quick Setup Checklist

- [ ] Database schema created (`schema/00_complete_setup.sql`)
- [ ] Supabase auth settings configured
- [ ] Test user registered through dashboard
- [ ] Email confirmation completed
- [ ] User can login successfully
- [ ] Funds assigned to user (`admin_assign_funds.py`)
- [ ] Data migrated (`python migrate.py`)
- [ ] Dashboard shows portfolio data

## 🚀 Production Deployment

For production, keep email confirmation enabled for security:

1. **Email confirmation**: ✅ Enabled
2. **Strong passwords**: ✅ Required
3. **User verification**: ✅ Required
4. **Fund access control**: ✅ Enabled

## 📞 Need Help?

If you're still having issues:

1. **Check Supabase logs** in your project dashboard
2. **Verify environment variables** are correct
3. **Test with a real email address** (not test@example.com)
4. **Ensure database schema** is created
5. **Check fund assignments** for the user

---

**Your secure authentication system is ready! 🎉**
