# Build arguments
ARG REACT_APP_API_URL=/api/v1
ARG REACT_APP_SUPABASE_URL
ARG REACT_APP_SUPABASE_ANON_KEY
ARG REACT_APP_URL=https://scout.buildomain.com

# Multi-stage build for Angular app
FROM node:20 AS build

# Pass build arg to environment
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_SUPABASE_URL=$REACT_APP_SUPABASE_URL
ENV REACT_APP_SUPABASE_ANON_KEY=$REACT_APP_SUPABASE_ANON_KEY
ENV REACT_APP_URL=$REACT_APP_URL
ENV NG_CLI_ANALYTICS=false
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Set working directory
WORKDIR /app

# Copy package files first (better layer caching)
COPY package*.json ./

# Install dependencies - capture full output to file for debugging
RUN npm install 2>&1 | tee /tmp/npm-install.log || (cat /tmp/npm-install.log && exit 1)

# Copy source code
COPY . .

# Build the Angular application with output capture
RUN npm run build > /tmp/build.log 2>&1 || (cat /tmp/build.log && exit 1)

# Find and verify build output - Angular 21 outputs to different paths
RUN echo "=== Checking for build output ===" && \
    find /app/dist -name "index.html" -type f 2>/dev/null | head -5 && \
    if [ -d "/app/dist/angular-version/browser" ]; then \
        echo "Found build at: /app/dist/angular-version/browser"; \
    elif [ -f "/app/dist/index.html" ]; then \
        echo "Found build at: /app/dist/"; \
        mkdir -p /app/dist/angular-version/browser && \
        cp -r /app/dist/* /app/dist/angular-version/browser/ 2>/dev/null || true; \
    else \
        echo "Build output not found!"; \
        ls -la /app/dist/ 2>/dev/null || echo "No dist folder"; \
        exit 1; \
    fi

# Production stage with nginx
FROM nginx:alpine

# Install curl for healthchecks and envsubst for config templating
RUN apk add --no-cache curl gettext

# Copy built app from build stage to nginx serving directory
COPY --from=build /app/dist/angular-version/browser /usr/share/nginx/html

# Copy env template for runtime substitution
COPY src/assets/env.template.js /usr/share/nginx/html/assets/

# Copy nginx configuration template
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 80

# Health check for Coolify - checks if nginx is responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Use entrypoint script to substitute env vars and start nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
