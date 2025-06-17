#!/usr/bin/env python3

"""
Multi-Personality Debate Agent for Sage AI
==========================================

This is the CORRECT implementation following LiveKit Agents official patterns.
It replaces our complex audio bridge system with a simple, standard approach
that manages all 5 AI debate personalities in a single worker.

Based on Context7 MCP analysis of official LiveKit Agents documentation.
"""

import asyncio
import logging
import os
from typing import Dict
from dotenv import load_dotenv

# Knowledge base integration
from knowledge_base_manager import initialize_knowledge_bases, get_agent_knowledge

# Supabase memory integration for persistent conversation memory
from supabase_memory_manager import (
    create_or_get_debate_room, 
    store_debate_segment, 
    get_debate_memory, 
    store_ai_memory
)

# Core LiveKit Agents imports (correct pattern)
try:
    from livekit.agents import (
        Agent,
        AgentSession, 
        JobContext,
        RunContext,
        WorkerOptions,
        cli,
        function_tool,
    )
    
    # OpenAI Realtime API and turn detection (simplified approach)
    from livekit.plugins import openai
    from livekit.plugins.turn_detector.english import EnglishModel
    
    LIVEKIT_AVAILABLE = True
except ImportError as e:
    LIVEKIT_AVAILABLE = False
    print(f"LiveKit Agents not available: {e}")
    print("Install with: pip install 'livekit-agents[openai,turn-detector]>=1.0'")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "instructions": """You are Solon, the ancient lawgiver and moderator. Your role is to ensure 
        fair discourse, enforce speaking order, and guide the debate structure. You maintain civility 
        and ensure all voices are heard. Keep discussions on track, manage time, and ensure productive 
        dialogue. Step in when debates become unproductive."""
    }

class DebateAgent(Agent):
    """Single agent that can embody different personalities"""
    
    def __init__(self, personality: Dict):
        self.personality = personality
        super().__init__(
            instructions=personality["instructions"]
        )
        
    @function_tool
    async def switch_personality(
        self,
        context: RunContext,
        new_personality: str,
    ):
        """Switch to a different debate personality
        
        Args:
            new_personality: The personality to switch to (socrates, aristotle, buddha, hermes, solon)
        """
        personalities = {
            "socrates": DebatePersonalities.SOCRATES,
            "aristotle": DebatePersonalities.ARISTOTLE, 
            "buddha": DebatePersonalities.BUDDHA,
            "hermes": DebatePersonalities.HERMES,
            "solon": DebatePersonalities.SOLON
        }
        
        if new_personality.lower() in personalities:
            selected = personalities[new_personality.lower()]
            new_agent = DebateAgent(selected)
            logger.info(f"Switching to {selected['name']}")
            return new_agent, f"Now speaking as {selected['name']}"
        
        return None, f"Unknown personality: {new_personality}"

    @function_tool
    async def get_debate_topic(
        self,
        context: RunContext,
    ):
        """Get the current debate topic"""
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        return {"topic": topic}

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

    @function_tool
    async def summarize_key_points(
        self,
        context: RunContext,
        topic: str = "",
    ):
        """Summarize key points from the debate so far for memory retention
        
        Args:
            topic: Optional specific topic to focus the summary on
        """
        try:
            # This would be enhanced to maintain conversation summaries
            # For now, it helps with memory management instructions
            summary_instruction = f"""As {self.personality['name']}, I maintain awareness of:
            
1. Key arguments made by each participant
2. Important questions raised (especially by Socrates)
3. Logical frameworks presented (especially by Aristotle)  
4. Conflict resolution points (especially by Buddha)
5. Synthesis attempts (especially by Hermes)
6. Moderation decisions (especially by Solon)

Focus: {topic if topic else 'Overall debate progression'}"""

            return {"summary_context": summary_instruction}
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return {"error": f"Summarization failed: {str(e)}"}

async def entrypoint(ctx: JobContext):
    """Main entrypoint following official LiveKit Agents pattern"""
    
    logger.info("Starting Sage AI Multi-Personality Debate Agent")
    
    # Initialize knowledge bases
    logger.info("🧠 Initializing knowledge bases...")
    knowledge_ready = await initialize_knowledge_bases()
    if knowledge_ready:
        logger.info("✅ Knowledge bases loaded successfully")
    else:
        logger.warning("⚠️ Knowledge bases failed to load, continuing without specialized knowledge")
    
    # Connect to room
    await ctx.connect()
    
    # Get debate topic from environment or use default
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    room_name = os.getenv("ROOM_NAME", ctx.room.name)
    
    logger.info(f"Room: {room_name}")
    logger.info(f"Topic: {topic}")
    
    # Start with Solon as moderator
    moderator = DebateAgent(DebatePersonalities.SOLON)
    
    # Create agent session with OpenAI Realtime API
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="shimmer",
            temperature=0.7
        ),
        turn_detection=EnglishModel(),  # Proper turn-taking management
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
    )
    
    # Start the session
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

Let's begin our philosophical exploration!"""
    
    await session.generate_reply(instructions=greeting)
    
    logger.info("Debate session started successfully")

def main():
    """Main function to run the agent"""
    
    if not LIVEKIT_AVAILABLE:
        logger.error("LiveKit Agents not available")
        logger.error("Install with: pip install 'livekit-agents[openai,turn-detector]>=1.0'")
        return
    
    # Verify environment variables
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your environment or .env file")
        return
    
    logger.info("All required environment variables found")
    logger.info("Starting Multi-Personality Debate Agent...")
    
    # Run with proper WorkerOptions
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="sage-debate-agent"
        )
    )

if __name__ == "__main__":
    main() 