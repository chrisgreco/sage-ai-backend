@echo off
echo 🚀 Starting Sage AI Agent...
echo 🔧 Environment Variables:
echo   LIVEKIT_URL: %LIVEKIT_URL%
echo   LIVEKIT_API_KEY: %LIVEKIT_API_KEY%
echo   OPENAI_API_KEY: %OPENAI_API_KEY%
echo   DEBATE_TOPIC: %DEBATE_TOPIC%
echo   ROOM_NAME: %ROOM_NAME%
echo   PERPLEXITY_API_KEY: %PERPLEXITY_API_KEY%

if "%LIVEKIT_URL%"=="" (
    echo ❌ LIVEKIT_URL not set
    exit /b 1
)

if "%LIVEKIT_TOKEN%"=="" (
    echo ❌ LIVEKIT_TOKEN not set
    exit /b 1
)

if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY not set
    exit /b 1
)

echo ✅ Environment variables OK

echo 📦 Pre-downloading models...
python debate_moderator_agent.py download-files

echo 🎯 Starting agent process...
python debate_moderator_agent.py 