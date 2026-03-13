# Build arguments
ARG REACT_APP_API_URL=/api/v1
ARG REACT_APP_SUPABASE_URL
ARG REACT_APP_SUPABASE_ANON_KEY
ARG REACT_APP_URL=https://scout.buildomain.com

# Multi-stage build for Angular app
FROM node:20-alpine as build

# Pass build arg to environment
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_SUPABASE_URL=$REACT_APP_SUPABASE_URL
ENV REACT_APP_SUPABASE_ANON_KEY=$REACT_APP_SUPABASE_ANON_KEY
ENV REACT_APP_URL=$REACT_APP_URL

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the Angular application
RUN npm run build
RUN ls -la /app/dist/angular-version/browser || echo "Build directory not found"

# Production stage with nginx
FROM nginx:alpine

# Install curl for healthchecks
RUN apk add --no-cache curl

# Copy built app from build stage to nginx serving directory
COPY --from=build /app/dist/angular-version/browser /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Validate nginx configuration
RUN nginx -t

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
