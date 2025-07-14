# Sage AI Debate Moderator

A minimal LiveKit-powered AI debate moderator agent built with Context7 best practices.

## Features

- **AI-Powered Moderation**: Uses OpenAI GPT-4o-mini for intelligent debate moderation
- **Real-time Fact-Checking**: Integrated Brave Search API for live fact verification during debates
- **Voice Interaction**: Real-time speech-to-text via Deepgram and text-to-speech via Cartesia
- **LiveKit Integration**: Built on LiveKit Agents framework for reliable real-time communication
- **Minimal Architecture**: Clean, focused implementation following LiveKit documentation patterns

## Quick Start

### Prerequisites

- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- API keys for OpenAI, Brave Search, and Deepgram

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

3. Configure environment variables in Render dashboard:
   - Set all required API keys in your Render service environment variables
   - No local .env files needed - Render manages environment variables directly

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
- `OPENAI_API_KEY` - OpenAI API key for LLM
- `BRAVE_API_KEY` - Brave Search API key for fact-checking
- `DEEPGRAM_API_KEY` - Deepgram API key for STT
- `CARTESIA_API_KEY` - Cartesia API key for TTS

Optional:
- `SUPABASE_URL` - Supabase URL for memory management
- `SUPABASE_KEY` - Supabase service key for memory management

## Deployment

### Render

The project includes `render.yaml` for easy deployment to Render:

1. Connect your GitHub repository to Render
2. Configure environment variables in Render dashboard
3. Deploy automatically from main branch

### Docker

```bash
docker build -t sage-ai-agent .
docker run sage-ai-agent
```
Note: Environment variables are managed by Render directly in production

## Architecture

- **LiveKit Agents**: Core framework for real-time AI agents
- **OpenAI GPT-4o-mini**: LLM for intelligent responses and moderation
- **Brave Search API**: Real-time fact-checking and information verification
- **Cartesia TTS**: High-quality text-to-speech synthesis with British male voice
- **Deepgram STT**: Fast, accurate speech-to-text
- **Silero VAD**: Voice activity detection
- **Supabase**: Optional memory management for conversation history

## Function Tools

The agent provides these interactive tools:

- `set_debate_topic` - Set and contextualize debate topics
- `moderate_discussion` - Control discussion flow and speaking turns
- `brave_search` - Search the web for real-time information using Brave Search API
- `fact_check_statement` - Real-time fact verification using Brave Search API

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