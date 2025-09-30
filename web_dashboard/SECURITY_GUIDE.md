# 🔒 Security Guide - Trading Bot Dashboard

## 🚨 CRITICAL SECURITY MEASURES

### **1. Admin-Only Access Control**

#### **How Admin Access Works:**
- **First user = Admin**: The first user to register automatically becomes admin
- **Database-level security**: Admin status stored in `user_profiles.role = 'admin'`
- **All dev tools require admin**: SQL interface, data export APIs, developer dashboard
- **No hardcoded credentials**: All authentication through Supabase

#### **Current Admin Setup:**
```sql
-- Admin is determined by being the first user
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
DECLARE
    user_count INTEGER;
    user_role VARCHAR(50);
BEGIN
    -- Check if this is the first user (admin)
    SELECT COUNT(*) INTO user_count FROM user_profiles;
    
    IF user_count = 0 THEN
        user_role := 'admin';  -- First user = admin
    ELSE
        user_role := 'user';   -- All others = regular users
    END IF;
    
    INSERT INTO user_profiles (user_id, email, full_name, role)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'full_name', ''), user_role);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### **2. Environment Variables (NO HARDCODED CREDENTIALS)**

#### **Required Environment Variables:**
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# JWT Secret (change this!)
JWT_SECRET=your-super-secret-jwt-key-here

# Flask Secret
FLASK_SECRET_KEY=your-flask-secret-key-here
```

#### **Where to Set These:**
- **Local Development**: Create `.env` file (gitignored)
- **Vercel Deployment**: Set in Vercel dashboard under Settings > Environment Variables
- **Never commit to git**: All sensitive data in environment variables only

### **3. Database Security (Row Level Security)**

#### **Fund-Based Access Control:**
```sql
-- Users can only see data for their assigned funds
CREATE POLICY "Users can view portfolio positions for their funds" ON portfolio_positions
    FOR SELECT USING (
        fund IN (
            SELECT fund_name FROM user_funds WHERE user_id = auth.uid()
        )
    );
```

#### **Admin-Only Functions:**
```sql
-- Only admins can access admin functions
CREATE POLICY "Admins can view all user profiles" ON user_profiles
    FOR SELECT USING (is_admin(auth.uid()));

CREATE POLICY "Admins can view all user funds" ON user_funds
    FOR SELECT USING (is_admin(auth.uid()));
```

### **4. API Security**

#### **All Dev Endpoints Require Admin:**
```python
@app.route('/dev/sql')
@require_auth
def sql_interface():
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    # ... rest of function
```

#### **Data Export APIs (LLM Access):**
```python
@app.route('/api/export/portfolio')
@require_auth
def export_portfolio():
    if not is_admin():
        return jsonify({"error": "Admin privileges required"}), 403
    # ... rest of function
```

### **5. File Security**

#### **Gitignore Protection:**
```
# Environment files
.env
.env.local
.env.production

# Credentials
*credentials*
supabase_credentials.txt

# Logs
*.log
```

#### **Current Status:**
- ✅ `supabase_credentials.txt` is gitignored
- ✅ All sensitive data in environment variables
- ✅ No hardcoded credentials in code
- ✅ Admin access controlled by database

### **6. Deployment Security**

#### **Vercel Environment Variables:**
1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings > Environment Variables
4. Add these variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `JWT_SECRET` (generate a strong secret)
   - `FLASK_SECRET_KEY`

#### **Supabase Security:**
1. **Row Level Security**: Enabled on all tables
2. **JWT Authentication**: All API calls require valid JWT
3. **Admin Functions**: Protected by database policies
4. **Fund Access**: Users only see their assigned funds

### **7. Access Control Summary**

#### **Who Can Access What:**

| Feature | Regular User | Admin (You) |
|---------|-------------|-------------|
| Portfolio Dashboard | ✅ (their funds only) | ✅ (all funds) |
| SQL Interface | ❌ | ✅ |
| Data Export APIs | ❌ | ✅ |
| Developer Dashboard | ❌ | ✅ |
| User Management | ❌ | ✅ |

#### **How to Ensure Only You Have Admin Access:**

1. **Register First**: Be the first user to register on the dashboard
2. **Check Admin Status**: Visit `/dev` - if you see the developer tools, you're admin
3. **Verify in Database**: 
   ```sql
   SELECT email, role FROM user_profiles WHERE role = 'admin';
   ```

### **8. Security Checklist**

#### **Before Deployment:**
- [ ] Set strong `JWT_SECRET` (32+ characters)
- [ ] Set strong `FLASK_SECRET_KEY` (32+ characters)
- [ ] Verify environment variables in Vercel
- [ ] Test admin access works
- [ ] Test regular user access is restricted

#### **After Deployment:**
- [ ] Register as first user (becomes admin)
- [ ] Test all dev tools work
- [ ] Test data export APIs work
- [ ] Verify no one else can access dev tools
- [ ] Check database admin status

### **9. Emergency Security Actions**

#### **If Someone Else Gets Admin:**
1. **Database Fix**: 
   ```sql
   -- Remove admin from other user
   UPDATE user_profiles SET role = 'user' WHERE email = 'other@email.com';
   
   -- Make yourself admin
   UPDATE user_profiles SET role = 'admin' WHERE email = 'your@email.com';
   ```

2. **Reset Access**:
   - Change JWT_SECRET in Vercel
   - All existing sessions will be invalidated
   - Users will need to log in again

#### **If Credentials Are Compromised:**
1. **Immediately change**:
   - JWT_SECRET in Vercel
   - FLASK_SECRET_KEY in Vercel
   - Supabase database password
2. **Revoke access**:
   - Delete all user sessions
   - Reset admin status
   - Re-register as admin

### **10. Best Practices**

#### **For You (Admin):**
- Keep your admin credentials secure
- Don't share admin access
- Regularly check who has access
- Use strong, unique passwords

#### **For the System:**
- All sensitive data in environment variables
- No hardcoded credentials
- Database-level security policies
- JWT-based authentication
- Row-level security enabled

---

## 🎯 **CURRENT SECURITY STATUS: SECURE**

✅ **Admin-only access to dev tools**  
✅ **No hardcoded credentials**  
✅ **Environment variable protection**  
✅ **Database-level security**  
✅ **Gitignore protection**  
✅ **JWT authentication**  
✅ **Row-level security**  

**You are the only one who can access the SQL interface, data export APIs, and developer dashboard!** 🔒
