# Audio Bridge Frontend Integration Guide

This guide explains how to integrate the audio bridge with your existing WebRTC system on the frontend.

## Overview

The audio bridge allows WebRTC audio data from human participants to be forwarded to AI agents in LiveKit rooms. This enables real-time voice interaction between humans and AI agents.

## Backend Components

### 1. Audio Bridge Endpoint: `/audio-bridge`

**Method**: POST
**Content-Type**: application/json

**Request Body**:
```json
{
  "room_name": "string",
  "audio_data": "base64-encoded-float32array",
  "participant_name": "string",
  "timestamp": 1234567890.123
}
```

**Response**:
```json
{
  "status": "success|warning|error",
  "message": "Description of result",
  "room_name": "string",
  "participant_name": "string", 
  "audio_samples": 16000,
  "audio_duration_seconds": 1.0,
  "timestamp": 1234567890.123,
  "audio_processed": true
}
```

### 2. Audio Bridge Integration Module

- Handles WebRTC → LiveKit audio conversion
- Manages audio streaming to AI agents
- Provides real-time audio forwarding capabilities

## Frontend Integration

### Step 1: Modify `useWebRTCRoom` Hook

Add audio bridge functionality to your existing `useWebRTCRoom` hook:

```typescript
// In src/hooks/useWebRTCRoom.ts

const BACKEND_API_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000' 
  : 'https://sage-ai-backend-l0en.onrender.com';

// Add this function to send audio to bridge
const sendAudioToBridge = useCallback(async (
  audioData: Float32Array, 
  roomName: string, 
  participantName: string
) => {
  try {
    // Convert Float32Array to base64
    const buffer = new ArrayBuffer(audioData.length * 4);
    const view = new Float32Array(buffer);
    view.set(audioData);
    
    const uint8Array = new Uint8Array(buffer);
    const base64Audio = btoa(String.fromCharCode(...uint8Array));
    
    // Send to audio bridge
    const response = await fetch(`${BACKEND_API_URL}/audio-bridge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        room_name: roomName,
        audio_data: base64Audio,
        participant_name: participantName,
        timestamp: Date.now() / 1000
      })
    });
    
    if (!response.ok) {
      throw new Error(`Audio bridge failed: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('Audio bridged to AI agents:', result);
    
  } catch (error) {
    console.error('Failed to bridge audio to AI agents:', error);
  }
}, []);
```

### Step 2: Update Audio Processing

Modify your existing audio processing to also send data to the bridge:

```typescript
// In your audio processing callback
const processAudioData = useCallback((audioData: Float32Array) => {
  // Existing audio processing logic
  if (onAudioData) {
    onAudioData(audioData);
  }
  
  // NEW: Also send to audio bridge for AI agents
  if (roomName && participantName) {
    sendAudioToBridge(audioData, roomName, participantName);
  }
}, [onAudioData, sendAudioToBridge, roomName, participantName]);
```

### Step 3: Update Component Usage

Ensure your components pass the required parameters:

```typescript
// In DebateRoom.tsx or similar components
const { 
  // ... existing props
} = useWebRTCRoom({
  roomName: currentRoom,
  participantName: user?.user_metadata?.name || 'Anonymous',
  onAudioData: handleAudioData, // Your existing handler
  // ... other props
});
```

## Audio Data Flow

```
Human Speaker (WebRTC) 
    ↓ 
  Audio Data (Float32Array)
    ↓
  Frontend Processing 
    ↓
  Base64 Encoding
    ↓
  POST /audio-bridge
    ↓
  Backend Audio Bridge
    ↓
  LiveKit Room
    ↓
  AI Agents (Voice Processing)
```

## Testing the Integration

### 1. Start the Backend

```bash
cd sage-ai-backend
python app.py
```

### 2. Test Audio Bridge Endpoint

```bash
cd sage-ai-backend  
python test_audio_bridge.py
```

### 3. Launch AI Agents

Use the frontend to:
1. Create a room
2. Launch AI agents via `/launch-ai-agents`
3. Start speaking - audio should be forwarded to AI agents

### 4. Monitor Logs

Check backend logs for:
- `🎤 Audio bridge called for room: ...`
- `📊 Audio bridge result: success - ...`
- `🎵 Audio bridge connected to room: ...`

## Configuration

### Environment Variables

Ensure these are set in your backend `.env`:

```
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
```

### CORS Configuration

The backend is already configured to allow requests from your frontend domain.

## Troubleshooting

### Audio Bridge Not Available
- Check that numpy is installed: `pip install numpy>=1.21.0`
- Verify LiveKit credentials are configured
- Check backend logs for initialization errors

### Audio Data Not Reaching AI Agents
- Verify AI agents are running in the target room
- Check audio data encoding is correct (Float32Array → base64)
- Monitor backend logs for processing errors

### Frontend Integration Issues
- Ensure `useWebRTCRoom` hook is properly modified
- Check console for JavaScript errors
- Verify API endpoint URLs are correct

## Next Steps

1. **Frontend Implementation**: Apply the above changes to your `useWebRTCRoom` hook
2. **Testing**: Use the provided test script to verify functionality
3. **Monitoring**: Add logging to track audio bridge usage
4. **Optimization**: Consider audio buffering and batching for performance

This integration preserves your existing WebRTC system while adding AI agent voice capabilities with minimal changes. 