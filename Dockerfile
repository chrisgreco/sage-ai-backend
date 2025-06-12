FROM node:18-alpine AS build
WORKDIR /app

# Install dependencies first (better caching)
COPY package*.json ./
COPY bun.lockb ./
RUN npm ci

# Copy only necessary files
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY index.html ./
COPY postcss.config.js ./
COPY tailwind.config.ts ./
COPY components.json ./
COPY public ./public
COPY src ./src

# Run the prebuild script to copy environment variables
COPY copy-env.js ./
RUN node copy-env.js

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Add non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Copy built files and configuration
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions
RUN chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid

# Switch to non-root user
USER appuser

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 