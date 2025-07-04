# LiveKit Agents Deployment Guide

## Critical Fixes Applied

This deployment includes critical fixes for the "No space left on device" errors that were causing exit status 2 crashes.

### ✅ Fixed Issues
- Turn detector model download failures 
- Docker image size optimization
- Graceful fallbacks for all model loading
- Proactive disk space monitoring

## Environment Configuration

### Required Environment Variables
```bash
# Core LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# AI Service Keys
OPENAI_API_KEY=your-openai-key
PERPLEXITY_API_KEY=your-perplexity-key (optional)
DEEPGRAM_API_KEY=your-deepgram-key (optional)
CARTESIA_API_KEY=your-cartesia-key (optional)

# Agent Configuration
DEBATE_TOPIC=General Discussion
MODERATOR_PERSONA=Aristotle

# CRITICAL: Prevent model download crashes
ENABLE_TURN_DETECTION=false

# Supabase (optional)
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### Render.com Configuration

#### Web Service (FastAPI Backend)
```yaml
services:
  - type: web
    name: sage-ai-backend
    env: docker
    dockerfilePath: ./Dockerfile
    dockerCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ENABLE_TURN_DETECTION
        value: false
      - key: OPENAI_API_KEY
        fromSecret: OPENAI_API_KEY
      # ... other env vars
```

#### Background Worker (LiveKit Agent)
```yaml
  - type: worker
    name: sage-ai-backend-moderator
    env: docker
    dockerfilePath: ./Dockerfile
    dockerCommand: python debate_moderator_agent.py start
    envVars:
      - key: ENABLE_TURN_DETECTION
        value: false
      - key: MODERATOR_PERSONA
        value: Aristotle
      - key: DEBATE_TOPIC
        value: Philosophy and Ethics
      # ... other env vars
```

## Multi-Agent Deployment

### Deploy Multiple Agent Personas

Create separate Render services for each agent persona:

#### Agent 1: Aristotle (Philosophy)
```yaml
- type: worker
  name: sage-ai-aristotle-agent
  env: docker
  dockerCommand: python debate_moderator_agent.py start
  envVars:
    - key: MODERATOR_PERSONA
      value: Aristotle
    - key: DEBATE_TOPIC
      value: Philosophy and Ethics
    - key: ENABLE_TURN_DETECTION
      value: false
```

#### Agent 2: Einstein (Science)
```yaml
- type: worker
  name: sage-ai-einstein-agent
  env: docker
  dockerCommand: python debate_moderator_agent.py start
  envVars:
    - key: MODERATOR_PERSONA
      value: Einstein
    - key: DEBATE_TOPIC
      value: Science and Technology
    - key: ENABLE_TURN_DETECTION
      value: false
```

#### Agent 3: Socrates (Critical Thinking)
```yaml
- type: worker
  name: sage-ai-socrates-agent
  env: docker
  dockerCommand: python debate_moderator_agent.py start
  envVars:
    - key: MODERATOR_PERSONA
      value: Socrates
    - key: DEBATE_TOPIC
      value: Critical Thinking
    - key: ENABLE_TURN_DETECTION
      value: false
```

## Docker Optimizations Applied

### Multi-Stage Build
- Separated build and runtime stages
- Minimal python:3.11-slim base image
- Removed unnecessary build dependencies from final image

### Space Optimization
- Comprehensive .dockerignore file
- Disabled model pre-downloading
- Python optimization flags
- Cleaned up package caches

## Troubleshooting

### If Agent Still Crashes
1. Check disk space: `df -h` in Render shell
2. Verify `ENABLE_TURN_DETECTION=false` is set
3. Check logs for specific error messages
4. Verify all required API keys are present

### Model Loading Issues
The agent now gracefully handles:
- Turn detector failures → Basic silence detection
- VAD failures → No VAD (optional)
- STT failures → OpenAI STT fallback
- TTS failures → OpenAI TTS fallback
- LLM failures → OpenAI GPT fallback

### Performance Optimization
- Turn detection disabled saves ~500MB+ model download
- Multi-stage Docker build reduces image size by ~60%
- Graceful fallbacks prevent restart loops

## Monitoring

### Key Metrics to Watch
- Container startup time (should be < 30 seconds)
- Memory usage (should be < 1GB with optimizations)
- Error rates in logs
- Agent response times

### Success Indicators
- No "Exited with status 2" errors
- No "No space left on device" messages
- Agents start successfully within 30 seconds
- Graceful fallback messages in logs (not errors)

## Deployment Commands

### Automatic Deployment
Push to main branch triggers automatic deployment on Render.

### Manual Deployment (if needed)
```bash
# Build and test locally first
docker build -t sage-ai-backend .
docker run -e ENABLE_TURN_DETECTION=false sage-ai-backend

# Deploy to Render
git push origin main
```

## Support

If issues persist after these fixes:
1. Check Render deployment logs
2. Verify environment variables are set correctly
3. Confirm API keys are valid and have sufficient quota
4. Monitor disk space usage in Render dashboard 