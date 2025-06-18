#!/usr/bin/env python3

"""
Sage AI Multi-Personality Debate Agent
Provides 5 distinct AI personalities for structured philosophical debates
"""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiveKit Agents imports - these MUST be available
try:
    from livekit import agents
    from livekit.agents import (
        Agent, 
        AgentSession, 
        JobContext, 
        RunContext, 
        WorkerOptions, 
        cli, 
        function_tool
    )
    from livekit.plugins import openai, silero
    LIVEKIT_AVAILABLE = True
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    logger.error("Install with: pip install 'livekit-agents[openai,silero]>=1.0'")
    LIVEKIT_AVAILABLE = False

# Memory system imports (optional)
try:
    from supabase_memory_manager import (
        create_or_get_debate_room,
        store_debate_segment,
        get_debate_memory,
        SUPABASE_AVAILABLE
    )
    logger.info("✅ Supabase memory system available")
except ImportError as e:
    logger.warning(f"⚠️ Supabase memory system not available: {e}")
    SUPABASE_AVAILABLE = False

# Knowledge system imports (optional)
try:
    from knowledge_base_manager import initialize_knowledge_bases, get_agent_knowledge
    KNOWLEDGE_AVAILABLE = True
    logger.info("✅ Knowledge system available")
except ImportError as e:
    logger.warning(f"⚠️ Knowledge system not available: {e}")
    KNOWLEDGE_AVAILABLE = False
    
    # Provide fallback functions
    async def initialize_knowledge_bases():
        return False
    
    async def get_agent_knowledge(agent_name, query, max_items=3):
        return []

class DebatePersonalities:
    """AI Debate Personalities with distinct characteristics"""
    
    SOCRATES = {
        "name": "Socrates",
        "voice": "echo",
        "instructions": """You are Socrates, the ancient Greek philosopher known for the Socratic method. 
        Your role is to ask probing questions that reveal deeper truths and challenge assumptions. 
        You believe that wisdom comes from recognizing what you don't know. Ask thoughtful questions 
        that help others examine their beliefs and reasoning. Keep responses concise and focused on inquiry."""
    }
    
    ARISTOTLE = {
        "name": "Aristotle", 
        "voice": "alloy",
        "instructions": """You are Aristotle, the systematic philosopher and scientist. Your role is to 
        provide factual analysis, logical reasoning, and evidence-based arguments. You excel at categorizing 
        ideas and finding practical solutions. Focus on empirical evidence, logical structure, and real-world 
        applications. Provide clear, well-reasoned responses."""
    }
    
    BUDDHA = {
        "name": "Buddha",
        "voice": "nova", 
        "instructions": """You are Buddha, the enlightened teacher focused on compassion and wisdom. 
        Your role is to promote peaceful resolution, mindful consideration, and understanding of different 
        perspectives. You seek to reduce suffering and find harmony. Speak with compassion, encourage 
        mindfulness, and help find middle paths through conflicts."""
    }
    
    HERMES = {
        "name": "Hermes",
        "voice": "onyx",
        "instructions": """You are Hermes, the messenger god and synthesizer of ideas. Your role is to 
        connect different viewpoints, find common ground, and summarize key insights from the discussion. 
        You excel at communication and bringing clarity to complex debates. Help bridge gaps between 
        different perspectives and highlight emerging consensus."""
    }
    
    SOLON = {
        "name": "Solon",
        "voice": "shimmer",
        "instructions": """You are Solon, the wise lawgiver and moderator. Your role is to maintain 
        order, ensure all voices are heard, and guide the discussion constructively. You facilitate 
        fair debate, summarize key points, and help the group reach meaningful conclusions. 
        Maintain neutrality while encouraging productive discourse."""
    }

class DebateAgent(Agent):
    """Enhanced Agent with personality switching and knowledge access"""
    
    def __init__(self, personality: Dict):
        super().__init__(instructions=personality["instructions"])
        self.personality = personality
        logger.info(f"Initialized {personality['name']} agent")

    @function_tool
    async def switch_personality(
        self,
        context: RunContext,
        new_personality: str,
    ):
        """Switch to a different AI personality during the debate
        
        Args:
            new_personality: Name of personality to switch to (Socrates, Aristotle, Buddha, Hermes, Solon)
        """
        personality_map = {
            "socrates": DebatePersonalities.SOCRATES,
            "aristotle": DebatePersonalities.ARISTOTLE, 
            "buddha": DebatePersonalities.BUDDHA,
            "hermes": DebatePersonalities.HERMES,
            "solon": DebatePersonalities.SOLON
        }
        
        new_personality_lower = new_personality.lower()
        if new_personality_lower in personality_map:
            self.personality = personality_map[new_personality_lower]
            return f"Switched to {self.personality['name']}. {self.personality['instructions'][:100]}..."
        else:
            return f"Personality '{new_personality}' not found. Available: {', '.join(personality_map.keys())}"

    @function_tool
    async def get_debate_topic(
        self,
        context: RunContext,
    ):
        """Get the current debate topic"""
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        return f"Current debate topic: {topic}"

    @function_tool
    async def access_knowledge(
        self,
        context: RunContext,
        query: str,
    ):
        """Access specialized knowledge for the current personality
        
        Args:
            query: The query or context to search for relevant knowledge
        """
        if not KNOWLEDGE_AVAILABLE:
            return {"knowledge": "Knowledge system not available", "sources": []}
            
        try:
            agent_name = self.personality["name"].lower()
            knowledge_items = await get_agent_knowledge(agent_name, query, max_items=3)
            
            if knowledge_items:
                knowledge_text = "\n\n".join([
                    f"Source: {item['source']}\n{item['content'][:500]}..." 
                    for item in knowledge_items
                ])
                return {
                    "knowledge": knowledge_text,
                    "sources": [item['source'] for item in knowledge_items]
                }
            else:
                return {"knowledge": "No relevant knowledge found", "sources": []}
                
        except Exception as e:
            logger.error(f"Knowledge access error: {e}")
            return {"error": f"Knowledge access failed: {str(e)}"}

async def entrypoint(ctx: JobContext):
    """Main entrypoint following official LiveKit Agents pattern"""
    
    logger.info("🎭 Starting Sage AI Multi-Personality Debate Agent")
    
    # Initialize knowledge bases if available
    if KNOWLEDGE_AVAILABLE:
        logger.info("🧠 Initializing knowledge bases...")
        knowledge_ready = await initialize_knowledge_bases()
        if knowledge_ready:
            logger.info("✅ Knowledge bases loaded successfully")
        else:
            logger.warning("⚠️ Knowledge bases failed to load, continuing without specialized knowledge")
    
    # Connect to room - this is critical for LiveKit agents
    logger.info("🔗 Connecting to LiveKit room...")
    await ctx.connect()
    logger.info(f"✅ Connected to room: {ctx.room.name}")
    
    # Get debate configuration from environment
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    room_name = os.getenv("ROOM_NAME", ctx.room.name)
    
    logger.info(f"🏛️ Room: {room_name}")
    logger.info(f"💬 Topic: {topic}")
    
    # Initialize Supabase memory for persistent conversation storage
    room_id = None
    memory_context = ""
    
    if SUPABASE_AVAILABLE:
        try:
            # Create or retrieve debate room in Supabase
            room_token = room_name  # Using room name as token
            room_id = await create_or_get_debate_room(
                room_token=room_token,
                topic=topic,
                max_duration_hours=24  # Allow up to 24-hour debates
            )
            
            # Load existing conversation memory 
            memory_data = await get_debate_memory(room_id)
            if memory_data["recent_segments"]:
                logger.info(f"📚 Loaded {len(memory_data['recent_segments'])} conversation segments from memory")
                # Add memory context to instructions
                recent_summary = memory_data.get("session_summaries", [])
                if recent_summary:
                    memory_context = f"\n\nConversation Memory:\n{recent_summary[-1]}"
            
            logger.info(f"✅ Supabase memory initialized for room {room_id}")
        except Exception as e:
            logger.warning(f"⚠️ Supabase memory initialization failed: {e}")
            room_id = None
    
    # Start with Solon as moderator
    moderator = DebateAgent(DebatePersonalities.SOLON)
    
    # Enhanced instructions with memory awareness
    enhanced_instructions = moderator.personality["instructions"] + memory_context
    
    # Create agent session with OpenAI Realtime API
    logger.info("🤖 Creating agent session with OpenAI Realtime API...")
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="shimmer",
            temperature=0.7,
            instructions=enhanced_instructions
        ),
        vad=silero.VAD.load(),  # Voice Activity Detection using Silero
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
    )
    
    # Start the session
    logger.info("🚀 Starting agent session...")
    await session.start(
        agent=moderator,
        room=ctx.room
    )
    
    # Generate initial greeting and setup
    greeting = f"""Welcome to the Sage AI Debate Room! I'm Solon, your moderator. 
    
Today's topic: "{topic}"

We have five AI personalities ready to engage:
- Socrates: The questioner who seeks truth through inquiry
- Aristotle: The analyst who provides logic and evidence  
- Buddha: The peacekeeper who seeks harmony and wisdom
- Hermes: The synthesizer who connects different viewpoints
- And myself, Solon: Your moderator ensuring fair discourse

{"Continuing our previous discussion..." if memory_context else "Let's begin our philosophical exploration!"}"""
    
    logger.info("💬 Generating initial greeting...")
    await session.generate_reply(instructions=greeting)
    
    # Store initial greeting in memory if available
    if room_id and SUPABASE_AVAILABLE:
        try:
            await store_debate_segment(
                room_id=room_id,
                speaker_name="Solon",
                speaker_type="ai",
                content=greeting,
                segment_type="greeting"
            )
            logger.info("💾 Stored greeting in memory")
        except Exception as e:
            logger.warning(f"Failed to store greeting in memory: {e}")
    
    logger.info("✅ Debate session started successfully! Agents are now active in the room.")

def main():
    """Main function to run the agent with proper error handling"""
    
    # Check if LiveKit is available
    if not LIVEKIT_AVAILABLE:
        logger.error("❌ LiveKit Agents not available")
        logger.error("Install with: pip install 'livekit-agents[openai,silero]>=1.0'")
        sys.exit(1)
    
    # Verify environment variables
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your environment or .env file")
        sys.exit(1)
    
    logger.info("✅ All required environment variables found")
    logger.info("🚀 Starting Multi-Personality Debate Agent...")
    
    # Run with proper WorkerOptions - REMOVE agent_name for automatic dispatch
    try:
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint
            )
        )
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 