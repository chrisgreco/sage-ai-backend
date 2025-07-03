# Lovable Frontend Implementation Guide
## Voice Debate Integration with Sage AI

### Overview
This guide provides step-by-step instructions for implementing voice debate functionality in the Lovable frontend, integrating with the Sage AI backend's improved chat API and LiveKit voice capabilities.

---

## 📋 Implementation Checklist

### Phase 1: Dependencies & Setup
- [ ] Install LiveKit React SDK
- [ ] Install additional UI dependencies
- [ ] Update environment variables
- [ ] Create new route for voice debates

### Phase 2: Core Components
- [ ] Create VoiceDebateRoom component
- [ ] Create VoiceControls component
- [ ] Create ConversationFeed component
- [ ] Create AudioLevelIndicator component

### Phase 3: Integration
- [ ] Connect to backend Chat API
- [ ] Implement LiveKit room management
- [ ] Add voice debate navigation
- [ ] Test end-to-end functionality

---

## 🚀 Step-by-Step Implementation

### Step 1: Install Dependencies

Add these packages to your `package.json`:

```json
{
  "dependencies": {
    "livekit-client": "^2.1.0",
    "@livekit/components-react": "^2.1.0",
    "lucide-react": "^0.263.1"
  }
}
```

**Lovable Command:**
```
Add the following dependencies: livekit-client, @livekit/components-react, and lucide-react for voice functionality and icons
```

### Step 2: Environment Variables

Update your environment configuration:

```env
# For development (localhost testing)
VITE_BACKEND_API_URL=http://localhost:8001
VITE_LIVEKIT_URL=ws://localhost:7880

# For production
VITE_BACKEND_API_URL=https://sage-ai-backend-l0en.onrender.com
VITE_LIVEKIT_URL=wss://sage-ai-backend-l0en.onrender.com
```

### Step 3: Create Voice API Hook

Create `src/hooks/useVoiceAPI.ts`:

```typescript
import { useState, useCallback } from 'react';

interface ChatMessage {
  message: string;
  room_id: string;
}

interface ChatResponse {
  response: {
    agent_name: string;
    agent_role: string;
    message: string;
  };
  conversation_length: number;
}

export function useVoiceAPI() {
  const [isLoading, setIsLoading] = useState(false);
  const backendUrl = import.meta.env.VITE_BACKEND_API_URL || 'https://sage-ai-backend-l0en.onrender.com';

  const sendMessage = useCallback(async (message: string, roomId: string): Promise<ChatResponse> => {
    setIsLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, room_id: roomId }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Voice API error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [backendUrl]);

  const getConversationMemory = useCallback(async (roomId: string) => {
    try {
      const response = await fetch(`${backendUrl}/api/chat/memory/${roomId}`);
      return await response.json();
    } catch (error) {
      console.error('Memory API error:', error);
      throw error;
    }
  }, [backendUrl]);

  return {
    sendMessage,
    getConversationMemory,
    isLoading
  };
}
```

### Step 4: Create Audio Level Indicator Component

Create `src/components/AudioLevelIndicator.tsx`:

```typescript
interface AudioLevelIndicatorProps {
  level: number; // 0-1
  isActive: boolean;
}

export function AudioLevelIndicator({ level, isActive }: AudioLevelIndicatorProps) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-700">
        Audio Level {isActive && <span className="text-green-600">●</span>}
      </label>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div 
          className={`h-3 rounded-full transition-all duration-150 ${
            isActive ? 'bg-green-500' : 'bg-gray-400'
          }`}
          style={{ width: `${level * 100}%` }}
        />
      </div>
    </div>
  );
}
```

### Step 5: Create Voice Controls Component

Create `src/components/VoiceControls.tsx`:

```typescript
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { AudioLevelIndicator } from './AudioLevelIndicator';

interface VoiceControlsProps {
  isMuted: boolean;
  isVolumeOn: boolean;
  audioLevel: number;
  isListening: boolean;
  isConnected: boolean;
  currentSpeaker: string | null;
  onToggleMute: () => void;
  onToggleVolume: () => void;
}

export function VoiceControls({
  isMuted,
  isVolumeOn,
  audioLevel,
  isListening,
  isConnected,
  currentSpeaker,
  onToggleMute,
  onToggleVolume
}: VoiceControlsProps) {
  return (
    <Card className="w-80">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mic className="w-5 h-5" />
          Voice Controls
        </CardTitle>
        <CardDescription>
          Manage your microphone and audio settings
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Microphone Control */}
        <div className="flex items-center gap-3">
          <Button
            onClick={onToggleMute}
            variant={isMuted ? "destructive" : "default"}
            size="lg"
            className="flex-1"
            disabled={!isConnected}
          >
            {isMuted ? <MicOff className="w-5 h-5 mr-2" /> : <Mic className="w-5 h-5 mr-2" />}
            {isMuted ? "Unmute" : "Mute"}
          </Button>
          
          <Button
            onClick={onToggleVolume}
            variant={isVolumeOn ? "default" : "secondary"}
            size="lg"
          >
            {isVolumeOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
          </Button>
        </div>

        {/* Audio Level Indicator */}
        <AudioLevelIndicator level={audioLevel} isActive={isListening} />

        {/* Status Indicators */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Listening:</span>
            <Badge variant={isListening ? "default" : "secondary"}>
              {isListening ? "Active" : "Inactive"}
            </Badge>
          </div>
          
          {currentSpeaker && (
            <div className="flex items-center justify-between text-sm">
              <span>Speaking:</span>
              <Badge variant="outline">{currentSpeaker}</Badge>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Step 6: Create Conversation Feed Component

Create `src/components/ConversationFeed.tsx`:

```typescript
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MessageCircle } from 'lucide-react';

interface AgentResponse {
  agent_name: string;
  agent_role: string;
  message: string;
  timestamp: number;
}

interface ConversationFeedProps {
  lastTranscript: string;
  agentResponses: AgentResponse[];
  isConnected: boolean;
}

export function ConversationFeed({ 
  lastTranscript, 
  agentResponses, 
  isConnected 
}: ConversationFeedProps) {
  return (
    <Card className="flex-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5" />
          Live Conversation
        </CardTitle>
        <CardDescription>
          Real-time voice conversation with Sage AI agents
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          
          {/* Last Transcript */}
          {lastTranscript && (
            <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
              <div className="text-sm font-medium text-blue-800">You said:</div>
              <div className="text-blue-700">{lastTranscript}</div>
            </div>
          )}
          
          {/* Agent Responses */}
          {agentResponses.map((response, index) => (
            <div key={index} className="bg-purple-50 p-3 rounded-lg border-l-4 border-purple-400">
              <div className="flex items-center gap-2 mb-1">
                <div className="text-sm font-medium text-purple-800">
                  {response.agent_name}
                </div>
                <Badge variant="outline" className="text-xs">
                  {response.agent_role}
                </Badge>
              </div>
              <div className="text-purple-700">{response.message}</div>
            </div>
          ))}
          
          {/* Connection Status */}
          {!isConnected && (
            <div className="text-center py-8 text-gray-500">
              Connecting to voice room...
            </div>
          )}
          
          {isConnected && agentResponses.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              Start speaking to begin your debate with the Sage AI agents
            </div>
          )}
          
        </div>
      </CardContent>
    </Card>
  );
}
```

### Step 7: Main Voice Debate Room Component

This is the core component that ties everything together. It handles LiveKit connections, audio processing, and integrates with the backend Chat API.

### Step 8: Add Navigation Route

Update your routing to include the voice debate room. Add a new route for `/voice-debate/:roomName` that renders the VoiceDebateRoom component.

### Step 9: Add Voice Debate Button to Homepage

Add a prominent "Start Voice Debate" button to your homepage that navigates users to the voice debate experience.

---

## 🎯 Key Integration Points

### Backend API Integration
- **Chat API**: `POST /api/chat/message` for sending voice transcripts
- **Memory API**: `GET /api/chat/memory/{room_id}` for conversation history
- **Health Check**: `GET /health` for API status monitoring

### LiveKit Integration
- **Audio Capture**: WebRTC microphone access with noise suppression
- **Real-time Streaming**: Low-latency audio transmission
- **Voice Activity Detection**: Automatic speaking detection
- **Echo Cancellation**: Professional audio quality

### UI/UX Features
- **Visual Audio Feedback**: Real-time audio level indicators
- **Connection Status**: Clear connection state indicators
- **Responsive Design**: Mobile-friendly voice controls
- **Accessibility**: Screen reader compatible controls

---

## 📱 Mobile Optimization

### iOS Considerations
- Handle iOS audio context requirements
- Test Safari microphone permissions
- Ensure audio playback works correctly

### Android Considerations
- Test Chrome autoplay policies
- Verify microphone access flow
- Handle device-specific audio issues

---

## 🔧 Configuration

### Environment Variables (Production)
```env
VITE_BACKEND_API_URL=https://sage-ai-backend-l0en.onrender.com
VITE_LIVEKIT_URL=wss://sage-ai-backend-l0en.onrender.com
```

### Environment Variables (Development)
```env
VITE_BACKEND_API_URL=http://localhost:8001
VITE_LIVEKIT_URL=ws://localhost:7880
```

---

## 🧪 Testing Checklist

- [ ] Microphone access permissions
- [ ] Audio level visualization
- [ ] Mute/unmute functionality
- [ ] Volume controls
- [ ] LiveKit connection status
- [ ] Chat API integration
- [ ] Agent response display
- [ ] Mobile responsiveness
- [ ] Error handling
- [ ] Loading states

---

## 🚀 Deployment Notes

1. **Dependencies**: Install all required packages
2. **Environment**: Configure production URLs
3. **Permissions**: Test microphone access flow
4. **Error Handling**: Implement comprehensive error boundaries
5. **Performance**: Monitor for memory leaks in audio processing

This implementation provides a complete voice debate system that integrates seamlessly with your existing Sage AI backend and provides a professional voice conversation experience!

# Lovable Frontend Integration - Backend Implementation Guide

## 🎯 Overview

This document outlines the comprehensive backend fixes implemented to ensure full compatibility with the Lovable frontend's LiveKit best practices implementation. The frontend now uses official `@livekit/components-react` with proper agent state management, and our backend has been updated to match these expectations.

## ✅ Key Issues Resolved

### 1. **Agent Identity & Recognition**
**Problem**: Frontend expects agents with specific identities containing "Socrates", "Aristotle", or "Buddha"
**Solution**: 
- Updated agent token generation to use persona name directly as identity
- Agent identity: `"Socrates"`, `"Aristotle"`, `"Buddha"` (not `"sage-ai-socrates"`)
- Agents automatically get `ParticipantKind.AGENT` from LiveKit agents framework

### 2. **Agent State Management** 
**Problem**: Frontend expects agents to expose state via `lk.agent.state` participant attribute
**Solution**: Added comprehensive state management system:
- **States**: `initializing`, `listening`, `thinking`, `speaking`
- **State Broadcasting**: Updates sent via both participant metadata and data messages
- **Automatic Transitions**: State changes based on agent workflow

### 3. **Agent Workflow Implementation**
**Problem**: Frontend expects specific agent workflow with proper state transitions
**Solution**: Implemented complete workflow:
```
User speaks → Agent receives audio → Agent state: thinking
→ Agent processes content → Agent state: speaking  
→ Agent publishes response → Agent state: listening
```

### 4. **Enhanced Audio Pipeline**
**Problem**: Basic audio setup not meeting production standards
**Solution**: Implemented full LiveKit voice AI stack:
- **Turn Detection**: `MultilingualModel()` for natural conversation flow
- **VAD**: `silero.VAD.load()` for better interruption handling
- **Noise Cancellation**: `noise_cancellation.BVC()` for cleaner audio
- **Premium TTS**: Cartesia support with OpenAI fallback

### 5. **Agent Startup & Connection**
**Problem**: Agent not connecting to same LiveKit server or joining rooms correctly
**Solution**: Fixed startup process:
- Corrected agent command: `python debate_moderator_agent.py` (removed "start" arg)
- Proper environment variable passing
- Enhanced error handling and logging

## 🔧 Technical Implementation Details

### Agent State Management Class
```python
class AgentState:
    INITIALIZING = "initializing"  # Agent starting up
    LISTENING = "listening"        # Agent listening to user speech
    THINKING = "thinking"          # Agent processing (tool use, API calls)
    SPEAKING = "speaking"          # Agent generating/playing response
```

### State Broadcasting Method
```python
async def set_agent_state(self, state: str):
    # Update participant metadata
    metadata = {
        "agent_state": state,
        "persona": self.persona,
        "topic": self.topic,
        "participant_type": "agent"
    }
    await self.room.local_participant.update_metadata(json.dumps(metadata))
    
    # Send immediate data message for frontend feedback
    state_message = {
        "type": "agent_state_change",
        "state": state,
        "persona": self.persona,
        "timestamp": datetime.utcnow().isoformat()
    }
    await self.room.local_participant.publish_data(
        data=json.dumps(state_message).encode('utf-8'),
        reliable=True
    )
```

### Enhanced Session Configuration
```python
session = AgentSession(
    vad=silero.VAD.load(),                    # Voice Activity Detection
    stt=deepgram.STT(model="nova-2"),         # Speech-to-Text
    llm=llm,                                  # Perplexity LLM
    tts=tts,                                  # Cartesia/OpenAI TTS
    turn_detection=MultilingualModel(),       # Turn detection
)

# Session with noise cancellation
await session.start(
    agent=agent,
    room=ctx.room,
    room_input_options=RoomInputOptions(
        noise_cancellation=noise_cancellation.BVC(),
    ),
)
```

### Agent Identity Generation
```python
# Frontend expects exact persona names as identity
agent_identity = f"{persona}"  # "Socrates", "Aristotle", "Buddha"
agent_token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
    .with_identity(agent_identity) \
    .with_name(f"Sage AI - {persona}") \
    .with_metadata({
        "topic": topic,
        "persona": persona,
        "participant_type": "agent",
        "agent_state": "initializing"
    })
```

## 🎭 AI Personality Implementation

All three AI moderators are fully implemented with distinct approaches:

### **Socrates** 
- Uses Socratic method to challenge assumptions
- Guides discovery through questioning
- State transitions: `listening` → `thinking` (analyzing assumptions) → `speaking` (asking questions)

### **Aristotle**
- Focuses on logical reasoning and fact-checking
- Structured argumentation approach
- State transitions: `listening` → `thinking` (fact-checking) → `speaking` (providing analysis)

### **Buddha**
- Emphasizes mindful communication and de-escalation
- Seeks mutual understanding
- State transitions: `listening` → `thinking` (considering emotions) → `speaking` (mediating)

## 🔄 Agent Workflow States

### 1. **Initializing** (`initializing`)
- Agent starting up and connecting to room
- Loading models and establishing session
- Setting up memory and context

### 2. **Listening** (`listening`) 
- Agent actively listening to user speech
- Waiting for user input or conversation
- Default state when not processing

### 3. **Thinking** (`thinking`)
- Agent processing user input
- Performing tool calls (moderation, fact-checking)
- Analyzing content based on persona

### 4. **Speaking** (`speaking`)
- Agent generating response
- Publishing audio back to room
- Delivering moderation or guidance

## 📡 Backend Startup Verification

To verify the backend is working correctly:

```bash
# Check agent process
python debate_moderator_agent.py

# Should show:
# ✅ Connected to LiveKit room
# 🚀 Agent session started successfully with enhanced audio processing
# 💬 Contextual greeting sent
# Agent state changed to: listening
```

### Expected Agent Behavior:
1. **Connects** to same LiveKit server URL as frontend tokens
2. **Uses correct API keys** (LiveKit, OpenAI, Perplexity, Cartesia)
3. **Joins rooms** when they're created by frontend
4. **Shows up as agent participants** with proper identity
5. **Implements all three AI personalities** with distinct behaviors
6. **Broadcasts state changes** for frontend visualization
7. **Publishes audio responses** back to room participants

## 🔍 Debugging Checklist

If agents aren't working:

### ✅ **Environment Variables**
- `LIVEKIT_URL` matches frontend configuration
- `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are valid
- `OPENAI_API_KEY` for TTS
- `PERPLEXITY_API_KEY` for LLM
- `CARTESIA_API_KEY` for premium TTS (optional)
- `DEEPGRAM_API_KEY` for STT

### ✅ **Agent Identity**
- Agent joins with identity: `"Socrates"`, `"Aristotle"`, or `"Buddha"`
- Participant metadata includes `"participant_type": "agent"`
- Agent state is being broadcast correctly

### ✅ **Audio Pipeline**
- Agent publishes audio tracks when speaking
- Agent subscribes to user microphone tracks
- VAD and turn detection are working
- TTS is generating audio responses

### ✅ **State Management**
- Agent states transition: `initializing` → `listening` → `thinking` → `speaking` → `listening`
- Frontend receives state updates via data messages
- Participant metadata reflects current agent state

## 🚀 Next Steps

The backend is now fully compatible with the Lovable frontend implementation. The system provides:

1. **Proper Agent Recognition**: Agents appear as `ParticipantKind.AGENT` with correct identities
2. **State Visualization**: Frontend can display agent states with `BarVisualizer` and controls
3. **Natural Conversation**: Turn detection and VAD enable smooth interruptions
4. **Enhanced Audio Quality**: Noise cancellation and premium TTS for better experience
5. **Memory Persistence**: Supabase integration maintains conversation context
6. **Multi-Persona Support**: Three distinct AI moderators with unique approaches

The frontend and backend are now in perfect sync, providing a professional-grade voice AI debate moderation experience.

# Sage AI LiveKit Integration - Implementation Guide for Lovable Team

## 🚨 Critical Issue: LiveKit Configuration Mismatch

Based on the console logs, the frontend is trying to connect to `sage-2kpu4zly.livekit.cloud` while the backend is configured for a different LiveKit instance. This is causing all the connection failures.

## Console Errors Analysis

### 1. **401 Unauthorized Errors**
```
GET https://sage-2kpu4zly.livekit.cloud/settings/region 401 (Unauthorized)
GET https://sage-2kpu4zly.livekit.cloud/rtc/validate 401 (Unauthorized)
```

### 2. **WebSocket Connection Failures**
```
WebSocket connection to 'wss://sage-2kpu4zly.livekit.cloud/rtc2access_token=...' failed
```

### 3. **Invalid Token Errors**
```
Failed to connect to room: ConnectionError: could not establish signal connection: invalid token
```

## Root Cause

**Frontend and backend are using different LiveKit instances:**
- **Frontend**: Trying to connect to `sage-2kpu4zly.livekit.cloud` (appears to be a Lovable-created LiveKit Cloud instance)
- **Backend**: Configured for a different LiveKit server (likely the user's own instance)

## Required Fixes

### 1. **Coordinate LiveKit Configuration**

The frontend and backend MUST use the same LiveKit instance. You have two options:

#### Option A: Use Backend's LiveKit Instance (Recommended)
- Get the `LIVEKIT_URL` from the backend environment
- Update frontend to use the same URL
- Ensure frontend uses backend's `/participant-token` endpoint for token generation

#### Option B: Use Frontend's LiveKit Instance
- Update backend to use `sage-2kpu4zly.livekit.cloud`
- Provide backend with matching API credentials
- Update backend environment variables

### 2. **Token Generation Coordination**

The frontend should request tokens from the backend's `/participant-token` endpoint:

```typescript
// Frontend token request should go to backend
const tokenResponse = await fetch(`${BACKEND_URL}/participant-token`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    room_name: roomName,
    participant_name: participantName,
    participant_identity: participantIdentity
  })
});
```

### 3. **Agent Detection Logic**

The backend is configured to create agents with identities:
- `"Socrates"`
- `"Aristotle"` 
- `"Buddha"`

Your frontend should detect these agents by checking:
```typescript
// Check if participant is an agent
const isAgent = participant.kind === ParticipantKind.Agent || 
                participant.identity.match(/^(Socrates|Aristotle|Buddha)$/);
```

### 4. **Agent State Visualization**

The backend broadcasts agent states via participant metadata:
```typescript
// Listen for agent state changes
const metadata = JSON.parse(participant.metadata || '{}');
const agentState = metadata.agent_state; // "initializing", "listening", "thinking", "speaking"
const persona = metadata.persona; // "Socrates", "Aristotle", "Buddha"
```

### 5. **Environment Variables Alignment**

Ensure these environment variables match between frontend and backend:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

## Backend API Endpoints

The backend provides these endpoints for frontend integration:

### 1. **Health Check**
```
GET /health
```
Returns LiveKit configuration status.

### 2. **Participant Token**
```
POST /participant-token
Body: {
  "room_name": "string",
  "participant_name": "string", 
  "participant_identity": "string"
}
```
Returns LiveKit token for room access.

### 3. **Agent Management**
```
POST /start-agent
Body: {
  "room_name": "string",
  "topic": "string",
  "persona": "Socrates|Aristotle|Buddha"
}
```
Starts an AI moderator agent in the specified room.

## Agent Behavior

### Agent States
- `"initializing"` - Agent is starting up
- `"listening"` - Agent is listening to conversation
- `"thinking"` - Agent is processing/analyzing
- `"speaking"` - Agent is currently speaking

### Agent Capabilities
- **Moderation**: Guides discussion flow
- **Fact-checking**: Verifies claims with sources
- **Context awareness**: Maintains conversation memory
- **Persona-based responses**: Each agent has distinct personality

## Testing Steps

1. **Verify Backend Health**
   ```bash
   curl https://sage-ai-backend-l0en.onrender.com/health
   ```

2. **Test Token Generation**
   ```bash
   curl -X POST https://sage-ai-backend-l0en.onrender.com/participant-token \
     -H "Content-Type: application/json" \
     -d '{"room_name":"test-room","participant_name":"test-user","participant_identity":"user-123"}'
   ```

3. **Start Agent**
   ```bash
   curl -X POST https://sage-ai-backend-l0en.onrender.com/start-agent \
     -H "Content-Type: application/json" \
     -d '{"room_name":"test-room","topic":"AI Ethics","persona":"Socrates"}'
   ```

## Expected Frontend Behavior

Once properly configured, the frontend should:
1. Successfully connect to the same LiveKit instance as backend
2. Receive valid tokens from backend
3. Detect agents as `ParticipantKind.Agent`
4. Display agent states in real-time
5. Show agents with their persona names ("Socrates", "Aristotle", "Buddha")

## Debugging Tips

1. **Check Network Tab**: Verify all requests go to correct LiveKit URL
2. **Console Logs**: Look for successful token generation
3. **Participant Events**: Monitor agent join/leave events
4. **Metadata Updates**: Watch for agent state changes

## Next Steps

1. **Coordinate with backend team** to confirm LiveKit instance
2. **Update frontend LiveKit configuration** to match backend
3. **Test token generation** flow
4. **Verify agent detection** logic
5. **Test agent state visualization**

The backend is fully ready and compatible with LiveKit standards. The issue is purely a configuration coordination problem between frontend and backend. 