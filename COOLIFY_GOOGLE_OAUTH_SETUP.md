# Google OAuth Configuration for giniloh.com

Based on your configuration, here are the exact values you should use.

## 1. Google Cloud Console Configuration
**Location**: APIs & Services > Credentials > OAuth 2.0 Client IDs

*   **Authorized JavaScript origins**:
    *   `https://sbdomain.giniloh.com`
    *   `http://localhost:3010` (for local development)
    *   `https://[YOUR_FRONTEND_DOMAIN]` (if deployed)

*   **Authorized redirect URIs**:
    *   `https://sbdomain.giniloh.com/auth/v1/callback`
    *(This is the value you asked about - it is CORRECT)*

## 2. Coolify / Supabase Configuration
**Location**: Coolify Dashboard > Supabase Service > Environment Variables

Ensure these variables are set and the service is **RESTARTED** after specific changes.

```bash
GOTRUE_EXTERNAL_GOOGLE_ENABLED=true
GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID=[YOUR_CLIENT_ID]
GOTRUE_EXTERNAL_GOOGLE_SECRET=[YOUR_CLIENT_SECRET]
GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI=https://sbdomain.giniloh.com/auth/v1/callback

# CRITICAL: Allow redirects back to your frontend
ADDITIONAL_REDIRECT_URLS=http://localhost:3010/auth/callback,https://[YOUR_FRONTEND_DOMAIN]/auth/callback
```

## 3. How the Redirect Flow Works
1.  **Frontend** initiates login and asks Supabase to redirect back to `http://localhost:3010/auth/callback`.
2.  **Supabase** redirects the user to **Google**.
3.  **Google** authenticates user and redirects back to **Supabase** (`https://sbdomain.giniloh.com/auth/v1/callback`).
    *   *This is why Google needs the Supabase URL.*
4.  **Supabase** processes the login and redirects back to **Frontend** (`http://localhost:3010/auth/callback`).
    *   *This is why Supabase needs the Frontend URL in `ADDITIONAL_REDIRECT_URLS`.*

## 4. Troubleshooting Common Errors

### "Unable to exchange external code: invalid_client"
**Cause:** This definitive error means the **Client Secret** or **Client ID** inside Coolify is WRONG.

**Check 1: The Client ID**
It must end in `.apps.googleusercontent.com`.
*   **Wrong:** `445556218231-` (Truncated)
*   **Correct:** `445556218231-abc123xyz.apps.googleusercontent.com`

**Check 2: The Client Secret**
It usually starts with `GOCSPX-`.
*   Ensure there are **NO SPACES** at the start or end.
*   Ensure there are **NO QUOTES** around the value in Coolify.

**Fix:**
1. Go to Google Cloud Console.
2. Copy the **ENTIRE** Client ID (ending in `.apps.googleusercontent.com`).
3. Copy the **ENTIRE** Client Secret.
4. Go to Coolify -> Supabase -> Environment Variables.
5. Update `GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID` and `GOTRUE_EXTERNAL_GOOGLE_SECRET`.
6. **Restart** the Supabase Service.

### "Redirect URI mismatch" or "400 Bad Request"
**Cause:** The Redirect URI in Google Console does not match `GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI`.
**Fix:**
Ensure both are exactly `https://sbdomain.giniloh.com/auth/v1/callback` (no trailing slash).
