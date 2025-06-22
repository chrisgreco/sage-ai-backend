# Transcription Feature (Optional)

## Overview

The Sage AI debate agents include **optional real-time transcription** capabilities that capture and forward speech from all participants to the frontend clients. The system gracefully degrades when transcription components are not available.

## How It Works

### 🎯 **Multi-Speaker Transcription (When Available)**
- **Socrates agent** captures audio from all participants (Aristotle focuses on moderation)
- **Deepgram STT** converts speech to text in real-time (if available)
- **Transcription segments** are forwarded to frontend clients
- **Each speaker is identified** by their participant identity
- **Single transcription source** prevents duplicate segments
- **Graceful fallback** when transcription components unavailable

### 🔧 **Technical Implementation**
- Uses conditional imports for `STTSegmentsForwarder` and `deepgram.STT`
- Integrates with existing audio track subscription system
- Forwards transcriptions as data messages to the room
- Compatible with existing agent conversation logic
- **Fails gracefully** if transcription dependencies missing

## Deployment Compatibility

### ✅ **Production Ready**
- **Works without transcription** - agents function normally
- **Optional dependency** - deepgram not required for basic operation
- **Error handling** - graceful degradation when components unavailable
- **Conditional setup** - only enables transcription when possible

### 🚫 **What Happens Without Transcription**
- Agents still function normally for voice debate
- Audio coordination and conversation flow maintained
- Knowledge retrieval and AI responses work perfectly
- Only real-time text display is unavailable

## Frontend Integration

### 📡 **Receiving Transcriptions (When Available)**
Frontend clients can listen for transcription events:

```typescript
// Listen for transcription segments
room.on('transcription', (transcription) => {
  console.log(`${transcription.participant}: ${transcription.text}`);
  // Update UI with real-time transcription
});
```

### 🎨 **UI Implementation**
- **Transcription Panel**: Show real-time text as participants speak
- **Speaker Labels**: Display who is speaking (User, Aristotle, Socrates)
- **Conversation Log**: Maintain history of what was said
- **Optional Display**: Hide transcription UI when not available

### ✅ **What's Included (When Available)**
- **Real-time transcription** of all participants
- **Speaker identification** (users, Aristotle, Socrates)
- **Automatic forwarding** to frontend clients
- **Integration with existing debate logic**
- **Single-agent transcription** (Socrates only, prevents duplicates)
- **Graceful degradation** when unavailable

## Configuration

### 📋 **Environment Variables (Optional)**
```bash
# Only needed if you want transcription
DEEPGRAM_API_KEY=your_deepgram_key_here
```

### 🔧 **Installation (Optional)**
```bash
# Add deepgram to dependencies only if you want transcription
pip install livekit-agents[deepgram]
```

## Status Monitoring

The system logs transcription availability:
- `✅ Transcription components available` - Full transcription enabled
- `⚠️ Transcription not available` - System continues without transcription
- `📝 Transcription not available - continuing without it` - Normal operation

## Benefits

### ✅ **With Transcription**
- Real-time text display for accessibility
- Conversation logging and review
- Better user experience for text-based analysis
- Enhanced debate documentation

### ✅ **Without Transcription**
- Full voice AI debate functionality
- Agent coordination and responses
- Knowledge-enhanced conversations
- All core features operational

The transcription feature enhances the experience when available but never blocks core functionality. 