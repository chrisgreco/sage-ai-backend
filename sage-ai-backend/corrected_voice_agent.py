#!/usr/bin/env python3

"""
Corrected LiveKit Voice Agent for Sage AI
=========================================

This is the properly implemented LiveKit voice agent following the official
LiveKit Agents framework patterns. It integrates with our existing chat API
to provide voice interaction with our AI debate agents.

Based on official LiveKit Agents documentation.
"""

import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv

# Core LiveKit Agents imports
from livekit.agents import (
    Agent,
    AgentSession, 
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)

# LiveKit plugins - properly imported
try:
    from livekit.plugins import deepgram, cartesia, openai, silero
    PLUGINS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LiveKit plugins not available: {e}")
    PLUGINS_AVAILABLE = False

# Our existing chat API integration
import requests
import json

load_dotenv()

logger = logging.getLogger(__name__)

class SageChatIntegration:
    """Integration with our existing Sage AI chat API"""
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
    
    async def send_to_chat_api(self, message: str, room_name: str) -> dict:
        """Send message to our chat API and get AI response"""
        try:
            response = requests.post(
                f"{self.api_base}/debate",
                json={
                    "topic": message,
                    "room_name": room_name,
                    "participant_name": "voice-participant"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Chat API error: {response.status_code}")
                return {"response": "I'm having trouble processing that request."}
                
        except Exception as e:
            logger.error(f"Chat API exception: {e}")
            return {"response": "I apologize, there seems to be a connection issue."}

# Global chat integration instance
chat_integration = SageChatIntegration()

@function_tool
async def debate_with_ai_agents(
    context: RunContext,
    user_message: str,
    room_name: str = "voice-debate"
):
    """
    Send user's voice input to our AI debate agents and get their response.
    
    Args:
        user_message: What the user said
        room_name: The debate room name
    """
    
    logger.info(f"Processing voice input for room {room_name}: {user_message[:50]}...")
    
    # Send to our existing chat API
    result = await asyncio.to_thread(
        chat_integration.send_to_chat_api, 
        user_message, 
        room_name
    )
    
    # Extract the response
    ai_response = result.get("response", "I'm having trouble responding right now.")
    
    logger.info(f"AI agents responded: {ai_response[:50]}...")
    
    return {
        "response": ai_response,
        "room": room_name,
        "processed": True
    }

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the LiveKit voice agent.
    This follows the official LiveKit Agents pattern.
    """
    
    # Connect to the LiveKit room
    await ctx.connect()
    
    logger.info(f"Connected to LiveKit room: {ctx.room.name}")
    
    # Create the AI agent with instructions and tools
    agent = Agent(
        instructions=(
            "You are a sophisticated AI facilitator for the Sage AI debate platform. "
            "You coordinate voice conversations between human participants and our "
            "five AI debate agents: Socrates (the questioner), Aristotle (the analyst), "
            "Buddha (the peacekeeper), Hermes (the synthesizer), and Solon (the moderator). "
            "When users speak, relay their input to the debate agents and present their responses naturally. "
            "Keep responses conversational and engaging."
        ),
        tools=[debate_with_ai_agents],
    )
    
    # Configure the agent session with proper plugins
    if PLUGINS_AVAILABLE:
        session = AgentSession(
            # Voice Activity Detection
            vad=silero.VAD.load(),
            
            # Speech-to-Text (Deepgram Nova-3 model)
            stt=deepgram.STT(
                model="nova-3",
                language="en",
                smart_format=True,
                interim_results=True
            ),
            
            # Large Language Model (OpenAI GPT-4)
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=0.7
            ),
            
            # Text-to-Speech (Cartesia - matches our existing setup)
            tts=cartesia.TTS(
                voice="79a125e8-cd45-4c13-8a67-188112f4dd22"  # Professional voice
            ),
        )
    else:
        # Fallback session if plugins aren't available
        logger.warning("LiveKit plugins not available - creating basic session")
        session = AgentSession()
    
    # Start the agent session
    await session.start(agent=agent, room=ctx.room)
    
    # Generate initial greeting
    await session.generate_reply(
        instructions=(
            "Greet the user warmly and introduce yourself as the voice interface "
            "to the Sage AI debate platform. Let them know they can start a conversation "
            "and that our AI debate agents are ready to engage with them."
        )
    )
    
    logger.info("Sage AI voice agent is now active and listening...")

def main():
    """Main function to run the voice agent"""
    
    # Check for required environment variables
    required_env_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your .env file or environment")
        return
    
    if not PLUGINS_AVAILABLE:
        logger.error("LiveKit plugins not installed. Please install with:")
        logger.error("pip install livekit-plugins-deepgram livekit-plugins-cartesia livekit-plugins-openai livekit-plugins-silero")
        return
    
    logger.info("Starting Sage AI Voice Agent...")
    
    # Run the agent using LiveKit CLI
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # You can add more worker options here if needed
        )
    )

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main() 