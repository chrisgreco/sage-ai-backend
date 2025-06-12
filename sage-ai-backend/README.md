# Sage AI Backend

This repository contains the backend for the Sage AI LiveKit debate moderator, built with FastAPI and Python 3.10. It provides a dual-service architecture for Render deployment:

1. **Web Service**: Handles HTTP API endpoints for creating debates and generating LiveKit tokens
2. **Background Worker**: Runs continuously to join LiveKit rooms and provide real-time AI moderation

## Architecture

The application is designed to run in two modes:

### Web Service Mode
- Exposes HTTP API endpoints for frontend integration
- Handles room creation and token generation
- Provides health check endpoint

### Background Worker Mode
- Continuously connects to active LiveKit rooms
- Processes real-time events (joins, messages, etc.)
- Provides AI-powered debate moderation using OpenAI

## API Endpoints

### Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy"
}
```

### Create Debate
```
POST /debate
```
Request:
```json
{
  "topic": "AI Ethics in Education",
  "room_name": "optional-custom-room-name" (optional)
}
```
Response:
```json
{
  "status": "success",
  "message": "Debate created on topic: AI Ethics in Education",
  "room_name": "debate-ai-ethics-in-education",
  "livekit_url": "wss://example.livekit.cloud",
  "token": "generated_livekit_token"
}
```

### Connect to LiveKit
```
GET /connect
```
Response:
```json
{
  "status": "success",
  "message": "Ready to connect to LiveKit",
  "livekit_url": "wss://example.livekit.cloud",
  "token": "generated_livekit_token"
}
```

## Environment Variables

The application requires the following environment variables:

```
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key (optional)
SERVICE_MODE=web (or "worker" for background mode)
PORT=8000 (for web service)
```

## Deployment

The application is configured for deployment on Render using Docker. The `render.yaml` file defines both the web service and background worker:

```yaml
services:
  # Web Service for API endpoints
  - type: web
    name: sage-ai-backend
    # ...config...

  # Background Worker for continuous processing
  - type: worker
    name: sage-ai-moderator
    # ...config...
```

## Development

To run the application locally:

```bash
# Set up environment variables in .env file
cp .env.example .env
# Edit .env with your API keys

# Run as web service
python app.py

# Run as background worker
SERVICE_MODE=worker python app.py
```

You can also use Docker:

```bash
# Build the image
docker build -t sage-ai-backend .

# Run as web service
docker run -p 8000:8000 -e SERVICE_MODE=web sage-ai-backend

# Run as background worker
docker run -e SERVICE_MODE=worker sage-ai-backend
```

## Integration with Frontend

The frontend should interact with the web service endpoints to:
1. Create debate rooms
2. Get tokens for LiveKit connection
3. Join the LiveKit room

The background worker will automatically join active rooms and provide AI moderation.