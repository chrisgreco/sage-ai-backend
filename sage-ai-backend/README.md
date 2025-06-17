<<<<<<< HEAD
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
=======
# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/tips-tricks/custom-domain#step-by-step-guide)
>>>>>>> f9c00ce7acd928a1089fc02ab4cdf9e509bf5fc5
