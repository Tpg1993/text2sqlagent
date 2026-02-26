# Build stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Serve stage
# Using nginx unprivileged image for non-root execution
FROM nginxinc/nginx-unprivileged:alpine

# Copy built assets from build stage
# The unprivileged image runs as nginx user (UID 101)
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Replace default config for SPA routing and to listen on unprivileged port 8080
USER root
RUN echo 'server { \
    listen 8080; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html index.htm; \
    try_files $uri $uri/ /index.html; \
    } \
    }' > /etc/nginx/conf.d/default.conf

# Switch back to non-root user
USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
