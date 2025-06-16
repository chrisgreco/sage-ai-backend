# Sage AI Backend

A sophisticated multi-agent AI debate system powered by LiveKit, featuring 5 distinct AI personalities that participate in intelligent voice debates.

## 🎭 AI Agent Personalities

### 1. **Dr. Alexandra Wright** - The Moderator
- **Voice**: Professional, clear
- **Role**: Guides discussions, maintains balance, asks clarifying questions
- **Speaking Style**: "That's an interesting point, let's explore...", "I'd like to hear more about..."

### 2. **Professor James Chen** - The Expert
- **Voice**: Authoritative, warm
- **Role**: Provides in-depth analysis, explains complex concepts, references research
- **Speaking Style**: "Research indicates...", "From an analytical perspective..."

### 3. **Sarah Rodriguez** - The Challenger
- **Voice**: Dynamic, engaging
- **Role**: Questions assumptions, plays devil's advocate, identifies logical flaws
- **Speaking Style**: "But what if...", "Have we considered...", "Playing devil's advocate..."

### 4. **Dr. Maya Patel** - The Synthesizer
- **Voice**: Thoughtful, harmonious
- **Role**: Finds common ground, synthesizes viewpoints, proposes frameworks
- **Speaking Style**: "Building on both perspectives...", "What I'm hearing is..."

### 5. **Dr. Robert Kim** - The Fact-Checker
- **Voice**: Precise, trustworthy
- **Role**: Verifies claims, provides evidence, corrects misinformation
- **Speaking Style**: "To verify that claim...", "According to reliable sources..."

## 🚀 Features

- **Multi-Agent AI System**: 5 unique AI personalities with distinct voices and roles
- **Real-time Voice AI**: Powered by Cartesia TTS and Deepgram STT
- **Intelligent Conversation**: Context-aware triggers and natural debate flow
- **LiveKit Integration**: Scalable real-time communication infrastructure
- **RESTful API**: Easy integration with frontend applications

## 📋 Prerequisites

### Required API Keys

1. **LiveKit**: Get from [LiveKit Cloud](https://cloud.livekit.io/)
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`

2. **OpenAI**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
   - `OPENAI_API_KEY`

3. **Deepgram**: Get from [Deepgram](https://deepgram.com/)
   - `DEEPGRAM_API_KEY`

4. **Cartesia**: Get from [Cartesia AI](https://cartesia.ai/)
   - `CARTESIA_API_KEY`

## 🛠️ Installation

### 1. Clone and Setup
```bash
cd sage-ai-backend
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy the example environment file
cp example.env .env

# Edit .env with your actual API keys
nano .env
```

### 3. Install Dependencies
```bash
# Install core dependencies
pip install livekit-api livekit-agents[openai,cartesia,deepgram,silero,turn-detector]

# Install specific plugins
pip install livekit-plugins-openai livekit-plugins-cartesia livekit-plugins-deepgram
```

## 🏃‍♂️ Usage

### Web Service Mode (Default)
```bash
python app.py
```

The API will be available at `http://localhost:8000`

### Key Endpoints

#### 1. Create Debate Room
```bash
POST /debate
{
  "topic": "The future of artificial intelligence",
  "room_name": "ai-debate-2024",
  "participant_name": "John"
}
```

#### 2. Launch AI Agents 🎯
```bash
POST /launch-ai-agents
{
  "room_name": "ai-debate-2024",
  "topic": "The future of artificial intelligence",
  "start_agents": true
}
```

#### 3. Check Agent Status
```bash
GET /ai-agents/status
```

#### 4. Stop AI Agents
```bash
POST /ai-agents/stop
{
  "room_name": "ai-debate-2024"
}
```

### Direct Agent Mode
```bash
# Start AI agents directly for a specific room
python ai_debate_agents.py start --room "debate-room-name"

# Alternative startup script
python start_ai_agents.py
```

## 🔧 API Documentation

### Health Check
- **GET** `/health` - Service health and configuration status

### Debate Management
- **POST** `/debate` - Create a new debate room and participant token
- **POST** `/participant-token` - Generate token for additional participants

### AI Agent Management
- **POST** `/launch-ai-agents` - Start multi-agent AI system for a room
- **GET** `/ai-agents/status` - Check running agent processes
- **POST** `/ai-agents/stop` - Stop agents for a specific room

### Debug
- **POST** `/debug` - Debug endpoint to inspect requests

## 🏗️ Architecture

```
Frontend (Lovable) 
    ↓
FastAPI Backend (Token Generation)
    ↓
LiveKit Cloud (Real-time Communication)
    ↓
AI Agents Process (Multi-Agent Debate System)
    ├── Cartesia TTS (Voice Synthesis)
    ├── Deepgram STT (Speech Recognition)
    ├── OpenAI GPT (Language Model)
    └── Agent Orchestration
```

## 🎯 AI Agent Features

### Intelligent Triggers
Each agent has specific conversation triggers:
- **Moderator**: "unclear", "confusing", "off-topic"
- **Expert**: "research", "study", "explain", "analysis"
- **Challenger**: "always", "never", "assumption", "bias"
- **Synthesizer**: "disagree", "common ground", "synthesis"
- **Fact-Checker**: "statistics", "evidence", "verify"

### Voice Emotions
- **Moderator**: Professional, calm
- **Expert**: Thoughtful, authoritative
- **Challenger**: Engaging, curious
- **Synthesizer**: Warm, understanding
- **Fact-Checker**: Precise, trustworthy

### Conversation Management
- Automatic speaking queue management
- Silence detection and intervention
- Context-aware response generation
- Balanced participation enforcement

## 🐳 Docker Deployment

```bash
# Build and run
docker build -t sage-ai-backend .
docker run -p 8000:8000 --env-file .env sage-ai-backend
```

## 🌐 Render Deployment

The backend is configured for Render deployment with:
- `render.yaml` configuration
- Health check endpoint
- CORS for Lovable domains
- Environment variable management

## 🧪 Testing

```bash
# Test API endpoints
curl -X GET http://localhost:8000/health

# Test debate creation
curl -X POST http://localhost:8000/debate \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Ethics", "participant_name": "TestUser"}'

# Test AI agent launch
curl -X POST http://localhost:8000/launch-ai-agents \
  -H "Content-Type: application/json" \
  -d '{"room_name": "test-room", "topic": "AI Ethics"}'
```

## 🔍 Troubleshooting

### Common Issues

1. **Missing API Keys**
   ```
   Error: Missing required environment variables: CARTESIA_API_KEY
   ```
   Solution: Ensure all required API keys are set in your `.env` file

2. **LiveKit Connection Issues**
   ```
   Error: LiveKit configuration missing
   ```
   Solution: Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`

3. **Agent Launch Failures**
   ```
   Error: Failed to launch AI agents
   ```
   Solution: Check logs for specific import errors or missing dependencies

### Debug Mode
Enable detailed logging:
```bash
export LIVEKIT_LOG_LEVEL=debug
python app.py
```

## 📚 Dependencies

Core AI & Voice:
- `livekit-agents` - AI agent framework
- `livekit-plugins-cartesia` - Text-to-speech
- `livekit-plugins-deepgram` - Speech-to-text
- `livekit-plugins-openai` - Language models

Web Service:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation

## 🤝 Contributing

1. Ensure all API keys are configured
2. Test with a simple debate topic first
3. Monitor agent logs for conversation flow
4. Report issues with specific error messages

## 📄 License

MIT License - see LICENSE file for details 