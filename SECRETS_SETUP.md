# 🔐 Secrets Management Setup Guide

This guide explains how to set up secure secret management for the Domain Analysis System using Supabase as the secrets store.

## 🏗️ Architecture Overview

- **Essential Secrets**: Stored in `.env` files (Supabase credentials, app secrets)
- **API Credentials**: Stored securely in Supabase `secrets` table
- **Runtime Retrieval**: Services fetch credentials from Supabase when needed
- **Caching**: Credentials are cached for 5 minutes to reduce database calls

## 📋 Setup Steps

### 1. **Set Up Supabase Database**

1. **Create the secrets table** by running the migration:
   ```sql
   -- Run this in your Supabase SQL editor
   -- File: backend/supabase_migrations/001_create_secrets_table.sql
   ```

2. **Verify the table was created**:
   ```sql
   SELECT * FROM secrets LIMIT 5;
   ```

### 2. **Configure Essential Secrets**

Update your `.env` files with your Supabase credentials:

#### **Backend `.env`** (already created):
```bash
# Replace with your actual Supabase credentials
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Generate a strong secret key
SECRET_KEY=your-secret-key-here-make-it-long-and-random
```

#### **Frontend `.env`** (already created):
```bash
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_DEBUG=false
```

### 3. **Add API Credentials to Supabase**

Use the secrets management script to add your API credentials:

```bash
# Navigate to backend directory
cd backend

# Make the script executable
chmod +x scripts/manage_secrets.py

# Add DataForSEO credentials
python scripts/manage_secrets.py add dataforseo '{"login": "your-login", "password": "your-password", "api_url": "https://api.dataforseo.com/v3"}'

# Add Gemini API key
python scripts/manage_secrets.py add gemini '{"api_key": "your-gemini-api-key"}'

# Add OpenAI API key (optional)
python scripts/manage_secrets.py add openai '{"api_key": "your-openai-api-key"}'

# Add other credentials as needed
python scripts/manage_secrets.py add google_trends '{"api_key": "your-google-trends-api-key"}'
python scripts/manage_secrets.py add shareasale '{"api_key": "your-shareasale-api-key"}'
# ... etc
```

### 4. **Verify Secrets Are Working**

```bash
# List all secrets
python scripts/manage_secrets.py list

# Get a specific secret
python scripts/manage_secrets.py get dataforseo

# Test the application
python src/main.py
```

## 🔧 Available Services

The following services can store credentials in Supabase:

### **Core APIs**
- `dataforseo` - DataForSEO API credentials
- `gemini` - Google Gemini API key
- `openai` - OpenAI API key (optional)
- `wayback_machine` - Wayback Machine configuration

### **Affiliate Networks**
- `shareasale` - ShareASale API key
- `impact` - Impact API key
- `amazon_associates` - Amazon Associates tag
- `cj` - Commission Junction API key
- `partnerize` - Partnerize API key

### **Social Media**
- `reddit` - Reddit API credentials
- `twitter` - Twitter Bearer token
- `tiktok` - TikTok API key

### **Content Optimization**
- `surfer_seo` - Surfer SEO API key
- `frase` - Frase API key
- `coschedule` - CoSchedule API key

### **Export Platforms**
- `google_docs` - Google Docs API key
- `notion` - Notion API key
- `wordpress` - WordPress API credentials

### **Other Services**
- `google_trends` - Google Trends API key
- `linkup` - LinkUp API key

## 🛠️ Management Commands

### **List All Secrets**
```bash
python scripts/manage_secrets.py list
```

### **Get Specific Secret**
```bash
python scripts/manage_secrets.py get dataforseo
```

### **Add/Update Secret**
```bash
python scripts/manage_secrets.py add service_name '{"key": "value"}'
```

### **Clear Cache**
```bash
# Clear all caches
python scripts/manage_secrets.py clear

# Clear specific service cache
python scripts/manage_secrets.py clear dataforseo
```

## 🔒 Security Features

### **Row Level Security (RLS)**
- Only authenticated users can read secrets
- Only service role can modify secrets
- Secrets are encrypted in transit and at rest

### **Caching**
- Credentials are cached for 5 minutes
- Reduces database calls and improves performance
- Cache can be cleared manually if needed

### **Error Handling**
- Graceful fallback if secrets are not available
- Detailed logging for debugging
- No sensitive data in logs

## 🚨 Security Best Practices

1. **Never commit real API keys** to git repositories
2. **Use strong, unique secret keys** for each service
3. **Rotate API keys regularly** (especially if exposed)
4. **Monitor access logs** for unusual activity
5. **Use least privilege principle** for database access
6. **Regularly audit** stored secrets

## 🔍 Troubleshooting

### **"Secret not found" errors**
- Check if the secret exists: `python scripts/manage_secrets.py get service_name`
- Verify the service name is correct
- Check Supabase connection

### **"Credentials not available" errors**
- Verify Supabase credentials in `.env`
- Check if the secrets table exists
- Ensure RLS policies are correct

### **Performance issues**
- Clear the cache: `python scripts/manage_secrets.py clear`
- Check database connection
- Monitor cache hit rates

## 📚 Next Steps

1. **Set up your Supabase project** and run the migration
2. **Configure your `.env` files** with Supabase credentials
3. **Add your API credentials** using the management script
4. **Test the system** to ensure everything works
5. **Deploy to production** with proper environment variables

## 🆘 Support

If you encounter issues:
1. Check the logs for detailed error messages
2. Verify your Supabase configuration
3. Test individual secrets using the management script
4. Review the security policies in Supabase




