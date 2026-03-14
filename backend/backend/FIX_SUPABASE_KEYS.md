# Fix Supabase JWSInvalidSignature Error

## Root Cause
The `JWSInvalidSignature` error means the JWT key doesn't match the JWT_SECRET on your self-hosted Supabase instance.

## Solution Steps

### 1. Get Fresh Keys from Coolify

1. Log into your Coolify Dashboard: https://coolify.giniloh.com
2. Navigate to your Supabase service (sbdomain.giniloh.com)
3. Click on "Environment Variables" or "Settings"
4. Look for these variables:
   - `SERVICE_SUPABASEANON_KEY` (or `ANON_KEY`)
   - `SERVICE_SUPABASESERVICE_KEY` (or `SERVICE_ROLE_KEY`)
   - `JWT_SECRET` (this is the signing secret)

### 2. Update Your Domain Analysis Resource

1. In Coolify, go to your Domain Analysis resource
2. Navigate to "Environment Variables"
3. Update these variables with the values from Step 1:

   ```
   SUPABASE_URL=https://sbdomain.giniloh.com
   SUPABASE_KEY=<paste ANON_KEY here>
   SUPABASE_SERVICE_ROLE_KEY=<paste SERVICE_ROLE_KEY here>
   SUPABASE_VERIFY_SSL=false
   ```

4. **Important**: Make sure there are NO extra quotes, spaces, or newlines

### 3. Redeploy

1. Click "Deploy" or "Restart"
2. Wait for deployment to complete
3. Test: `curl https://scout.buildomain.com/api/v1/health`

## Alternative: If Keys Were Rotated

If you recently rotated the JWT_SECRET in Coolify:

1. Go to your Supabase service in Coolify
2. Look for "Generate Keys" or "Reset JWT" option
3. This will generate new keys matching the new JWT_SECRET
4. Copy the new keys to your Domain Analysis environment variables

## Verify the Fix

After redeployment, check the logs:
1. In Coolify → Domain Analysis → "Logs"
2. Look for: "Supabase client initialized successfully"
3. Should NOT see: "JWSError JWSInvalidSignature"

## Local .env vs Coolify

**Important**: Your local `backend/.env` file is NOT used by Coolify.
Coolify uses its own environment variables set in the dashboard.
Make sure the changes are in Coolify, not just locally.
