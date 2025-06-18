# Sage AI Dual-Agent Deployment Guide

## 🎯 Overview

This guide explains how to deploy the Sage AI two-agent debate system using **Option 1: Background Workers** architecture.

### Agent Architecture

- **Aristotle (Moderator)**: `debate_moderator_agent.py` - Logical moderator with reason + structure
- **Socrates (Philosopher)**: `debate_philosopher_agent.py` - Inquisitive challenger with questioning + truth-seeking

Both agents join the **same LiveKit room** with different participant identities to create a dynamic debate.

## 🚀 Render.com Deployment (Recommended)

### Step 1: Create Environment Variable Group

1. Go to your Render dashboard
2. Create an environment variable group named `sage-ai-env`
3. Add the following variables:

```
LIVEKIT_URL=wss://your-livekit-url.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
OPENAI_API_KEY=your-openai-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

### Step 2: Deploy Using render.yaml

The included `render.yaml` configures **3 services**:

1. **Web Service**: `sage-ai-backend` - HTTP API + token generation
2. **Background Worker 1**: `aristotle-agent` - Moderator agent
3. **Background Worker 2**: `socrates-agent` - Philosopher agent

### Step 3: Deploy to Render

```bash
# Option A: Connect GitHub repo to Render dashboard
# - Use the included render.yaml for automatic deployment
# - All 3 services will be created automatically

# Option B: Manual deployment via CLI
render deploy
```

## 🎭 How It Works

### Room Joining Process

1. **Frontend calls** `/launch-ai-agents` endpoint
2. **Web service spawns** both agent processes locally 
3. **Both agents connect** to the same LiveKit room:
   - Aristotle joins as participant `aristotle_moderator_001`
   - Socrates joins as participant `socrates_philosopher_001`
4. **Agents begin debating** the specified topic

### Token Generation

Each agent gets a unique LiveKit token:

```python
# Aristotle token
aristotle_token = AccessToken(api_key, api_secret)
aristotle_token.identity = "aristotle_moderator_001"
aristotle_token.name = "Aristotle"

# Socrates token  
socrates_token = AccessToken(api_key, api_secret)
socrates_token.identity = "socrates_philosopher_001"
socrates_token.name = "Socrates"
```

### API Endpoints

- **`POST /launch-ai-agents`**: Spawns both agents for a room
- **`POST /ai-agents/stop`**: Stops both agents for a room
- **`GET /ai-agents/status`**: Shows status of all agents
- **`POST /participant-token`**: Generates tokens for human participants

## 🔧 Local Development

### Running Individual Agents

```bash
# Terminal 1: Aristotle (Moderator)
cd sage-ai-backend
export ROOM_NAME="test-room"
export DEBATE_TOPIC="AI Ethics"
python debate_moderator_agent.py start

# Terminal 2: Socrates (Philosopher)
cd sage-ai-backend  
export ROOM_NAME="test-room"
export DEBATE_TOPIC="AI Ethics"
python debate_philosopher_agent.py start
```

### Running Web Service

```bash
# Terminal 3: Web API
cd sage-ai-backend
python -m uvicorn app:app --reload --port 8000
```

## 📊 Monitoring

### Agent Status

Check agent health via:

```bash
curl https://your-backend-url.onrender.com/ai-agents/status
```

Response shows both agents:

```json
{
  "status": "success",
  "summary": {
    "total_rooms": 1,
    "total_agents": 2,
    "running_agents": 2,
    "connected_agents": 2
  },
  "rooms": {
    "debate-ai-ethics": {
      "agents": {
        "aristotle": {
          "process_id": 12345,
          "role": "logical moderator with reason + structure",
          "running": true
        },
        "socrates": {
          "process_id": 12346,
          "role": "inquisitive challenger with questioning + truth-seeking", 
          "running": true
        }
      }
    }
  }
}
```

## 🔄 Alternative Deployment Options

### Option 2: Separate Web Services (Alternative)

If you prefer separate URLs for each agent:

1. **Service 1**: `sage-aristotle` → `debate_moderator_agent.py`
2. **Service 2**: `sage-socrates` → `debate_philosopher_agent.py`
3. **Service 3**: `sage-api` → `app.py` (token generation only)

### Option 3: Docker Deployment

```dockerfile
# For background workers
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "debate_moderator_agent.py", "start"]
```

## ⚠️ Important Notes

### Existing Functionality Preserved

- ✅ All existing endpoints work unchanged
- ✅ Human participants can still join rooms
- ✅ Memory/Supabase integration maintained
- ✅ Frontend compatibility preserved

### Cost Considerations

- **3 services** on Render (1 web + 2 background workers)
- **Starter plan** sufficient for each service
- **Agents run continuously** when deployed as background workers

### Troubleshooting

1. **Agents not joining room**: Check LiveKit credentials in environment variables
2. **OpenAI timeouts**: Verify API key and network connectivity
3. **Memory errors**: Ensure Supabase credentials are correct
4. **Process crashes**: Check logs in Render dashboard

## 🎉 Ready to Deploy!

Your dual-agent architecture is now ready for production deployment. The system will automatically spawn both Aristotle and Socrates to join any debate room and engage in philosophical discussions. 