# Lovable Quick Start: Voice Debate Implementation

## 🚀 Phase 1: Dependencies (5 minutes)

**Lovable Prompt:**
```
Add the following dependencies to package.json: livekit-client version 2.1.0, @livekit/components-react version 2.1.0, and lucide-react version 0.263.1 for voice functionality and icons
```

## 🎯 Phase 2: Create Hook (10 minutes)

**Lovable Prompt:**
```
Create a new file src/hooks/useVoiceAPI.ts that contains a React hook for integrating with our Sage AI backend Chat API. The hook should have methods for sendMessage (POST to /api/chat/message) and getConversationMemory (GET to /api/chat/memory/{roomId}). Use fetch API with proper error handling and loading states. The backend URL should default to https://sage-ai-backend-l0en.onrender.com but read from VITE_BACKEND_API_URL environment variable.
```

## 🎨 Phase 3: Audio Indicator Component (10 minutes)

**Lovable Prompt:**
```
Create src/components/AudioLevelIndicator.tsx - a React component that displays a horizontal progress bar showing audio input level from 0-1. When isActive is true, show a green dot and green progress bar. When false, show gray. Include proper TypeScript interfaces. Use Tailwind CSS for styling with rounded corners and smooth transitions.
```

## 🎛️ Phase 4: Voice Controls Component (15 minutes)

**Lovable Prompt:**
```
Create src/components/VoiceControls.tsx - a React component that renders voice control UI in a Card layout. Include mute/unmute button (red when muted), volume toggle button, audio level indicator, connection status badge, and current speaker display. Use lucide-react icons: Mic, MicOff, Volume2, VolumeX. Component should accept props for all state and callback functions. Use shadcn/ui Card, Button, and Badge components.
```

## 💬 Phase 5: Conversation Feed Component (15 minutes)

**Lovable Prompt:**
```
Create src/components/ConversationFeed.tsx - a React component that displays a scrollable conversation history in a Card layout. Show user transcript in blue-themed messages and AI agent responses in purple-themed messages with agent name and role badges. Include empty states for not connected and no messages. Use shadcn/ui Card, Badge components and proper TypeScript interfaces. Max height 96 (24rem) with overflow scroll.
```

## 🎤 Phase 6: Main Voice Room Component (25 minutes)

**Lovable Prompt:**
```
Create src/components/VoiceDebateRoom.tsx - the main voice debate room component. This should:
1. Use livekit-client to connect to LiveKit rooms
2. Handle microphone capture with LocalAudioTrack
3. Manage room state (connected, connecting, participants)
4. Include audio level monitoring with Web Audio API
5. Integrate with useVoiceAPI hook for chat functionality
6. Use VoiceControls and ConversationFeed components
7. Handle LiveKit events (participant joined/left, tracks)
8. Full-screen layout with header showing room name and controls
9. Proper cleanup on unmount
10. TypeScript interfaces for all props and state

The component should connect to VITE_LIVEKIT_URL (default wss://sage-ai-backend-l0en.onrender.com) and handle all voice room functionality.
```

## 🧭 Phase 7: Add Navigation (10 minutes)

**Lovable Prompt:**
```
Add a new route /voice-debate/:roomName to the app routing that renders the VoiceDebateRoom component. The component should receive roomName from URL params and handle navigation back to home on leave. Also add a prominent "Start Voice Debate" button to the homepage with a microphone icon that navigates to /voice-debate/general-discussion.
```

## ⚙️ Phase 8: Environment Configuration (5 minutes)

**Lovable Prompt:**
```
Add these environment variables to the project configuration:
- VITE_BACKEND_API_URL with value https://sage-ai-backend-l0en.onrender.com
- VITE_LIVEKIT_URL with value wss://sage-ai-backend-l0en.onrender.com

These should be accessible via import.meta.env in the React components.
```

## 🎨 Phase 9: UI Polish (10 minutes)

**Lovable Prompt:**
```
Update the voice debate room layout to use a beautiful gradient background (purple-50 to blue-50), ensure all components are responsive for mobile devices, add proper loading states and error boundaries around voice components, and include accessibility attributes (ARIA labels) for screen readers on all interactive elements.
```

## 🧪 Phase 10: Testing Integration (10 minutes)

**Lovable Prompt:**
```
Add error handling and user feedback throughout the voice components. Include toast notifications for connection status, microphone errors, and AI agent responses. Ensure graceful degradation when microphone access is denied or LiveKit connection fails. Add loading spinners and connection status indicators.
```

---

## 📱 Total Implementation Time: ~2 hours

## 🎯 Key Features Delivered:
- ✅ **Professional Voice Interface** - Complete microphone controls with visual feedback
- ✅ **LiveKit Integration** - Real-time audio streaming and room management  
- ✅ **AI Chat Integration** - Direct connection to Sage AI backend API
- ✅ **Responsive Design** - Mobile-friendly voice controls and layout
- ✅ **Error Handling** - Comprehensive error boundaries and user feedback
- ✅ **Accessibility** - Screen reader compatible voice controls

## 🔗 Backend Integration:
The frontend will connect to:
- **Chat API**: `https://sage-ai-backend-l0en.onrender.com/api/chat/message`
- **Memory API**: `https://sage-ai-backend-l0en.onrender.com/api/chat/memory/{room_id}`
- **LiveKit**: `wss://sage-ai-backend-l0en.onrender.com` (WebSocket)

## 🎉 Result:
A complete voice debate system where users can speak naturally and receive intelligent responses from Sage AI agents (Aristotle, Socrates, Buddha, Hermes, Solon) with professional audio quality and real-time conversation flow! 