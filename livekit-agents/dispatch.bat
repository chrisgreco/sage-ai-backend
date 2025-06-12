@echo off

rem Default parameters
set LIVEKIT_URL=wss://sage-2kpu4z1y.livekit.cloud
set LIVEKIT_API_KEY=APIWQtUQUijqXVp
set LIVEKIT_API_SECRET=LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI
set ROOM_NAME=test-debate-room

rem Display configuration
echo Using configuration:
echo   LIVEKIT_URL: %LIVEKIT_URL%
echo   LIVEKIT_API_KEY: %LIVEKIT_API_KEY%
echo   LIVEKIT_API_SECRET: %LIVEKIT_API_SECRET:~0,5%...
echo   ROOM_NAME: %ROOM_NAME%
if defined OPENAI_API_KEY (
  echo   OPENAI_API_KEY: %OPENAI_API_KEY:~0,5%...
) else (
  echo   OPENAI_API_KEY: not set (required for agent to work properly)
)

rem Run the dispatch agent
echo Starting LiveKit agent dispatcher...
python dispatch_agent.py %ROOM_NAME% 