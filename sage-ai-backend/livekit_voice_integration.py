#!/usr/bin/env python3

"""
LiveKit Voice Integration for Sage AI
====================================

This module integrates our improved chat API with LiveKit for real-time voice conversations.
It handles:
- Speech-to-Text conversion
- AI agent response generation via our chat API
- Text-to-Speech conversion  
- Turn-taking coordination
- Audio streaming to/from LiveKit rooms

Note: This is an advanced feature that requires additional LiveKit plugins.
For now, we use the audio bridge integration instead.
"""

import asyncio
import logging
import json
import os
from typing import Dict, Optional, Any
import requests
import numpy as np

# LiveKit imports - make them conditional
try:
    from livekit import rtc, api
    from livekit.agents import llm, stt, tts, utils, voice
    from livekit.agents.voice import Agent as VoiceAgent
    LIVEKIT_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LiveKit agents not available: {e}")
    LIVEKIT_AVAILABLE = False

# Plugin imports - make them conditional
try:
    from livekit.plugins import openai, deepgram
    PLUGINS_AVAILABLE = True
except ImportError:
    logging.warning("LiveKit plugins not available")
    PLUGINS_AVAILABLE = False

try:
    from livekit.plugins import elevenlabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    logging.warning("ElevenLabs plugin not available")
    ELEVENLABS_AVAILABLE = False

# Our chat API integration
CHAT_API_BASE = "http://localhost:8001"

logger = logging.getLogger(__name__)

class SageVoiceAgent:
    """
    Voice agent that integrates with our improved chat API
    """
    
    def __init__(self, room_id: str, api_base: str = CHAT_API_BASE):
        self.room_id = room_id
        self.api_base = api_base
        self.conversation_active = False
        
    async def send_to_chat_api(self, message: str) -> Dict[str, Any]:
        """Send message to our improved chat API"""
        try:
            response = requests.post(
                f"{self.api_base}/api/chat/message",
                json={"message": message, "room_id": self.room_id},
                timeout=30
            )
            return response.json()
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return {
                "response": {
                    "agent_name": "Solon", 
                    "agent_role": "Rule Enforcer",
                    "message": "I apologize, there seems to be a connection issue. Please try again."
                }
            }

    async def process_speech(self, text: str) -> tuple[str, str, str]:
        """
        Process speech through our chat API and return response info
        Returns: (agent_name, agent_role, response_message)
        """
        if not text.strip():
            return "Solon", "Rule Enforcer", "I didn't catch that. Could you please repeat?"
            
        # Send to our improved chat API
        result = await asyncio.to_thread(self.send_to_chat_api, text)
        
        response = result.get("response", {})
        agent_name = response.get("agent_name", "Solon")
        agent_role = response.get("agent_role", "Rule Enforcer") 
        message = response.get("message", "I'm having trouble processing that request.")
        
        logger.info(f"Agent {agent_name} ({agent_role}) responding to: {text[:50]}...")
        return agent_name, agent_role, message

class SageLiveKitAssistant:
    """
    Main LiveKit assistant integrating with Sage AI chat system
    """
    
    def __init__(self, room_id: str):
        if not LIVEKIT_AVAILABLE:
            raise ImportError("LiveKit agents not available. Please install with: pip install livekit-agents")
        
        self.room_id = room_id
        self.sage_agent = SageVoiceAgent(room_id)
        
        # Configure STT (Speech-to-Text)
        if PLUGINS_AVAILABLE:
            self.stt = deepgram.STT(
                model="nova-2-general",
                language="en",
                smart_format=True,
                interim_results=True
            )
        else:
            logger.warning("Deepgram STT not available")
            self.stt = None
        
        # Configure TTS (Text-to-Speech)
        if ELEVENLABS_AVAILABLE:
            self.tts = elevenlabs.TTS(
                voice=elevenlabs.Voice.DANIEL  # Professional male voice
            )
        else:
            logger.warning("ElevenLabs TTS not available")
            self.tts = None
        
        # Voice Assistant configuration
        if LIVEKIT_AVAILABLE and self.stt and self.tts:
            self.assistant = VoiceAgent(
                vad=rtc.VAD.for_speaking_detection(),  # Voice Activity Detection
                stt=self.stt,
                llm=self._create_llm_proxy(),  # Our custom LLM that calls chat API
                tts=self.tts,
                chat_ctx=llm.ChatContext(),
                will_synthesize_assistant_reply=self._will_synthesize_assistant_reply
            )
        else:
            logger.warning("Voice assistant not available - missing dependencies")
            self.assistant = None

    def _create_llm_proxy(self):
        """
        Create an LLM proxy that routes to our chat API instead of direct LLM calls
        """
        if not LIVEKIT_AVAILABLE:
            return None
            
        class SageChatLLMProxy(llm.LLM):
            def __init__(self, sage_agent: SageVoiceAgent):
                super().__init__()
                self.sage_agent = sage_agent
                
            async def agenerate(
                self, 
                *, 
                chat_ctx, 
                fnc_ctx: Optional[Any] = None,
                temperature: Optional[float] = None,
                n: Optional[int] = None,
                parallel_tool_calls: Optional[bool] = None,
            ):
                # Get the latest user message
                user_message = ""
                for msg in reversed(chat_ctx.messages):
                    if msg.role == "user":
                        user_message = msg.content
                        break
                
                # Process through our chat API
                agent_name, agent_role, response = await self.sage_agent.process_speech(user_message)
                
                # Create a mock LLM stream response
                class MockLLMStream:
                    def __init__(self, content: str):
                        self.content = content
                        self._finished = False
                    
                    async def __anext__(self):
                        if not self._finished:
                            self._finished = True
                            return {"content": self.content}
                        raise StopAsyncIteration
                    
                    def __aiter__(self):
                        return self
                
                return MockLLMStream(response)
                
        return SageChatLLMProxy(self.sage_agent)

    async def _will_synthesize_assistant_reply(
        self, 
        assistant, 
        chat_ctx
    ) -> bool:
        """
        Control when to synthesize speech - prevents overlapping responses
        """
        return not self.sage_agent.conversation_active

    async def connect_to_room(self, url: str, token: str):
        """Connect to LiveKit room and start voice assistant"""
        
        if not LIVEKIT_AVAILABLE or not self.assistant:
            raise RuntimeError("Voice assistant not available")
        
        # Connect to room
        room = rtc.Room()
        
        @room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(f"Participant connected: {participant.identity}")
            
        @room.on("track_published")
        def on_track_published(publication, participant):
            logger.info(f"Track published: {publication.sid}")
            
        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            logger.info(f"Track subscribed: {track.sid}")
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                asyncio.create_task(self.assistant.start(room, participant))
                
        # Connect to the room
        await room.connect(url, token)
        logger.info(f"Connected to LiveKit room: {self.room_id}")
        
        return room

async def main():
    """
    Example usage of the Sage LiveKit Voice Integration
    """
    if not LIVEKIT_AVAILABLE:
        logger.error("LiveKit agents not available. Please install with: pip install livekit-agents")
        return
        
    # Environment setup
    livekit_url = os.getenv("LIVEKIT_URL", "wss://sage-ai-backend-l0en.onrender.com")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([livekit_api_key, livekit_api_secret]):
        logger.error("Missing LiveKit credentials")
        return
    
    # Create room token
    token_api = api.AccessToken(livekit_api_key, livekit_api_secret)
    token_api.identity = "sage-ai-assistant"
    token_api.name = "Sage AI Assistant"
    
    # Create and connect assistant
    assistant = SageLiveKitAssistant("demo-room")
    
    try:
        room = await assistant.connect_to_room(livekit_url, token_api.to_jwt())
        logger.info("Voice assistant connected and running...")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down voice assistant...")
    except Exception as e:
        logger.error(f"Error running voice assistant: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 