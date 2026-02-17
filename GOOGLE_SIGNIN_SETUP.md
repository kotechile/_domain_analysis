# 🔐 Google Sign-In Setup Guide for Self-Hosted Supabase

This guide will walk you through enabling Google OAuth authentication in your self-hosted Supabase instance running on Hostinger VPS with Coolify.

## 📋 Prerequisites

- Access to your Google Cloud Console
- Access to your Coolify dashboard
- Your Supabase domain: `sbdomain.giniloh.com`
- Your frontend domain (if different)

---

## Step 1: Create Google OAuth Credentials

### 1.1 Go to Google Cloud Console

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Go to **APIs & Services** → **Credentials**

### 1.2 Create OAuth 2.0 Client ID

1. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
2. If prompted, configure the OAuth consent screen first:
   - **User Type**: External (or Internal if using Google Workspace)
   - **App name**: Domain Analysis System (or your app name)
   - **User support email**: Your email
   - **Developer contact information**: Your email
   - **Scopes**: Add `email`, `profile`, `openid`
   - **Test users**: Add your email if using External type

3. Back in Credentials, select **OAuth client ID**
4. **Application type**: Web application
5. **Name**: Supabase Auth (or any name)
6. **Authorized JavaScript origins**:
   ```
   https://sbdomain.giniloh.com
   http://sbdomain.giniloh.com:8000
   ```
   (Add your frontend domain if different)

7. **Authorized redirect URIs**:
   ```
   https://sbdomain.giniloh.com/auth/v1/callback
   http://sbdomain.giniloh.com:8000/auth/v1/callback
   ```
   (Add your frontend callback URL if you have one)

8. Click **CREATE**
9. **Copy the Client ID and Client Secret** - you'll need these in Step 3

---

## Step 2: Configure Supabase Environment Variables in Coolify

### 2.1 Access Coolify Dashboard

1. Log into your Coolify dashboard
2. Navigate to your Supabase service
3. Go to **Environment Variables** section

### 2.2 Add Google OAuth Variables

Add or update the following environment variables:

```bash
# Google OAuth Configuration
GOTRUE_EXTERNAL_GOOGLE_ENABLED=true
GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID=your-google-client-id-here
GOTRUE_EXTERNAL_GOOGLE_SECRET=your-google-client-secret-here
GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI=https://sbdomain.giniloh.com/auth/v1/callback

# Site URL (important for redirects)
GOTRUE_SITE_URL=https://sbdomain.giniloh.com

# Additional redirect URLs (if you have a frontend app)
ADDITIONAL_REDIRECT_URLS=https://your-frontend-domain.com/auth/callback,https://your-frontend-domain.com
```

### 2.3 Verify Existing Variables

Make sure these are set correctly (they should already be there):

```bash
# These should already exist from your setup
SUPABASE_URL=https://sbdomain.giniloh.com
SUPABASE_PUBLIC_URL=https://sbdomain.giniloh.com
API_EXTERNAL_URL=http://supabase-kong:8000
```

### 2.4 Save and Restart

1. **Save** the environment variables
2. **Restart** your Supabase service in Coolify
   - This is important - GoTrue needs to restart to pick up the new OAuth config

---

## Step 3: Verify Configuration

### 3.1 Check GoTrue Service

1. In Coolify, check the logs for the `supabase-auth` service
2. Look for any errors related to Google OAuth
3. You should see logs indicating Google provider is enabled

### 3.2 Test the OAuth Endpoint

You can test if Google OAuth is configured by checking:

```bash
# Get the auth URL (replace with your actual domain)
curl https://sbdomain.giniloh.com/auth/v1/authorize?provider=google
```

This should redirect you to Google's OAuth consent screen.

---

## Step 4: Update Frontend (Optional - If You Have a Frontend App)

If you have a React/Next.js frontend, you'll need to integrate Supabase Auth:

### 4.1 Install Supabase Client

```bash
cd frontend
npm install @supabase/supabase-js
```

### 4.2 Create Supabase Client

Create `frontend/src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'https://sbdomain.giniloh.com'
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'your-anon-key'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 4.3 Add Environment Variables

Update `frontend/.env`:

```bash
REACT_APP_SUPABASE_URL=https://sbdomain.giniloh.com
REACT_APP_SUPABASE_ANON_KEY=your-supabase-anon-key
REACT_APP_API_URL=http://localhost:8010/api/v1
```

### 4.4 Create Sign-In Component

Example component `frontend/src/components/GoogleSignIn.tsx`:

```typescript
import { supabase } from '../lib/supabase'

export const GoogleSignIn = () => {
  const handleGoogleSignIn = async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    })
    
    if (error) {
      console.error('Error signing in:', error)
    }
  }

  return (
    <button onClick={handleGoogleSignIn}>
      Sign in with Google
    </button>
  )
}
```

### 4.5 Create Callback Handler

Create `frontend/src/pages/AuthCallback.tsx`:

```typescript
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export const AuthCallback = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const handleAuthCallback = async () => {
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Auth error:', error)
        navigate('/login')
        return
      }

      if (data.session) {
        // User is authenticated
        navigate('/dashboard')
      }
    }

    handleAuthCallback()
  }, [navigate])

  return <div>Completing sign in...</div>
}
```

---

## Step 5: Configure Database (If Needed)

### 5.1 Enable Email Sign-Up (Optional)

If you want to allow email sign-up alongside Google:

In Coolify, set:
```bash
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false  # Set to true if you want auto-confirm
```

### 5.2 Check User Table

After a successful Google sign-in, check your database:

```sql
-- Connect to your Supabase database
SELECT id, email, raw_user_meta_data, created_at 
FROM auth.users 
ORDER BY created_at DESC 
LIMIT 5;
```

You should see new users with `raw_user_meta_data` containing Google profile information.

---

## Step 6: Troubleshooting

### Issue: "Redirect URI mismatch"

**Solution**: 
- Verify the redirect URI in Google Cloud Console matches exactly:
  - `https://sbdomain.giniloh.com/auth/v1/callback`
- Check `GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI` in Coolify
- Make sure there are no trailing slashes

### Issue: "OAuth provider not enabled"

**Solution**:
- Verify `GOTRUE_EXTERNAL_GOOGLE_ENABLED=true` in Coolify
- Restart the Supabase service
- Check GoTrue logs for errors

### Issue: "Invalid client credentials"

**Solution**:
- Double-check `GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID` and `GOTRUE_EXTERNAL_GOOGLE_SECRET`
- Make sure there are no extra spaces or quotes
- Verify the credentials in Google Cloud Console

### Issue: "Connection refused" or SSL errors

**Solution**:
- Verify your domain is accessible: `https://sbdomain.giniloh.com`
- Check SSL certificate is valid
- Verify firewall rules allow HTTPS (port 443)

---

## Step 7: Test the Integration

### 7.1 Test via Supabase Dashboard

1. Access your Supabase Studio (if available):
   - `https://sbdomain.giniloh.com` (or your configured Studio URL)
2. Try signing in with Google

### 7.2 Test via API

```bash
# Get the authorization URL
curl "https://sbdomain.giniloh.com/auth/v1/authorize?provider=google"

# This should return a redirect URL to Google
```

### 7.3 Test via Frontend

If you've set up the frontend:
1. Click "Sign in with Google"
2. Complete Google OAuth flow
3. Verify you're redirected back to your app
4. Check that user session is created

---

## 📝 Summary Checklist

- [ ] Created Google OAuth credentials in Google Cloud Console
- [ ] Added authorized redirect URI: `https://sbdomain.giniloh.com/auth/v1/callback`
- [ ] Set `GOTRUE_EXTERNAL_GOOGLE_ENABLED=true` in Coolify
- [ ] Set `GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID` in Coolify
- [ ] Set `GOTRUE_EXTERNAL_GOOGLE_SECRET` in Coolify
- [ ] Set `GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI` in Coolify
- [ ] Verified `GOTRUE_SITE_URL` is set correctly
- [ ] Restarted Supabase service in Coolify
- [ ] Tested OAuth flow
- [ ] Verified user creation in database

---

## 🔒 Security Best Practices

1. **Never commit OAuth secrets** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate credentials** periodically
4. **Monitor OAuth usage** in Google Cloud Console
5. **Set up proper RLS policies** in Supabase for user data
6. **Use HTTPS** for all OAuth redirects

---

## 📚 Additional Resources

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GoTrue Configuration](https://supabase.com/docs/guides/auth/auth-helpers/configuring-third-party-oauth-providers)

---

## 🆘 Need Help?

If you encounter issues:
1. Check Coolify logs for the `supabase-auth` service
2. Verify all environment variables are set correctly
3. Test the OAuth endpoint directly
4. Check Google Cloud Console for OAuth errors
5. Review Supabase/GoTrue documentation

