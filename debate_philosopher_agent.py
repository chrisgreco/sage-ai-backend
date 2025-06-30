#!/usr/bin/env python3

"""
Sage AI Debate Philosopher Agent - Simple LiveKit Implementation
Handles Socrates persona with thoughtful questioning and dialogue exploration
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

class DebatePhilosopherAgent:
    """Simple debate philosopher agent (Socrates)"""
    
    def __init__(self):
        self.name = "philosopher"

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
async def explore_philosophical_dimensions(topic: str):
    """Explore the philosophical dimensions of a topic"""
    logger.info(f"🤔 Exploring philosophical dimensions of: {topic}")
    
    # Simple philosophical exploration responses
    philosophical_approaches = {
        "ethics": "Let us examine the ethical implications. What moral principles are at stake here? How do we determine what is right or good in this context?",
        "knowledge": "This raises questions about the nature of knowledge itself. How do we know what we claim to know? What are the sources and limits of our understanding?",
        "existence": "What does this tell us about the nature of existence and reality? Are we dealing with fundamental questions about what it means to be?",
        "truth": "How do we determine what is true here? What methods of inquiry will lead us to genuine understanding rather than mere opinion?",
        "justice": "What principles of justice apply in this situation? How do we ensure fairness and consider all perspectives?",
        "wisdom": "The pursuit of wisdom requires us to question our assumptions. What do we think we know, and how might we be mistaken?"
    }
    
    for key, approach in philosophical_approaches.items():
        if key in topic.lower():
            return approach
    
    return "Let us examine this more deeply. What assumptions are we making? What questions should we be asking that we haven't yet considered?"

@function_tool
async def ask_socratic_question(statement: str):
    """Generate Socratic questions to explore a statement more deeply"""
    logger.info(f"❓ Generating Socratic question for: {statement}")
    
    # Types of Socratic questions
    question_types = [
        "What do you mean when you say '{}'?",
        "What evidence supports this view?",
        "How does this relate to what we discussed earlier?",
        "What might someone who disagrees say?",
        "What are the implications if this is true?",
        "What assumptions are underlying this statement?",
        "How did you come to this conclusion?",
        "What if we considered the opposite perspective?",
        "Can you give me an example of what you mean?",
        "What questions does this raise for you?"
    ]
    
    import random
    question_template = random.choice(question_types)
    
    if '{}' in question_template:
        return question_template.format(statement[:50] + "..." if len(statement) > 50 else statement)
    else:
        return question_template

@function_tool
async def examine_assumptions(argument: str):
    """Help examine the underlying assumptions in an argument"""
    logger.info(f"🔍 Examining assumptions in: {argument}")
    
    return f"Let us pause and examine the foundations of this argument. What assumptions are we taking for granted? If we question these basic premises, how might our understanding change? What would happen if we assumed the opposite?"

@function_tool
async def seek_definition(concept: str):
    """Ask for clarification and definition of key concepts"""
    logger.info(f"📖 Seeking definition for: {concept}")
    
    return f"Before we proceed, let us ensure we understand what we mean by '{concept}'. How would you define this term? Are we all using it in the same way? What are the essential characteristics that make something '{concept}'?"

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the debate philosopher agent"""
    logger.info(f"🏛️ Starting Debate Philosopher Agent")
    
    # Get debate topic and philosopher persona from job metadata
    debate_topic = "The impact of AI on society"  # Default
    philosopher_persona = "Socrates"  # Default persona

    # Check job metadata
    if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata'):
        try:
            metadata = json.loads(ctx.job.metadata) if isinstance(ctx.job.metadata, str) else ctx.job.metadata
            debate_topic = metadata.get("debate_topic", debate_topic)
            philosopher_persona = metadata.get("philosopher", philosopher_persona)
            logger.info(f"📋 Job metadata - Topic: {debate_topic}, Philosopher: {philosopher_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse job metadata: {e}")

    # Also check room metadata
    if ctx.room.metadata:
        try:
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("topic", debate_topic)
            philosopher_persona = room_metadata.get("philosopher", philosopher_persona)
            logger.info(f"📋 Room metadata - Topic: {debate_topic}, Philosopher: {philosopher_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")

    # Set environment variables
    os.environ["DEBATE_TOPIC"] = debate_topic
    os.environ["PHILOSOPHER_PERSONA"] = philosopher_persona

    # Create philosopher agent
    philosopher = DebatePhilosopherAgent()

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
        tts = openai.TTS(voice="echo")  # Different voice for Socrates
        logger.info("✅ TTS initialized")
    except Exception as tts_error:
        logger.error(f"❌ Failed to initialize TTS: {tts_error}")
        raise

    # Create agent session
    try:
        logger.info(f"🤖 Creating AgentSession for {philosopher_persona}")
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
            agent_name = philosopher_persona.lower()
            if event.new_state == "speaking":
                with conversation_state.conversation_lock:
                    conversation_state.active_speaker = agent_name
                    logger.info(f"🎤 {philosopher_persona} started speaking")
            elif event.new_state in ["idle", "listening", "thinking"]:
                with conversation_state.conversation_lock:
                    if conversation_state.active_speaker == agent_name:
                        conversation_state.active_speaker = None
                        logger.info(f"🔇 {philosopher_persona} finished speaking")
        except Exception as e:
            logger.error(f"❌ Error in agent_state_changed handler: {e}")

    # Start the agent session
    try:
        logger.info(f"🚀 Starting agent session for {philosopher_persona}")
        await agent_session.start(agent=philosopher, room=ctx.room)
        logger.info(f"✅ Agent session started successfully")
    except Exception as start_error:
        logger.error(f"❌ Failed to start agent session: {start_error}")
        raise

    # Generate initial greeting
    def get_persona_greeting(persona: str, topic: str) -> str:
        if persona.lower() == "socrates":
            return f"Greetings, friends. I am Socrates. We gather to explore: {topic}. I know that I know nothing, so let us discover truth together through questions. What do you think you know about this topic?"
        elif persona.lower() == "plato":
            return f"Welcome to this dialogue on: {topic}. I am Plato. Let us seek the ideal forms of truth through reasoned discussion."
        else:  # Default Socrates
            return f"Greetings. I am here to explore: {topic}. Through questioning, we may discover what we truly know and what we merely think we know."

    try:
        initial_prompt = get_persona_greeting(philosopher_persona, debate_topic)
        logger.info(f"🎭 Generated greeting for {philosopher_persona}")
        await agent_session.say(initial_prompt)
        logger.info(f"✅ Initial greeting sent successfully")
    except Exception as greeting_error:
        logger.error(f"❌ Failed to generate initial greeting: {greeting_error}")

    logger.info(f"🏛️ {philosopher_persona} agent is now active and listening...")

    # Keep the agent session alive
    try:
        # Create a shutdown event
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info(f"🛑 Shutdown signal received for {philosopher_persona}")
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
        logger.info(f"🔚 {philosopher_persona} agent shutting down gracefully")
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info(f"🔚 {philosopher_persona} agent session interrupted")
    except Exception as session_error:
        logger.error(f"❌ Agent session error: {session_error}")
    finally:
        logger.info(f"🔚 {philosopher_persona} agent session cleanup starting...")
        
        # Clean up agent session
        if hasattr(agent_session, 'aclose'):
            try:
                await agent_session.aclose()
                logger.info(f"✅ Agent session closed successfully")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Error closing agent session: {cleanup_error}")
        
        logger.info(f"🔚 {philosopher_persona} agent session ended")

def main():
    """Main entry point for the debate philosopher agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="philosopher",
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main() 