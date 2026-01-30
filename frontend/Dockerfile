# Multi-stage build for React app
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
# Install dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
# Copy source code
COPY . .

# Disable CI=true to prevent warnings from failing the build
ENV CI=false
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS="--max-old-space-size=2048"

# Build the application
RUN CI=false npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built app from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
