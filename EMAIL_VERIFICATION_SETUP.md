# Email Verification System - Setup Guide

## 🎉 What's New

Your signup system now includes **email verification**! Users must verify their email address before their account is created.

### ✨ Features
- ✅ 6-digit verification code sent via email
- ✅ Similar UI to login/signup pages
- ✅ "Resend Code" button
- ✅ 10-minute code expiration
- ✅ 5 verification attempts allowed
- ✅ Auto-login after successful verification
- ✅ Automatic cleanup of expired codes

---

## 📧 Setting Up Gmail SMTP in Vercel

To send verification emails, you need to configure Gmail SMTP. Here's how:

### Step 1: Generate Gmail App Password

1. **Go to your Google Account**
   - Visit: https://myaccount.google.com/

2. **Enable 2-Step Verification** (if not already enabled)
   - Go to Security → 2-Step Verification
   - Follow the prompts to enable it

3. **Generate App Password**
   - Go to Security → 2-Step Verification
   - Scroll down to "App passwords"
   - Click "App passwords"
   - Select "Mail" and "Other (Custom name)"
   - Name it: "CLASS XII PYTHON"
   - Click "Generate"
   - **Copy the 16-character password** (you won't see it again!)

### Step 2: Add Environment Variables in Vercel

Go to your Vercel project dashboard:

1. **Navigate to your project**
   - Go to: https://vercel.com/
   - Select your "CLASS-XII" project

2. **Open Settings**
   - Click "Settings" tab
   - Click "Environment Variables" in left sidebar

3. **Add the following variables:**

| Variable Name | Value | Example |
|--------------|-------|---------|
| `EMAIL_HOST` | `smtp.gmail.com` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` | `587` |
| `EMAIL_USE_TLS` | `True` | `True` |
| `EMAIL_HOST_USER` | Your Gmail address | `youremail@gmail.com` |
| `EMAIL_HOST_PASSWORD` | App Password from Step 1 | `abcd efgh ijkl mnop` (remove spaces) |
| `DEFAULT_FROM_EMAIL` | Your Gmail address | `youremail@gmail.com` |

### Step 3: Add Variables in Vercel Dashboard

For each variable:
1. Click "Add New" button
2. Enter the **Variable Name** (exactly as shown above)
3. Enter the **Value**
4. Select environment: Check all three (Production, Preview, Development)
5. Click "Save"

### Example Screenshot Guide:

```
┌─────────────────────────────────────────────────┐
│  Add Environment Variable                       │
├─────────────────────────────────────────────────┤
│  Name:  EMAIL_HOST                             │
│  Value: smtp.gmail.com                         │
│                                                 │
│  Environments:                                  │
│  ☑ Production                                  │
│  ☑ Preview                                     │
│  ☑ Development                                 │
│                                                 │
│  [Cancel]  [Save]                              │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Complete Environment Variables Checklist

Here's the complete list of environment variables you need in Vercel:

### Database (Existing)
- ✅ `DATABASE_URL` - Your Neon PostgreSQL URL
- ✅ `SECRET_KEY` - Django secret key

### Email (New - Required)
- 📧 `EMAIL_HOST` = `smtp.gmail.com`
- 📧 `EMAIL_PORT` = `587`
- 📧 `EMAIL_USE_TLS` = `True`
- 📧 `EMAIL_HOST_USER` = Your Gmail address
- 📧 `EMAIL_HOST_PASSWORD` = Gmail app password
- 📧 `DEFAULT_FROM_EMAIL` = Your Gmail address (same as EMAIL_HOST_USER)

### Optional (Existing)
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = Your domain
- `CSRF_COOKIE_SECURE` = `True`
- `SESSION_COOKIE_SECURE` = `True`

---

## 🧪 Testing Email Verification

### Test Locally (Optional)

1. **Create a `.env` file** in your project root (if not exists):
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

2. **Run the server:**
```bash
cd /workspaces/CLASS-XII/api
python manage.py runserver
```

3. **Test signup:**
   - Go to `/auth/signup/`
   - Fill in the form
   - Should redirect to verification page
   - Check your email for the 6-digit code

### Test on Vercel

1. **Deploy your code** (push to git)
2. **Wait for deployment** to complete
3. **Visit your site** and try signup
4. **Check email** for verification code

---

## 📱 User Flow

### Before (Old Flow):
```
Signup → Account Created → Login
```

### After (New Flow):
```
Signup → Verify Email → Enter 6-Digit Code → Account Created → Auto-Login
```

### Detailed Flow:

1. **User fills signup form**
   - Username
   - Email
   - Password
   - Confirm Password

2. **System validates data**
   - Checks if username exists
   - Checks if email exists
   - Validates password strength

3. **System sends verification email**
   - Generates 6-digit code
   - Stores in database (expires in 10 min)
   - Sends styled HTML email

4. **User enters verification code**
   - Has 5 attempts
   - Can resend code if needed
   - Code expires after 10 minutes

5. **System verifies code**
   - Creates user account
   - Auto-login
   - Redirects to account page

---

## 🎨 Email Template

The verification email includes:
- ✨ Styled with your terminal/matrix theme
- 🔢 Large, bold 6-digit code
- ⏱️ Expiration time (10 minutes)
- ⚠️ Security warning
- 📧 Professional footer

Example:
```
┌────────────────────────────────────┐
│  → CLASS XII PYTHON ASSEMBLY ←     │
├────────────────────────────────────┤
│  Hello username,                   │
│                                    │
│  Your verification code is:        │
│                                    │
│       ┌─────────────┐              │
│       │   123456    │              │
│       └─────────────┘              │
│                                    │
│  Valid for 10 minutes              │
└────────────────────────────────────┘
```

---

## 🔒 Security Features

1. **Expiring Codes**: 10-minute validity
2. **Rate Limiting**: 5 attempts per code
3. **Unique Codes**: Random 6-digit generation
4. **Session-Based**: Email stored in session only
5. **Auto-Cleanup**: Old verifications deleted automatically
6. **Hashed Passwords**: Password hashed before storage

---

## 🐛 Troubleshooting

### "Failed to send verification email"
- **Check**: Gmail app password is correct
- **Check**: Email address is valid
- **Check**: Environment variables are set in Vercel
- **Try**: Generate new app password

### "Verification code expired"
- **Solution**: Click "Resend Code"
- **Note**: Codes expire after 10 minutes

### "Too many failed attempts"
- **Solution**: Click "Start over" and signup again
- **Note**: Limited to 5 attempts per code

### Email not received
- **Check**: Spam/Junk folder
- **Check**: Email address is correct
- **Wait**: Can take up to 1-2 minutes
- **Try**: Click "Resend Code"

### Gmail blocking
- **Error**: "Username and Password not accepted"
- **Solution**: Make sure 2-Step Verification is enabled
- **Solution**: Use App Password, not your Gmail password
- **Check**: Less secure app access is NOT enabled (use App Passwords instead)

---

## 📊 Admin Features

View verification attempts in Django admin:
- Access: `/admin/auth_app/emailverification/`
- See: All pending and completed verifications
- Monitor: Failed attempts and expired codes
- Debug: Check which codes were sent

---

## 🚀 Deployment Steps

1. **Push code to Git**
   ```bash
   git add .
   git commit -m "Add email verification system"
   git push
   ```

2. **Add environment variables** in Vercel (see Step 2 above)

3. **Redeploy** (automatic after push)

4. **Test** the signup flow

---

## ⚡ Quick Reference

### Gmail Settings
```
Host: smtp.gmail.com
Port: 587
Security: TLS
User: your-email@gmail.com
Password: [16-character app password]
```

### Vercel Environment Variables
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### Code Expiration
- ⏱️ **Validity**: 10 minutes
- 🔄 **Can Resend**: Yes, unlimited
- 🔢 **Attempts**: 5 per code
- 🗑️ **Cleanup**: After 1 hour (failed) or 24 hours (success)

---

## ✅ All Set!

Your email verification system is ready! Users will now need to verify their email before accessing the platform.

**Need Help?**
- Check Django admin for verification logs
- View server logs in Vercel dashboard
- Test with your own email first

🎉 **Happy Coding!**
