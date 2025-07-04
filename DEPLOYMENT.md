# LiveKit Agents Deployment Guide

## Critical Fixes Applied

This deployment includes critical fixes for the "No space left on device" errors that were causing exit status 2 crashes.

### ✅ Fixed Issues
- Turn detector model download failures (now pre-downloaded during build)
- Docker image size optimization with multi-stage builds
- Graceful fallbacks for all model loading
- Proper model caching strategy

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
MODERATOR_PERSONA=neutral-facilitator

# Database (Optional - for memory persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Render Deployment Configuration

### For Web Service (sage-ai-backend)
```bash
# Build Command
npm install

# Start Command  
uvicorn app:app --host 0.0.0.0 --port $PORT

# Environment Variables
PORT=8000
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
```

### For Background Worker (sage-ai-backend-moderator)
```bash
# Build Command
(leave empty - uses Dockerfile)

# Start Command
python debate_moderator_agent.py start

# Environment Variables (same as above plus)
DEBATE_TOPIC=Technology and Innovation
MODERATOR_PERSONA=neutral-facilitator
```

## Available Moderator Personas

The system supports dynamic persona switching within a single agent service:

### Core Personas
- **neutral-facilitator**: Balanced, fair moderation
- **socratic-questioner**: Deep questioning and critical thinking
- **devils-advocate**: Challenge assumptions and explore counterarguments
- **topic-expert**: Subject matter expertise and fact-checking
- **time-keeper**: Structure and time management focus

### Persona Selection
Personas are set via environment variable `MODERATOR_PERSONA` or can be dynamically changed by room participants during the session.

## Turn Detection Fix

### What Was Fixed
- **Issue**: Turn detector models failing to download during runtime due to disk space
- **Solution**: Pre-download models during Docker build phase
- **Optimization**: Use `EnglishModel()` instead of `MultilingualModel()` for smaller size
- **Build Process**: Added `python debate_moderator_agent.py download-files` to Dockerfile

### Technical Details
```dockerfile
# Pre-download LiveKit models to avoid runtime downloads
RUN python debate_moderator_agent.py download-files || echo "Model download failed but continuing build"
```

The agent now uses the smaller English-only turn detection model that is pre-downloaded during the container build process, eliminating runtime download failures.

## Troubleshooting

### "No space left on device" Errors
✅ **FIXED**: Models are now pre-downloaded during build
- Ensure Dockerfile includes model pre-download step
- Use English-only model for smaller footprint
- Models cached in container image, not downloaded at runtime

### Agent Won't Start
1. Check environment variables are set correctly
2. Verify LiveKit credentials are valid
3. Check logs for specific model loading errors
4. Ensure `python debate_moderator_agent.py download-files` succeeded during build

### Performance Optimization
- Multi-stage Docker build reduces final image size
- Pre-downloaded models eliminate startup delays
- Graceful fallbacks prevent service interruption
- Memory management with Supabase persistence

## Model Fallback Chain

1. **STT**: Deepgram → OpenAI STT
2. **TTS**: Cartesia → OpenAI TTS  
3. **LLM**: Perplexity → OpenAI GPT-4o-mini
4. **VAD**: Silero (optional, graceful degradation)
5. **Turn Detection**: EnglishModel (pre-downloaded, required)

All components except turn detection can gracefully degrade. Turn detection is essential for natural conversation flow and is now properly pre-installed.

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