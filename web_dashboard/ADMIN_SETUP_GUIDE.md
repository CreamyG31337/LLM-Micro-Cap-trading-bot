# Admin Setup Guide

This guide will help you set up the admin system for your Portfolio Dashboard.

## 🎯 What You'll Get

- **Admin Dashboard**: Full user management interface at `/admin`
- **Fund Assignment**: Assign funds to users through the web UI
- **User Management**: View all users and their fund assignments
- **Automatic Admin**: First user to register becomes admin automatically

## 🚀 Quick Setup (5 minutes)

### Step 1: Update Database Schema

1. **Go to your Supabase project dashboard**
2. **Navigate to SQL Editor**
3. **Copy the entire content from `web_dashboard/schema/00_complete_setup.sql`**
4. **Paste it into the SQL editor**
5. **Click "Run"**

This will add admin functionality to your database.

### Step 2: Deploy Updated Code

Your Vercel app will automatically update with the new admin features.

### Step 3: Set Up Admin Credentials

1. **Add your admin credentials to `.env` file**:
   ```
   ADMIN_EMAIL=your-email@example.com
   ADMIN_PASSWORD=your-secure-password
   ADMIN_NAME=Your Name
   ```

2. **Run the secure setup script**:
   ```bash
   cd web_dashboard
   python setup_admin_secure.py
   ```

**🎉 You're now an admin!** The script will create your account and make you admin.

### Step 4: Access Admin Dashboard

1. **Login to your dashboard**
2. **Click the purple "Admin" button** (only visible to admins)
3. **You'll see the admin dashboard at `/admin`

## 👑 Admin Features

### User Management
- **View all users** and their roles
- **See fund assignments** for each user
- **User statistics** and counts

### Fund Assignment
- **Assign funds to users** by email
- **Remove fund access** from users
- **Manage all fund assignments** through the web UI

### Security
- **Only admins** can access the admin dashboard
- **Row Level Security** ensures users only see their assigned funds
- **Automatic role assignment** for the first user

## 🔧 Manual Admin Assignment

If you need to make an existing user an admin:

```bash
cd web_dashboard
python make_admin.py
```

## 📱 Admin Dashboard URLs

- **Main Dashboard**: https://webdashboard-hazel.vercel.app
- **Admin Dashboard**: https://webdashboard-hazel.vercel.app/admin
- **Authentication**: https://webdashboard-hazel.vercel.app/auth

## 🎯 Next Steps

1. **Register your admin account**
2. **Access the admin dashboard**
3. **Assign funds to other users**
4. **Start using the secure portfolio system!**

## 🆘 Troubleshooting

### "Admin privileges required" error
- Make sure you're the first user to register
- Or run `python make_admin.py` to make yourself admin

### Can't see admin button
- Clear your browser cache
- Make sure you're logged in as an admin user

### Database errors
- Make sure you ran the complete setup SQL script
- Check that all tables were created successfully

## 🎉 You're All Set!

Your portfolio dashboard now has a complete admin system. You can manage users and fund assignments entirely through the web interface - no more Python commands needed!
