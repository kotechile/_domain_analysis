#!/bin/sh

# Entrypoint script for Angular frontend container
# Substitutes environment variables in nginx config and starts nginx

# Set default backend URL if not provided
# In Coolify, the backend service name is passed as an environment variable
# Can also use direct IP if needed
if [ -z "$API_BACKEND_URL" ]; then
    # Try to use the service name from docker-compose if available
    # Otherwise default to localhost (for single-container setups)
    export API_BACKEND_URL="http://backend:8000"
fi

echo "Configuring nginx with backend URL: $API_BACKEND_URL"

# Substitute environment variables in nginx config
envsubst '$API_BACKEND_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Verify the config is valid
nginx -t

if [ $? -ne 0 ]; then
    echo "ERROR: nginx configuration test failed"
    exit 1
fi

echo "Starting nginx..."
exec nginx -g "daemon off;"
