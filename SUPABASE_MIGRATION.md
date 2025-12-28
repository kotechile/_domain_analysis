# Self-Hosted Supabase Migration Guide

## ✅ Configuration Updated

Your `.env` files have been updated to use your self-hosted Supabase instance at `sbdomain.aichieve.net`.

## 📋 Next Steps Required

### 1. Get Your Supabase API Keys

You need to retrieve the API keys from your self-hosted Supabase instance:

1. **Access your Supabase dashboard** at `https://sbdomain.aichieve.net` (or your configured URL)
2. **Navigate to Settings > API**
3. **Copy the following keys:**
   - **Anon/Public Key** → Use for `SUPABASE_KEY`
   - **Service Role Key** → Use for `SUPABASE_SERVICE_ROLE_KEY`

### 2. Update Backend .env File

Edit `/backend/.env` and replace the placeholder values:

```bash
# Replace these placeholders:
SUPABASE_KEY=YOUR_ANON_KEY_HERE
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY_HERE
```

### 3. Verify Supabase API URL

The API URL has been set to:
```
SUPABASE_URL=https://sbdomain.aichieve.net
```

**If your self-hosted Supabase API is on a different URL or port**, update this value. Common alternatives:
- `http://sbdomain.aichieve.net:8000` (if using HTTP on port 8000)
- `https://sbdomain.aichieve.net:443` (if using HTTPS on custom port)

### 4. Test the Connection

After updating the keys, test the connection:

```bash
cd backend
source venv/bin/activate
python test_supabase.py
```

## 📝 Connection Details

**PostgreSQL Connection String:**
```
postgresql://postgres:mySecurePass123@sbdomain.aichieve.net:5434/postgres?sslmode=require
```

This connection string is stored for reference. The application uses the Supabase Python SDK which requires the API URL and keys, not the direct PostgreSQL connection.

## 🔧 Files Updated

- ✅ `backend/.env` - Updated with self-hosted Supabase URL and placeholders for keys
- ✅ `backend/.env.backup` - Backup of your original configuration

## ⚠️ Important Notes

1. **API Keys Required**: The Supabase Python SDK requires API keys (anon and service_role), not just the PostgreSQL connection string.

2. **API URL**: Make sure your self-hosted Supabase API is accessible at the URL you configure. The API typically runs on port 443 (HTTPS) or 8000 (HTTP).

3. **Service Role Key**: This key has admin privileges and should be kept secret. Never commit it to version control.

4. **SSL Mode**: Your PostgreSQL connection uses `sslmode=require`, which is good for security.

## 🚀 After Configuration

Once you've updated the API keys:

1. Restart your backend server
2. Test the connection using `python test_supabase.py`
3. Verify the health endpoint: `curl http://localhost:8010/api/v1/health`

## 📚 Additional Resources

- Supabase Self-Hosted Documentation: Check your Supabase instance docs
- API Keys Location: Settings > API in your Supabase dashboard
