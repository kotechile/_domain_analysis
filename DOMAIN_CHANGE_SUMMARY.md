# 🔄 Domain Name Change Summary

## Changes Made

Updated all domain references from:
- `sb_domain.aichieve.net` → `sbdomain.aichieve.net`
- `sb_content.aichieve.net` → `sbcontent.aichieve.net` (no references found)

## ✅ Files Updated

### Configuration Files
- ✅ `backend/.env` - Updated `SUPABASE_URL` and PostgreSQL connection string

### Documentation Files
- ✅ `GOOGLE_SIGNIN_SETUP.md` - All domain references updated
- ✅ `COOLIFY_GOOGLE_OAUTH_VARS.md` - All domain references updated
- ✅ `SUPABASE_CONFIGURATION_COMPLETE.md` - All domain references updated
- ✅ `SUPABASE_MIGRATION.md` - All domain references updated

## 📝 Key Changes

### Backend Configuration (`backend/.env`)
```bash
# Before
SUPABASE_URL=https://sb_domain.aichieve.net
postgresql://postgres:mySecurePass123@sb_domain.aichieve.net:5434/postgres?sslmode=require

# After
SUPABASE_URL=https://sbdomain.aichieve.net
postgresql://postgres:mySecurePass123@sbdomain.aichieve.net:5434/postgres?sslmode=require
```

## ⚠️ Important: Next Steps

### 1. Update Coolify Environment Variables

You need to update your Coolify environment variables to match the new domain:

**In your Supabase service in Coolify, update:**
- `SERVICE_FQDN_SUPABASEKONG` → `sbdomain.aichieve.net`
- `SERVICE_URL_SUPABASEKONG` → `https://sbdomain.aichieve.net`
- `GOTRUE_SITE_URL` → `https://sbdomain.aichieve.net`
- `SUPABASE_URL` → `https://sbdomain.aichieve.net`
- `SUPABASE_PUBLIC_URL` → `https://sbdomain.aichieve.net`

### 2. Update Google OAuth Configuration

In Google Cloud Console, update the authorized redirect URIs:
- Old: `https://sb_domain.aichieve.net/auth/v1/callback`
- New: `https://sbdomain.aichieve.net/auth/v1/callback`

### 3. Update DNS Records

Make sure your DNS records point to the new domain:
- `sbdomain.aichieve.net` → Your server IP
- `sbcontent.aichieve.net` → Your server IP (if applicable)

### 4. Restart Services

After updating Coolify environment variables:
1. **Restart your Supabase service** in Coolify
2. **Restart your backend server** to pick up the new `.env` configuration

### 5. Test Connection

```bash
# Test Supabase connection
cd backend
source venv/bin/activate
python test_supabase.py

# Test API endpoint
curl https://sbdomain.aichieve.net/auth/v1/authorize?provider=google
```

## ✅ Verification

All references to `sb_domain.aichieve.net` have been replaced with `sbdomain.aichieve.net`.

No references to `sb_content.aichieve.net` were found in the codebase.

## 📋 Checklist

- [x] Updated `backend/.env` file
- [x] Updated all documentation files
- [ ] Update Coolify environment variables
- [ ] Update Google OAuth redirect URIs
- [ ] Update DNS records (if needed)
- [ ] Restart Supabase service in Coolify
- [ ] Restart backend server
- [ ] Test Supabase connection
- [ ] Test Google OAuth flow


















