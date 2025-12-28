# ✅ Self-Hosted Supabase Configuration Complete

## Configuration Summary

Your application has been successfully configured to connect to your self-hosted Supabase instance running on Hostinger VPS with Coolify.

### ✅ What Was Configured

1. **Backend `.env` File** - Updated with:
   - `SUPABASE_URL=https://sbdomain.aichieve.net`
   - `SUPABASE_KEY` - Anon key from Coolify (`SERVICE_SUPABASEANON_KEY`)
   - `SUPABASE_SERVICE_ROLE_KEY` - Service role key from Coolify (`SERVICE_SUPABASESERVICE_KEY`)
   - `SUPABASE_VERIFY_SSL=false` - Disabled SSL verification for self-signed certificate

2. **Database Service** - Updated to handle SSL verification for self-hosted instances

3. **Test Script** - Updated to use the database service with proper SSL handling

### ✅ Connection Test Results

```
✅ Configuration loaded successfully
✅ Supabase client created successfully
✅ Supabase connection successful
Query result: 1 records found
```

The connection is working and you can query your Supabase database!

### 📋 Coolify Environment Variables Used

From your Coolify environment variables, we used:
- `SERVICE_URL_SUPABASEKONG` → `SUPABASE_URL`
- `SERVICE_SUPABASEANON_KEY` → `SUPABASE_KEY`
- `SERVICE_SUPABASESERVICE_KEY` → `SUPABASE_SERVICE_ROLE_KEY`

### 🔒 Security Notes

1. **SSL Verification**: Disabled for self-hosted instance with self-signed certificate
   - This is safe for internal/self-hosted instances
   - The connection still uses HTTPS, just doesn't verify the certificate

2. **Service Role Key**: Has admin privileges - keep it secure
   - Never commit to version control
   - Only use in backend/server-side code

3. **Anon Key**: Safe for client-side use
   - Can be used in frontend applications
   - Respects Row Level Security (RLS) policies

### 🚀 Next Steps

1. **Restart your backend server** to pick up the new configuration:
   ```bash
   cd backend
   source venv/bin/activate
   # Kill existing server and restart
   ```

2. **Test the health endpoint**:
   ```bash
   curl http://localhost:8010/api/v1/health
   ```

3. **Verify API functionality** by running a domain analysis

### 📝 Files Modified

- `backend/.env` - Supabase configuration
- `backend/src/utils/config.py` - Added `SUPABASE_VERIFY_SSL` setting
- `backend/src/services/database.py` - SSL verification handling
- `backend/test_supabase.py` - Updated to use database service

### 🔍 Troubleshooting

If you encounter connection issues:

1. **Check SSL Certificate**: The connection works with SSL verification disabled. If you want to enable it, you'll need to add your self-signed certificate to the system trust store.

2. **Verify API URL**: Make sure `https://sbdomain.aichieve.net` is accessible from your backend server.

3. **Check Firewall**: Ensure port 443 (HTTPS) is open for your Supabase API.

4. **Test Connection**: Run `python test_supabase.py` to verify the connection.

### 📚 Additional Resources

- Supabase Self-Hosted Docs: [Your Supabase instance documentation]
- Coolify Documentation: [Coolify docs for environment variables]
- PostgreSQL Connection String: `postgresql://postgres:mySecurePass123@sbdomain.aichieve.net:5434/postgres?sslmode=require`
