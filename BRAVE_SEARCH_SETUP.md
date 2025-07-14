# Brave Search API Integration Setup

## Overview
The Sage AI Backend now includes real-time fact-checking capabilities using the Brave Search API. This integration allows the AI agent to search the web for current information during debates.

## Configuration Required

### 1. Get Brave Search API Key
1. Visit [Brave Search API](https://api.search.brave.com/)
2. Sign up for a developer account
3. Subscribe to a plan (they offer a free tier)
4. Get your API key from the dashboard

### 2. Configure in Render
1. Go to your Render dashboard
2. Navigate to your `sage-ai-backend` service
3. Go to **Environment** tab
4. Add new environment variable:
   - **Key**: `BRAVE_API_KEY`
   - **Value**: Your Brave Search API key

### 3. Deploy
The deployment will happen automatically when you save the environment variable in Render.

## Features Implemented

### `brave_search` Function Tool
- **Purpose**: Search the web for real-time information
- **Usage**: Called automatically by the AI agent when fact-checking is needed
- **Returns**: Top 3 search results with titles and URLs
- **Error Handling**: Graceful fallback if API is unavailable

### Integration Points
- Integrated into the main agent as a function tool
- Follows LiveKit official patterns for tool implementation
- Uses `httpx` for async HTTP requests
- Proper error handling and logging

## Testing

### Local Testing
Run the test script to verify your API key works:
```bash
export BRAVE_API_KEY="your_api_key_here"
python test_brave_search.py
```

### Production Testing
1. Deploy with the API key configured
2. Start a debate session
3. Make a factual claim that can be verified
4. The agent should automatically use Brave Search for fact-checking

## API Limits
- Check your Brave Search API plan limits
- Free tier typically includes 2,000 queries per month
- Monitor usage in the Brave API dashboard

## Troubleshooting

### Testing Your Setup
Use the included test script to verify all API keys:
```bash
python test_api_keys.py
```

This will test:
- LiveKit configuration
- OpenAI API connectivity
- Brave Search API functionality
- Deepgram STT configuration
- Cartesia TTS configuration

### Common Issues

1. **"BRAVE_API_KEY not configured"**: 
   - Ensure the environment variable is set in Render dashboard
   - Variable name must be exactly `BRAVE_API_KEY`
   - Value should be your subscription token from Brave API dashboard

2. **"Brave search failed"**: 
   - Check API key validity in Brave dashboard
   - Verify account status and billing
   - Ensure you haven't exceeded rate limits

3. **OpenAI 404 errors**:
   - Check `OPENAI_API_KEY` is correctly set
   - Verify API key has access to `gpt-4o-mini` model
   - Check for any billing issues with OpenAI account

4. **Rate limiting**: 
   - Monitor usage in Brave Search dashboard
   - Upgrade your plan if hitting limits
   - Consider caching results for repeated queries

### Logs
Check Render logs for:
- API responses and error messages
- Environment variable loading
- Function tool execution
- Network connectivity issues

### Environment Variables Checklist
Ensure all these are set in Render:
- ✅ `LIVEKIT_URL`
- ✅ `LIVEKIT_API_KEY` 
- ✅ `LIVEKIT_API_SECRET`
- ✅ `OPENAI_API_KEY`
- ✅ `BRAVE_API_KEY`
- ✅ `DEEPGRAM_API_KEY`
- ✅ `CARTESIA_API_KEY`

## Architecture
```
LiveKit Agent
├── OpenAI GPT-4o-mini (LLM)
├── Brave Search API (Fact-checking)
├── Cartesia TTS (Voice synthesis)
├── Deepgram STT (Speech recognition)
└── Supabase (Memory management)
```

The agent now has real-time access to current web information for accurate fact-checking during philosophical debates. 