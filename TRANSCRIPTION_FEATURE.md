# Transcription Feature (Built-in)

## Overview

The Sage AI debate agents include **built-in real-time transcription** capabilities through LiveKit's native Agent framework. Transcription is handled automatically without requiring manual setup or additional dependencies.

## How It Works

### 🎯 **Automatic Transcription**
- **LiveKit Agent framework** automatically handles transcription for all participants
- **Built-in Speech-to-Text** processes audio from users and agents
- **Native transcription events** are sent to frontend clients automatically
- **No manual setup required** - works out of the box with Agent pattern
- **Speaker identification** included automatically

### 🔧 **Technical Implementation**
- Uses LiveKit's native `Agent` pattern with `openai.realtime.RealtimeModel`
- Transcription is built into the Agent framework - no additional imports needed
- Frontend receives transcription via standard LiveKit transcription events
- Compatible with existing agent conversation logic
- No dependencies on external STT services for basic transcription

## Frontend Integration

### 📡 **Receiving Transcriptions**
Frontend clients automatically receive transcription data through LiveKit's built-in events:

```typescript
// Frontend receives transcription via LiveKit's native events
room.on(RoomEvent.TranscriptionReceived, (segments: TranscriptionSegment[]) => {
  segments.forEach(segment => {
    console.log(`${segment.participant.identity}: ${segment.text}`);
    // Display transcription in UI
  });
});
```

### 🎨 **UI Integration**
- Real-time text display of all speech
- Speaker identification (users + AI agents)
- Automatic scrolling transcript
- Export/save transcript functionality

## Agent Configuration

### ✅ **Current Implementation**
Both Aristotle and Socrates agents use the built-in transcription:

```python
# Transcription is automatic with Agent pattern
agent = Agent(
    instructions="...",
    tools=[...]
)

# RealtimeModel includes built-in transcription
llm = openai.realtime.RealtimeModel(
    model="gpt-4o-realtime-preview-2024-12-17",
    voice="alloy",
    temperature=0.2
)

session = AgentSession(
    llm=llm,
    vad=silero.VAD.load(),
    # Transcription happens automatically
)
```

### 🚫 **What We Don't Need**
- ❌ No `STTSegmentsForwarder` (doesn't exist in LiveKit)
- ❌ No manual deepgram imports
- ❌ No manual transcription setup
- ❌ No additional dependencies

## Deployment Compatibility

### ✅ **Production Ready**
- **Works on all deployments**: Render, local, cloud
- **No additional dependencies**: Uses built-in LiveKit functionality
- **Automatic failover**: If transcription fails, agents continue normally
- **Zero configuration**: Works immediately upon deployment

### 🔧 **Configuration**
```bash
# No additional environment variables needed for basic transcription
# Standard LiveKit variables are sufficient:
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
LIVEKIT_URL=your_url
```

## Benefits

### 🚀 **Advantages of Built-in Transcription**
1. **Zero Setup**: Works immediately without configuration
2. **Reliable**: Uses LiveKit's proven transcription infrastructure  
3. **Integrated**: Seamlessly works with voice agents
4. **Efficient**: No additional API calls or dependencies
5. **Speaker ID**: Automatically identifies who is speaking
6. **Real-time**: Low latency transcription delivery

### 🎯 **Use Cases**
- **Live Captions**: Real-time captions during debates
- **Meeting Notes**: Automatic transcript generation
- **Accessibility**: Support for hearing-impaired users
- **Analysis**: Post-debate transcript analysis
- **Search**: Searchable conversation history

## Future Enhancements

For advanced transcription features, consider:
- **Custom STT providers**: For specialized domains
- **Translation**: Real-time language translation
- **Sentiment analysis**: Emotion detection in speech
- **Summary generation**: AI-powered transcript summaries

---

**Note**: This transcription feature is built into the LiveKit Agent framework and requires no additional setup or dependencies. It works automatically with your existing agent deployment. 