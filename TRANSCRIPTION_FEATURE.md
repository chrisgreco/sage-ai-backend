# Transcription Feature

## Overview

The Sage AI debate agents now include **real-time transcription** capabilities that capture and forward speech from all participants to the frontend clients.

## How It Works

### 🎯 **Multi-Speaker Transcription**
- **Socrates agent** captures audio from all participants (Aristotle focuses on moderation)
- **Deepgram STT** converts speech to text in real-time
- **Transcription segments** are forwarded to frontend clients
- **Each speaker is identified** by their participant identity
- **Single transcription source** prevents duplicate segments

### 🔧 **Technical Implementation**
- Uses `STTSegmentsForwarder` from LiveKit Agents framework
- Integrates with existing audio track subscription system
- Forwards transcriptions as data messages to the room
- Compatible with existing agent conversation logic

## Frontend Integration

### 📡 **Receiving Transcriptions**
Your frontend can receive transcription events using LiveKit SDK:

```typescript
import { Room, RoomEvent, TranscriptionSegment } from 'livekit-client';

// Listen for transcription events
room.on(RoomEvent.TranscriptionReceived, (segments: TranscriptionSegment[]) => {
  segments.forEach(segment => {
    console.log(`${segment.participant.identity}: ${segment.text}`);
    
    // Check if segment is final (complete)
    if (segment.final) {
      // Store or display the complete transcription
      addToTranscript(segment.participant.identity, segment.text);
    }
  });
});
```

### 📝 **Transcription Data Structure**
Each transcription segment includes:
- `id`: Unique segment identifier
- `text`: The transcribed text
- `participant`: Speaker information
- `track`: Associated audio track
- `final`: Whether the segment is complete
- `timestamp`: When the segment was created

## Configuration

### 🔑 **Required Environment Variables**
Add to your `.env` file:
```bash
# Deepgram API key for speech-to-text
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

### 📦 **Dependencies**
The following dependency has been added to `requirements.txt`:
```
livekit-agents[openai,silero,turn-detector,deepgram]>=1.0
```

## Features

### ✅ **What's Included**
- **Real-time transcription** of all participants
- **Speaker identification** (users, Aristotle, Socrates)
- **Automatic forwarding** to frontend clients
- **Integration with existing debate logic**
- **Single-agent transcription** (Socrates only, prevents duplicates)

### 🔄 **Transcription Flow**
1. **Audio Track Subscription**: Agents subscribe to all participant audio
2. **STT Processing**: Deepgram converts speech to text
3. **Segment Creation**: Text is packaged into transcription segments
4. **Frontend Forwarding**: Segments are sent to all connected clients
5. **Real-time Display**: Frontend can display live transcriptions

## Usage Examples

### 🎤 **Debate Transcription**
Perfect for:
- **Live debate transcription** during discussions
- **Meeting minutes** generation
- **Accessibility** for hearing-impaired participants
- **Content analysis** and review
- **AI-powered moderation** based on transcript content

### 🔍 **Integration with Existing Features**
- **Memory System**: Transcriptions can be stored in Supabase
- **Knowledge Base**: Agents can reference transcribed content
- **Fact-Checking**: Use transcriptions for real-time verification
- **Argument Analysis**: Analyze transcribed arguments for structure

## Deployment Notes

### 🚀 **Render Deployment**
- Transcription works automatically with existing deployment
- Ensure `DEEPGRAM_API_KEY` is set in Render environment variables
- No additional configuration needed

### 🔧 **Local Development**
1. Get Deepgram API key from [deepgram.com](https://deepgram.com)
2. Add to your `.env` file
3. Install updated dependencies: `pip install -r requirements.txt`
4. Run agents normally - transcription will be active

## Monitoring

### 📊 **Logs**
Look for these log messages:
- `✅ LiveKit Agents successfully imported` (includes Deepgram)
- `🎧 [Agent] subscribed to audio track from: [participant]`
- `📝 Transcription forwarding active`

### 🐛 **Troubleshooting**
- **No transcriptions**: Check Deepgram API key
- **Missing segments**: Verify audio track subscription
- **Frontend not receiving**: Check TranscriptionReceived event handler

## Future Enhancements

### 🔮 **Planned Features**
- **Conversation summaries** based on transcriptions
- **Keyword highlighting** for important topics
- **Multi-language support** via Deepgram
- **Custom vocabulary** for domain-specific terms
- **Integration with memory system** for persistent storage

---

The transcription feature enhances the Sage AI debate system by providing real-time speech-to-text capabilities, making conversations more accessible and enabling advanced analysis features. 