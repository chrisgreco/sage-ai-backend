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