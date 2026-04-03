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

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source code
COPY . .

# Build the Angular application
RUN npm run build > /tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }

# Verify build output exists
RUN ls -la /app/dist/angular-version/browser

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
