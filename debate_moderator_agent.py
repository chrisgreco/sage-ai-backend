#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Simple LiveKit Implementation
Handles debate moderation with basic error handling
"""

import os
import sys
import asyncio
import logging
import json
import time
import threading
import signal
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Set, Dict, List, Any
from enum import Enum

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiveKit Agents imports
try:
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
    from livekit.plugins import openai, silero
    from livekit import rtc
    from livekit.rtc import TrackKind
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
    sys.exit(1)

# Check if Perplexity is available
PERPLEXITY_AVAILABLE = bool(os.environ.get("PERPLEXITY_API_KEY"))
if PERPLEXITY_AVAILABLE:
    logger.info("✅ Perplexity research available")
else:
    logger.warning("⚠️ Perplexity API key not found - research features disabled")

@dataclass
class ConversationState:
    """Shared state for coordinating between agents"""
    active_speaker: Optional[str] = None
    user_speaking: bool = False
    last_intervention_time: float = 0
    intervention_count: int = 0
    conversation_lock: threading.Lock = threading.Lock()

# Global conversation state
conversation_state = ConversationState()

class DebateModeratorAgent:
    """Simple debate moderator agent"""
    
    def __init__(self):
        self.name = "moderator"

    async def check_speaking_permission(self, session) -> bool:
        """Check if agent can speak"""
        with conversation_state.conversation_lock:
            if conversation_state.user_speaking:
                return False
            if conversation_state.active_speaker and conversation_state.active_speaker != self.name:
                return False
            return True

    async def claim_speaking_turn(self):
        """Claim speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = self.name

    async def release_speaking_turn(self):
        """Release speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = None

@function_tool
async def get_debate_topic():
    """Get the current debate topic"""
    topic = os.environ.get("DEBATE_TOPIC", "The impact of AI on society")
    logger.info(f"📋 Current debate topic: {topic}")
    return f"The current debate topic is: {topic}"

@function_tool
async def access_facilitation_knowledge(query: str):
    """Access debate facilitation knowledge"""
    logger.info(f"🧠 Accessing facilitation knowledge for: {query}")
    
    # Simple knowledge responses
    knowledge_responses = {
        "logical fallacy": "Common logical fallacies include ad hominem, straw man, false dichotomy, and appeal to authority. When you notice these, gently redirect the conversation to address the actual argument.",
        "debate structure": "A good debate follows: opening statements, main arguments with evidence, rebuttals, and closing summaries. Ensure each participant has equal time.",
        "moderation": "As a moderator, remain neutral, ensure fair participation, fact-check claims, and guide the conversation toward productive discourse.",
        "evidence": "Strong arguments require credible evidence. Ask for sources, verify claims, and distinguish between opinion and fact."
    }
    
    for key, response in knowledge_responses.items():
        if key in query.lower():
            return response
    
    return "I can help with debate structure, logical fallacies, moderation techniques, and evidence evaluation. What specific aspect would you like guidance on?"

@function_tool
async def suggest_process_intervention(situation: str):
    """Suggest process interventions for debate management"""
    logger.info(f"🔧 Suggesting intervention for: {situation}")
    
    interventions = {
        "interruption": "Let's ensure everyone has a chance to complete their thoughts. Please hold questions until the speaker finishes.",
        "off-topic": "This is an interesting point, but let's return to our main topic. How does this relate to our current discussion?",
        "personal attack": "Let's focus on the ideas and arguments rather than personal characteristics. Can you rephrase that to address the position itself?",
        "repetition": "I notice we're revisiting this point. Let's either explore a new angle or move to the next aspect of the debate.",
        "dominance": "Thank you for your passion. Let's hear from others who haven't had a chance to contribute recently.",
        "confusion": "Let me help clarify the current state of our discussion and the key points raised so far."
    }
    
    for key, intervention in interventions.items():
        if key in situation.lower():
            return intervention
    
    return "Consider: pausing for clarification, summarizing key points, ensuring balanced participation, or refocusing on the topic."

@function_tool
async def fact_check_claim(claim: str, source_requested: bool = False):
    """Fact-check a claim made during the debate"""
    logger.info(f"🔍 Fact-checking claim: {claim}")
    
    # Simple fact-checking responses
    if source_requested:
        return f"I'd like to verify this claim: '{claim}'. Could you provide a source for this information so we can evaluate its credibility?"
    
    return f"This claim requires verification: '{claim}'. Let's examine the evidence supporting this statement. What sources inform this position?"

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the debate moderator agent"""
    logger.info(f"🏛️ Starting Debate Moderator Agent")
    
    # Get debate topic and moderator persona from job metadata
    debate_topic = "The impact of AI on society"  # Default
    moderator_persona = "Aristotle"  # Default persona

    # Check job metadata
    if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata'):
        try:
            metadata = json.loads(ctx.job.metadata) if isinstance(ctx.job.metadata, str) else ctx.job.metadata
            debate_topic = metadata.get("debate_topic", debate_topic)
            moderator_persona = metadata.get("moderator", moderator_persona)
            logger.info(f"📋 Job metadata - Topic: {debate_topic}, Moderator: {moderator_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse job metadata: {e}")

    # Also check room metadata
    if ctx.room.metadata:
        try:
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("topic", debate_topic)
            moderator_persona = room_metadata.get("moderator", moderator_persona)
            logger.info(f"📋 Room metadata - Topic: {debate_topic}, Moderator: {moderator_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")

    # Set environment variables
    os.environ["DEBATE_TOPIC"] = debate_topic
    os.environ["MODERATOR_PERSONA"] = moderator_persona

    # Create moderator agent
    moderator = DebateModeratorAgent()

    # Initialize LLM
    try:
        if PERPLEXITY_AVAILABLE:
            research_llm = openai.LLM.with_perplexity(
                model="llama-3.1-sonar-large-128k-online"
            )
            logger.info("✅ Perplexity LLM initialized")
        else:
            research_llm = openai.LLM(model="gpt-4o-mini")
            logger.info("✅ OpenAI LLM initialized")
    except Exception as llm_error:
        logger.error(f"❌ Failed to initialize LLM: {llm_error}")
        raise

    # Initialize TTS
    try:
        tts = openai.TTS(voice="nova")
        logger.info("✅ TTS initialized")
    except Exception as tts_error:
        logger.error(f"❌ Failed to initialize TTS: {tts_error}")
        raise

    # Create agent session
    try:
        logger.info(f"🤖 Creating AgentSession for {moderator_persona}")
        agent_session = AgentSession(
            stt=openai.STT(),
            llm=research_llm,
            tts=tts,
            vad=silero.VAD.load()
        )
        logger.info(f"✅ AgentSession created successfully")
    except Exception as session_error:
        logger.error(f"❌ Failed to create AgentSession: {session_error}")
        raise

    # Register event handlers
    @agent_session.on("user_state_changed")
    def handle_user_state_changed(event):
        """Monitor user speaking state"""
        try:
            with conversation_state.conversation_lock:
                if event.new_state == "speaking":
                    conversation_state.user_speaking = True
                    if conversation_state.active_speaker:
                        logger.info("👤 User started speaking - agent should yield")
                        conversation_state.active_speaker = None
                elif event.new_state == "listening":
                    conversation_state.user_speaking = False
                    logger.info("👂 User stopped speaking")
        except Exception as e:
            logger.error(f"❌ Error in user_state_changed handler: {e}")

    @agent_session.on("agent_state_changed")
    def handle_agent_state_changed(event):
        """Monitor agent speaking state"""
        try:
            agent_name = moderator_persona.lower()
            if event.new_state == "speaking":
                with conversation_state.conversation_lock:
                    conversation_state.active_speaker = agent_name
                    logger.info(f"🎤 {moderator_persona} started speaking")
            elif event.new_state in ["idle", "listening", "thinking"]:
                with conversation_state.conversation_lock:
                    if conversation_state.active_speaker == agent_name:
                        conversation_state.active_speaker = None
                        logger.info(f"🔇 {moderator_persona} finished speaking")
        except Exception as e:
            logger.error(f"❌ Error in agent_state_changed handler: {e}")

    # Start the agent session
    try:
        logger.info(f"🚀 Starting agent session for {moderator_persona}")
        await agent_session.start(agent=moderator, room=ctx.room)
        logger.info(f"✅ Agent session started successfully")
    except Exception as start_error:
        logger.error(f"❌ Failed to start agent session: {start_error}")
        raise

    # Generate initial greeting
    def get_persona_greeting(persona: str, topic: str) -> str:
        if persona.lower() == "socrates":
            return f"Welcome to this debate on: {topic}. I am Socrates. I will help explore this topic through thoughtful questioning."
        elif persona.lower() == "buddha":
            return f"Welcome to this debate on: {topic}. I am Buddha. I will help maintain harmony and understanding in our discussion."
        else:  # Aristotle
            return f"Welcome to this debate on: {topic}. I am Aristotle. I will help ensure our discussion is grounded in evidence and sound reasoning."

    try:
        initial_prompt = get_persona_greeting(moderator_persona, debate_topic)
        logger.info(f"🎭 Generated greeting for {moderator_persona}")
        await agent_session.say(initial_prompt)
        logger.info(f"✅ Initial greeting sent successfully")
    except Exception as greeting_error:
        logger.error(f"❌ Failed to generate initial greeting: {greeting_error}")

    logger.info(f"🏛️ {moderator_persona} agent is now active and listening...")

    # Keep the agent session alive
    try:
        # Create a shutdown event
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info(f"🛑 Shutdown signal received for {moderator_persona}")
            shutdown_event.set()
        
        # Register signal handlers
        try:
            loop = asyncio.get_running_loop()
            for sig in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(sig, signal_handler)
        except (NotImplementedError, RuntimeError):
            logger.debug("Signal handling not available in this environment")
        
        # Wait for shutdown
        await shutdown_event.wait()
        logger.info(f"🔚 {moderator_persona} agent shutting down gracefully")
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info(f"🔚 {moderator_persona} agent session interrupted")
    except Exception as session_error:
        logger.error(f"❌ Agent session error: {session_error}")
    finally:
        logger.info(f"🔚 {moderator_persona} agent session cleanup starting...")
        
        # Clean up agent session
        if hasattr(agent_session, 'aclose'):
            try:
                await agent_session.aclose()
                logger.info(f"✅ Agent session closed successfully")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Error closing agent session: {cleanup_error}")
        
        logger.info(f"🔚 {moderator_persona} agent session ended")

def main():
    """Main entry point for the debate moderator agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main() 