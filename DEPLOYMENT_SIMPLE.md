# Simplified Deployment Guide - Context7 MCP Implementation

## 🎯 **The Correct Way (150 lines vs 1500+ lines)**

Based on Context7 MCP analysis, we've replaced our complex audio bridge system with the **official LiveKit Agents pattern**.

---

## 📋 **What Changed**

### ❌ **Old Complex Approach**
- 8+ files, 1500+ lines of code
- Custom audio bridge system
- Manual room management  
- Complex WebRTC ↔ AI agent audio processing
- 15+ dependencies

### ✅ **New Simple Approach**  
- 1 file, 150 lines of code
- Standard LiveKit Agents pattern
- OpenAI Realtime API (automatic audio processing)
- Proper multi-agent personality management
- 2 dependencies

---

## 🚀 **Local Development**

### **1. Install Dependencies**
```bash
cd sage-ai-backend
pip install -r simple_agent_requirements.txt
```

### **2. Set Environment Variables**
```bash
# Required for LiveKit Agents
export LIVEKIT_API_KEY="your_livekit_api_key"
export LIVEKIT_API_SECRET="your_livekit_secret"  
export LIVEKIT_URL="wss://your-livekit-server.com"
export OPENAI_API_KEY="your_openai_key"

# Optional: Customize debate
export ROOM_NAME="my-debate-room"
export DEBATE_TOPIC="The future of AI ethics"
```

### **3. Run Agent (Development)**
```bash
python multi_personality_agent.py dev
```

### **4. Run Agent (Production)**
```bash
python multi_personality_agent.py start
```

---

## 🌐 **Production Deployment (Render)**

### **Environment Variables in Render**
Set these in your Render service environment:
```
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret  
LIVEKIT_URL=wss://your-livekit-server.com
OPENAI_API_KEY=your_openai_key
DEBATE_TOPIC=The impact of AI on society
```

### **Update render.yaml**
```yaml
services:
  - type: worker
    name: sage-voice-agent
    env: python
    buildCommand: pip install -r simple_agent_requirements.txt
    startCommand: python multi_personality_agent.py start
    envVars:
      - key: LIVEKIT_API_KEY
        sync: false
      - key: LIVEKIT_API_SECRET  
        sync: false
      - key: LIVEKIT_URL
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

---

## 🎭 **How It Works**

### **Multi-Personality System**
- **Solon**: Moderator (starts first, guides discussion)
- **Socrates**: Questioner (asks probing questions)  
- **Aristotle**: Analyst (provides logic and evidence)
- **Buddha**: Peacekeeper (promotes harmony)
- **Hermes**: Synthesizer (connects viewpoints)

### **Voice Integration**
- OpenAI Realtime API handles all voice processing automatically
- Each personality has a distinct voice (echo, ash, nova, onyx, shimmer)
- Turn detection manages conversation flow
- No manual audio bridges needed!

### **Frontend Integration**
- Frontend connects to standard LiveKit room
- AI agents appear as regular room participants  
- Voice flows through LiveKit WebRTC automatically
- Remove all custom audio bridge API calls

---

## 🔧 **Testing**

### **Local Test**
```bash
# Terminal 1: Start agent
python multi_personality_agent.py dev

# Terminal 2: Test with console mode
python multi_personality_agent.py console
```

### **Verify Environment**
```bash
python -c "
import os
required = ['LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'LIVEKIT_URL', 'OPENAI_API_KEY']
missing = [v for v in required if not os.getenv(v)]
print('✅ All set!' if not missing else f'❌ Missing: {missing}')
"
```

---

## 📊 **Performance Comparison**

| Metric | Old Approach | New Approach |
|--------|-------------|--------------|
| **Code Lines** | 1500+ | 150 |
| **Files** | 8+ | 1 |
| **Dependencies** | 15+ | 2 |
| **Complexity** | Very High | Very Low |
| **Maintenance** | Difficult | Easy |
| **Performance** | Complex | Optimized |

---

## 🎯 **Next Steps**

1. **Deploy new agent** to Render using simplified approach
2. **Update frontend** to use standard LiveKit room connections
3. **Remove legacy** audio bridge endpoints from app.py
4. **Test voice interaction** with all 5 AI personalities

The Context7 MCP analysis revealed we were **massively over-engineering** the solution. LiveKit Agents provides everything we built manually! 