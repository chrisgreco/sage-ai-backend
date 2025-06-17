# Sage AI Backend

This repository contains the backend services for the Sage AI debate moderator application.

## Architecture

The backend is built with a dual-service architecture on Render:

1. **Web Service**: A FastAPI application that provides API endpoints for token generation and room creation.
2. **Background Worker**: A service that will eventually connect to LiveKit rooms and provide real-time AI moderation.

## Dependencies

- Python 3.10+
- FastAPI
- LiveKit Python SDK (`livekit-api`)
- OpenAI
- Deepgram (for future speech-to-text capabilities)

## Environment Variables

The following environment variables are required:

```
LIVEKIT_URL=https://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
OPENAI_API_KEY=your-openai-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key (optional for now)
SERVICE_MODE=web or worker
```

## API Endpoints

### Health Check

```
GET /health
```

Returns a simple health status to verify the service is running.

### LiveKit Connection

```
GET /connect
```

Returns a LiveKit token for the backend service, along with connection details.

### Create Debate Room

```
POST /debate
{
  "topic": "Should AI be regulated?",
  "room_name": "ai-debate-123" (optional)
}
```

Creates a new debate room in LiveKit and returns a token with room creation permissions.

## Deployment

This project is set up for deployment on Render with the included `render.yaml` blueprint file. 

The deployment creates:

1. A Web Service for API endpoints (on the free plan)
2. A Background Worker for AI moderation (on the starter plan - $7/month)

## Local Development

1. Clone the repository
2. Create a `.env` file with the required environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run the service: `python app.py`

The service will start on port 8000 by default.

## Current Status

The API endpoints for token generation and room creation are working. The background worker service is currently a placeholder that will be expanded in future versions to provide real-time AI moderation capabilities. 