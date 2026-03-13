#!/bin/sh

# Entrypoint script for Angular frontend container
# Substitutes environment variables in nginx config and starts nginx

# Set default backend URL if not provided
# In Coolify, the backend service name is passed as an environment variable
# Can also use direct IP if needed
if [ -z "$API_BACKEND_URL" ]; then
    echo "WARNING: API_BACKEND_URL not set, using default http://backend:8000"
    echo "Set this environment variable in Coolify to point to your backend service"
    export API_BACKEND_URL="http://backend:8000"
fi

echo "Configuring nginx with backend URL: $API_BACKEND_URL"

# Substitute environment variables in nginx config
envsubst '$API_BACKEND_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# For Docker environments where backend may not resolve at startup,
# we skip the config test because nginx will fail if the upstream doesn't resolve.
# Instead, we just start nginx and let it handle connection errors at runtime.
echo "Starting nginx..."
exec nginx -g "daemon off;"
