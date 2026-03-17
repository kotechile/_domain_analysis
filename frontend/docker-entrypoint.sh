#!/bin/sh

# Entrypoint script for Angular frontend container
# Substitutes environment variables in nginx config and generates runtime env.js

# Set default values if not provided
if [ -z "$API_BACKEND_URL" ]; then
    echo "WARNING: API_BACKEND_URL not set, using default http://backend:8000"
    export API_BACKEND_URL="http://backend:8000"
fi

# Set default Supabase values
if [ -z "$REACT_APP_SUPABASE_URL" ]; then
    echo "WARNING: REACT_APP_SUPABASE_URL not set, using default"
    export REACT_APP_SUPABASE_URL="https://sbdomain.buildomain.com"
fi

if [ -z "$REACT_APP_SUPABASE_ANON_KEY" ]; then
    echo "WARNING: REACT_APP_SUPABASE_ANON_KEY not set"
    export REACT_APP_SUPABASE_ANON_KEY=""
fi

if [ -z "$REACT_APP_API_URL" ]; then
    export REACT_APP_API_URL="/api/v1"
fi

if [ -z "$REACT_APP_URL" ]; then
    export REACT_APP_URL="https://scout.buildomain.com"
fi

echo "Configuring nginx with backend URL: $API_BACKEND_URL"
echo "Supabase URL: $REACT_APP_SUPABASE_URL"

# Substitute environment variables in nginx config
envsubst '$API_BACKEND_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Generate runtime environment config for Angular
# This allows the frontend to read env vars at runtime
envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js

echo "Generated runtime environment config"

# For Docker environments where backend may not resolve at startup,
# we skip the config test because nginx will fail if the upstream doesn't resolve.
# Instead, we just start nginx and let it handle connection errors at runtime.
echo "Starting nginx..."
exec nginx -g "daemon off;"
