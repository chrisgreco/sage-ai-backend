# Sage AI Backend

This repository contains the backend API for the Sage AI application. It provides a Docker-ready deployment setup for Render.

## Features

- Multi-stage Docker build for optimized container size
- Nginx configuration for proper SPA routing
- Environment variable handling
- GitHub Actions CI/CD workflow
- Render deployment configuration

## Deployment

The application is configured for deployment on Render using Docker. See the deployment instructions in the documentation.

## Development

To run the application locally using Docker:

```bash
# Build the Docker image
npm run docker:build

# Run the Docker container
npm run docker:run
```

The application will be available at http://localhost:8080 