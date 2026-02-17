# 🔧 Coolify Environment Variables for Google OAuth

Quick reference for the exact environment variables to add/update in Coolify for Google sign-in.

## ✅ Required Variables

Add these to your Supabase service in Coolify:

```bash
# Enable Google OAuth Provider
GOTRUE_EXTERNAL_GOOGLE_ENABLED=true

# Google OAuth Credentials (from Google Cloud Console)
GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOTRUE_EXTERNAL_GOOGLE_SECRET=your-google-client-secret-here

# OAuth Redirect URI (must match Google Cloud Console)
GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI=https://sbdomain.giniloh.com/auth/v1/callback
```

## ✅ Verify These Existing Variables

These should already be set (from your current setup):

```bash
# Site URL (used for redirects)
GOTRUE_SITE_URL=${SERVICE_URL_SUPABASEKONG}
# Which should be: https://sbdomain.giniloh.com

# API External URL
API_EXTERNAL_URL=http://supabase-kong:8000

# Supabase URLs
SUPABASE_URL=${SERVICE_URL_SUPABASEKONG}
SUPABASE_PUBLIC_URL=${SERVICE_URL_SUPABASEKONG}
```

## 🔄 Optional: Additional Redirect URLs

If you have a frontend application on a different domain:

```bash
# Add your frontend callback URLs (comma-separated)
ADDITIONAL_REDIRECT_URLS=https://your-frontend.com/auth/callback,https://your-frontend.com
```

## 📝 Step-by-Step in Coolify

1. **Go to your Supabase service** in Coolify
2. **Click on "Environment Variables"** tab
3. **Click "Add Variable"** for each new variable above
4. **Save** all changes
5. **Restart the service** (important!)

## ⚠️ Important Notes

- **No quotes needed** - Coolify handles values as-is
- **Case sensitive** - Variable names must match exactly
- **Restart required** - GoTrue service must restart to load new OAuth config
- **Redirect URI must match exactly** - Check Google Cloud Console

## 🧪 Quick Test

After setting variables and restarting, test with:

```bash
curl "https://sbdomain.giniloh.com/auth/v1/authorize?provider=google"
```

This should redirect to Google's OAuth consent screen.

