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
- *Note*: `REACT_APP_SUPABASE_URL` and `REACT_APP_SUPABASE_ANON_KEY` are automatically mapped from `SUPABASE_URL` and `SUPABASE_KEY` in `docker-compose.yml`. You do NOT need to add them manually unless you want to override them.


### 3. Exposing Ports & Domains
- **Frontend**: Map port `3000` to your main domain (e.g., `https://analysis.yourdomain.com`).
- **Backend (Optional)**: If you need to access the API directly (e.g., from n8n outside the Docker network), map port `8000` to a subdomain (e.g., `https://api.analysis.yourdomain.com`).
    - *Note*: If n8n is on the **same** VPS and Docker network, you can access it internally (see below).

#### n8n Optimization (Critical for Large Files)
For reliable handling of large files (150MB+), add this variable to your n8n service in Coolify:
- `N8N_DEFAULT_BINARY_DATA_MODE`: `filesystem`
- `SUPABASE_SERVICE_ROLE_KEY`: `your-service-role-key` (Required for Supabase Uploads)

### 4. Deploy
- Click **Deploy**. Check the deployment logs for any errors.

### 5. Critical: Configure Proxy for Large Uploads
The Nginx proxy usually defaults to 1MB uploads. To allow auction files (20MB+) you **MUST** configure the proxy:
1. Go to your **Backend Service** in Coolify.
2. Find the **Proxy / Nginx / Configuration** section.
3. In actual Coolify versions, this is often under **General -> Configuration -> Custom Nginx Configuration**.
4. Paste the following:
   ```nginx
   client_max_body_size 500M;
   proxy_read_timeout 300;
   proxy_connect_timeout 300;
   proxy_send_timeout 300;
   ```
5. **Save** and **Redeploy** the service.

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

## Auto-deploy on `git push` (webhook)

This application deploys from `kotechile/_domain_analysis` branch `main`. The push trigger is a
**manual GitHub webhook**, not a GitHub App source — the app was created from the public-repo path,
which does not register a webhook on its own.

| Field | Value |
| --- | --- |
| Payload URL | `https://coolify.giniloh.com/webhooks/source/github/events/manual` |
| Content type | `application/json` |
| Secret | the app's `manual_webhook_secret_github` (Coolify UI → app → Webhooks, or `GET /api/v1/applications/<uuid>`) |
| Events | `push` only |

Coolify matches the delivery on `repository.full_name` **and** branch, so a push to any branch other
than `main` is answered `200` and silently deploys nothing. Inspect a delivery's `response.payload`:
`"Deployment queued."` is success; `"No matching application or invalid signature."` means repo,
branch or secret is wrong (the endpoint deliberately does not say which).

Rotating the secret in Coolify requires re-sending the whole `config` object on
`PATCH /repos/kotechile/_domain_analysis/hooks/<id>` — `config[url]` and `config[content_type]`
are mandatory or GitHub answers `422 url cannot be blank`.

### Do not hand-write Traefik labels in `docker-compose.yml`

Routing for `scout.buildomain.com` is generated by Coolify from the domain set on the `frontend`
service (stored in `docker_compose_domains`) — it emits the `http-0-…` router (redirect to https)
and the `https-0-…` router (Let's Encrypt TLS). A hand-written router without an explicit
`.service` label cannot be auto-linked when the container owns several services, and Traefik drops
it on every config rebuild:

```
ERR Router scout-insecure cannot be linked automatically with multiple Services:
    ["http-0-…-frontend-aca3" "https-0-…-frontend-aca3" "scout-svc"]
```

Keep only `traefik.enable=true` and `traefik.docker.network=coolify` in the compose file.
