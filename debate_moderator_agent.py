#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Memory and Context
Follows official LiveKit 1.0 patterns from the documentation
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime

# Core LiveKit imports following official patterns
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import openai, silero, deepgram, cartesia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import memory manager with graceful fallback
try:
    from supabase_memory_manager import SupabaseMemoryManager
except ImportError:
    SupabaseMemoryManager = None

class DebateModerator(Agent):
    """LiveKit Agent for moderating debates with AI personas"""
    
    def __init__(self, persona: str = "Aristotle", topic: str = "AI in society"):
        self.persona = persona
        self.topic = topic
        
        # Initialize memory manager if available
        self.memory_manager = None
        if SupabaseMemoryManager:
            try:
                self.memory_manager = SupabaseMemoryManager()
                logger.info("✅ Memory manager initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Memory manager unavailable: {e}")
        
        super().__init__(
            instructions=self.get_prompt_for_persona(persona),
            tools=[self.moderate_discussion, self.fact_check_statement, self.set_debate_topic]
        )
    
    def get_prompt_for_persona(self, persona: str) -> str:
        """Get dynamic system prompt for the specified persona"""
        base_prompt = f"""You are {persona}, moderating a debate about "{self.topic}".

CRITICAL BEHAVIOR RULES:
- Respond naturally when participants speak to you
- Only interrupt if discussion becomes hostile or unproductive  
- Keep ALL responses to 1-2 sentences maximum
- Ask thoughtful questions to guide the discussion
- Stay in character as {persona}
- Be helpful and engaging while maintaining your philosophical approach

"""
        
        persona_specific = {
            "Aristotle": """As Aristotle:
- Use logical reasoning and find the golden mean
- Ask focused questions to clarify logic
- Guide toward virtue ethics and practical wisdom
- "What is the virtuous path here?"
- "Let us examine this through reason and evidence"
""",
            "Socrates": """As Socrates:
- Ask probing questions to reveal assumptions
- Use the Socratic method to guide discovery
- Challenge participants to think deeper
- "What do you mean by that?"
- "How do you know this to be true?"
""",
            "Buddha": """As Buddha:
- Focus on compassion and mindful consideration
- Guide toward understanding suffering and attachment
- Encourage middle way thinking
- "What attachment might be causing this view?"
- "How might we approach this with compassion?"
"""
        }
        
        return base_prompt + persona_specific.get(persona, persona_specific["Aristotle"])

    @function_tool
    async def moderate_discussion(
        self,
        context: RunContext,
        action: Annotated[str, "The moderation action to take"],
        reason: Annotated[str, "Reason for the moderation"],
    ):
        """Moderate the discussion when needed"""
        try:
            logger.info(f"🛡️ Moderation action: {action} - {reason}")
            
            if self.memory_manager:
                try:
                    await self.memory_manager.log_moderation_action(
                        session_id="current_session",
                        action=action,
                        reason=reason,
                        persona=self.persona
                    )
                except Exception as e:
                    logger.warning(f"Failed to log moderation: {e}")
            
            return f"As {self.persona}, I must {action}. {reason}"
        
        except Exception as e:
            logger.error(f"Error in moderate_discussion: {e}")
            return f"I apologize, but I encountered an issue while moderating. Let us continue with respect and understanding."

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        statement: Annotated[str, "The statement to fact-check"],
        participant: Annotated[str, "Who made the statement"],
    ):
        """Fact-check a statement made during the debate"""
        try:
            logger.info(f"🔍 Fact-checking: {statement}")
            
            # In a real implementation, this would call a fact-checking API
            return f"Let me examine that claim, {participant}. While I cannot verify all facts in real-time, I encourage us to consider the sources and evidence for such statements."
        
        except Exception as e:
            logger.error(f"Error in fact_check_statement: {e}")
            return f"I apologize, but I cannot fact-check that statement right now. Let us proceed with careful consideration of our claims."

    @function_tool
    async def set_debate_topic(
        self,
        context: RunContext,
        new_topic: Annotated[str, "The new topic for debate"],
    ):
        """Change the debate topic"""
        try:
            logger.info(f"📝 Setting new debate topic: {new_topic}")
            self.topic = new_topic
            
            if self.memory_manager:
                try:
                    await self.memory_manager.update_session_topic("current_session", new_topic)
                except Exception as e:
                    logger.warning(f"Failed to update topic: {e}")
            
            return f"Excellent! Let us now turn our attention to: {new_topic}"
        
        except Exception as e:
            logger.error(f"Error in set_debate_topic: {e}")
            return f"I apologize, but I encountered an issue changing the topic. Let us continue with our current discussion."

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following official patterns"""
    
    try:
        # Connect to the room first (official pattern)
        logger.info("🔗 Connecting to LiveKit room...")
        await ctx.connect()
        logger.info("✅ Successfully connected to LiveKit room")
        
        # Now we can access the actual room object and its metadata
        room = ctx.room
        room_metadata = {}
        
        # Safely get metadata if available
        if hasattr(room, 'metadata') and room.metadata:
            try:
                import json
                room_metadata = json.loads(room.metadata) if isinstance(room.metadata, str) else room.metadata
                logger.info(f"📋 Room metadata loaded: {room_metadata}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse room metadata: {e}, using defaults")
                room_metadata = {}
        
        # Extract persona and topic from room metadata or use defaults
        persona = room_metadata.get('persona', 'Aristotle')
        topic = room_metadata.get('topic', 'AI in society')
        
        logger.info(f"🎭 Starting {persona} moderator for topic: {topic}")
        
        # Create the debate moderator agent
        agent = DebateModerator(persona=persona, topic=topic)
        
        # Create session with Perplexity integration following official pattern
        logger.info("🔧 Creating AgentSession with Perplexity integration...")
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-2"),
            llm=openai.LLM.with_perplexity(
                model="sonar-pro",
                temperature=0.7,
            ),
            tts=openai.TTS(voice="alloy"),
        )
        logger.info("✅ AgentSession created successfully")
        
        # Start the session with the agent and room (official pattern)
        logger.info("🚀 Starting agent session...")
        await session.start(agent=agent, room=room)
        logger.info("✅ Agent session started successfully")
        
        # Generate initial greeting (official pattern)
        logger.info("👋 Generating initial greeting...")
        await session.generate_reply(
            instructions="Greet the participants and introduce yourself as the debate moderator. Briefly explain your role and invite them to begin the discussion."
        )
        logger.info("✅ Initial greeting generated successfully")
        
        # Keep the session alive
        logger.info("🔄 Agent is now active and ready for participants")
        
    except Exception as e:
        logger.error(f"❌ Critical error in entrypoint: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        
        # Try to handle gracefully
        try:
            if 'session' in locals():
                logger.info("🛑 Attempting graceful session cleanup...")
                # Session cleanup would go here if needed
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")
        
        # Re-raise the exception so LiveKit can handle it
        raise

if __name__ == "__main__":
    try:
        logger.info("🎬 Starting LiveKit Debate Moderator Agent...")
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        raise 