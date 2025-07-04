# Sage AI Debate Moderator

A minimal LiveKit-powered AI debate moderator agent built with Context7 best practices.

## Features

- **AI-Powered Moderation**: Uses Perplexity AI for intelligent debate moderation and fact-checking
- **Voice Interaction**: Real-time speech-to-text via Deepgram and text-to-speech via OpenAI
- **LiveKit Integration**: Built on LiveKit Agents framework for reliable real-time communication
- **Minimal Architecture**: Clean, focused implementation following LiveKit documentation patterns

## Quick Start

### Prerequisites

- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- API keys for OpenAI, Perplexity, and Deepgram

### Installation

1. Clone the repository:
```bash
git clone https://github.com/chrisgreco/sage-ai-backend.git
cd sage-ai-backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp example.env .env
# Edit .env with your actual API keys
```

4. Run the agent:
```bash
# Development mode
python debate_moderator_agent.py dev

# Production mode  
python debate_moderator_agent.py start
```

## Environment Variables

Required:
- `LIVEKIT_URL` - Your LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `OPENAI_API_KEY` - OpenAI API key for TTS
- `PERPLEXITY_API_KEY` - Perplexity API key for LLM
- `DEEPGRAM_API_KEY` - Deepgram API key for STT

Optional:

- `PERPLEXITY_MODEL` - Perplexity model (default: "llama-3.1-sonar-small-128k-online")

## Deployment

### Render

The project includes `render.yaml` for easy deployment to Render:

1. Connect your GitHub repository to Render
2. Configure environment variables in Render dashboard
3. Deploy automatically from main branch

### Docker

```bash
docker build -t sage-ai-agent .
docker run --env-file .env sage-ai-agent
```

## Architecture

- **LiveKit Agents**: Core framework for real-time AI agents
- **Perplexity AI**: LLM for intelligent responses and fact-checking
- **OpenAI TTS**: High-quality text-to-speech synthesis
- **Deepgram STT**: Fast, accurate speech-to-text
- **Silero VAD**: Voice activity detection

## Function Tools

The agent provides these interactive tools:

- `set_debate_topic` - Set and contextualize debate topics
- `moderate_discussion` - Control discussion flow and speaking turns
- `fact_check_statement` - Real-time fact verification using Perplexity

## License

MIT License - see LICENSE file for details.

## Current Status

The API endpoints for token generation and room creation are working. The background worker service is currently a placeholder that will be expanded in future versions to provide real-time AI moderation capabilities.

## Critical Deployment Fix Needed

Based on analysis of the LiveKit voice assistant example, our current architecture is incorrect:

### Current (Wrong) Pattern:
- Frontend calls `/launch-ai-agents` endpoint
- Backend spawns agent subprocess per request
- Agents try to join specific rooms

### Correct Pattern (From LiveKit Example):
- Agents run as **persistent workers** using `python multi_personality_agent.py start`
- Agents **automatically join ALL new rooms**
- Frontend connects directly to LiveKit rooms using tokens
- No "launch agents" - they're always running

### Required Changes:

1. **Deploy Persistent Agent Worker:**
   ```bash
   # Run this on Render as a separate service
   python multi_personality_agent.py start
   ```

2. **Remove Agent Launching:**
   - Remove `/launch-ai-agents` endpoint
   - Frontend should only get room tokens
   - Agents join automatically when rooms are created

3. **Frontend Pattern:**
   - Use @livekit/components-react
   - Connect directly to LiveKit rooms
   - Monitor participants (agents will appear automatically)

### Immediate Fix:
Run agents as persistent workers on Render, not subprocess per request. 