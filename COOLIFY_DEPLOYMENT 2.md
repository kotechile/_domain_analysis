# Deploying to Coolify

This guide explains how to deploy the **Domain Analysis** project to your VPS using Coolify.

## Prerequisites

- A VPS with Coolify installed.
- Access to your Coolify dashboard.
- This repository pushed to a Git provider (GitHub/GitLab) connected to Coolify.

## Deployment Steps

### 1. Create a New Service
1. In Coolify, go to your project/environment.
2. Click **+ New Resource**.
3. Select **Docker Compose** (or "Git Repository" -> "Docker Compose").
4. Select your repository and branch.

### 2. Configuration
Coolify will read the `docker-compose.yml` file. You need to configure the following:

#### Build Pack
- Ensure **Docker Compose** is selected as the build pack.

#### Environment Variables
You must add the following environment variables in the Coolify UI for the service. These match your local `.env`.

**Backend Variables:**
- `SUPABASE_URL`: Your Supabase URL.
- `SUPABASE_KEY`: Your Supabase Service Role Key.
- `DATAFORSEO_LOGIN`: Your DataForSEO Login.
- `DATAFORSEO_PASSWORD`: Your DataForSEO Password.
- `GEMINI_API_KEY`: Your Gemini API Key.
- `SECRET_KEY`: A strong random string for security.
- `ALLOWED_ORIGINS`: `["https://your-domain.com"]` (Update with your actual Coolify-generated domain).
- `REDIS_URL`: `redis://redis:6379` (This is already set in docker-compose, but good to double-check).

**Frontend Variables:**
- `REACT_APP_API_URL`: `/api/v1` (This allows the frontend to talk to the backend via the internal proxy).

### 3. Exposing Ports & Domains
- **Frontend**: Map port `3000` to your main domain (e.g., `https://analysis.yourdomain.com`).
- **Backend (Optional)**: If you need to access the API directly (e.g., from n8n outside the Docker network), map port `8000` to a subdomain (e.g., `https://api.analysis.yourdomain.com`).
    - *Note*: If n8n is on the **same** VPS and Docker network, you can access it internally (see below).

### 4. Deploy
- Click **Deploy**. Check the deployment logs for any errors.

## Connecting n8n (Same VPS)

If n8n is running in a Docker container on the same VPS:

1. **Same Network**: Ensure n8n and this project are on the same Docker network.
    - In Coolify, you can often share networks or use the host internal IP.
2. **Internal Access**: Use `http://domain-analysis-backend:8000` (service name) if on the same network.
3. **Public Access**: If n8n is separate/cloud-hosted, use the public Backend URL you configured above (e.g., `https://api.analysis.yourdomain.com`).
    - **Auth**: Ensure n8n sends the necessary headers if your API requires auth.

## Troubleshooting
- **PDF Generation Fails**: Check logs for `weasyprint` errors. The `Dockerfile` has been updated with necessary libraries (`libcairo2`, etc.).
- **CORS Errors**: Check `ALLOWED_ORIGINS` in your environment variables.
- **Connection Refused**: Ensure the Frontend container can reach the Backend container. The `nginx.conf` is set to proxy `/api/` to `http://backend:8000`.
