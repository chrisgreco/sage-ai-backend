#!/usr/bin/env python3
"""
Socrates Philosopher Agent - The inquisitive challenger with questioning + truth-seeking  
Provides Socratic questioning method combined with compassionate wisdom
"""

import os
import sys
import asyncio
import logging
import random
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Signal handling is managed by LiveKit framework - no manual handling needed

# LiveKit Agents imports
try:
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
    from livekit.plugins import openai, silero
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    sys.exit(1)

# Knowledge system imports (optional)
try:
    from knowledge_base_manager import get_agent_knowledge
    KNOWLEDGE_AVAILABLE = True
    logger.info("✅ Knowledge system available")
except ImportError as e:
    logger.warning(f"⚠️ Knowledge system not available: {e}")
    KNOWLEDGE_AVAILABLE = False
    
    async def get_agent_knowledge(agent_name, query, max_items=3):
        return []

# Supabase memory imports (optional)
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

class DebatePhilosopherAgent(Agent):
    """Socrates - The inquisitive challenger with questioning + truth-seeking"""
    
    def __init__(self):
        # Socrates + Buddha philosophical instructions
        instructions = """You are Socrates, the Sage AI Debate Philosopher. You embody the inquisitive challenger with questioning and truth-seeking, combining Socratic method with Buddhist wisdom.

YOUR CORE IDENTITY - SOCRATES (Questioning + Truth-Seeking):
- Role: The inquisitive challenger
- Traits: Socratic method, constant questioning, humble but piercing
- Tone: Calm and probing
- Strengths: Dissects assumptions, reveals contradictions, challenges overconfidence in claims

🔑 MINIMAL INTERVENTION PRINCIPLE:
- DEFAULT MODE: **MINDFUL LISTENING** - Observe the human debate with wisdom
- PRIMARY ROLE: **UNDERSTAND BEFORE QUESTIONING** - Let conversations develop naturally
- ONLY SPEAK WHEN:
  1. **EXPLICITLY CALLED UPON** by name ("Socrates, what's your view?")
  2. **PHILOSOPHICAL CLARITY URGENTLY NEEDED** (major contradictions, confused definitions)
  3. **ASSUMPTIONS CAUSING HARM** or preventing understanding
  4. **WISDOM SPECIFICALLY REQUESTED** for guidance or insight

🚫 DO NOT INTERRUPT FOR:
- Normal debate flow or passionate discussion
- Minor logical inconsistencies that humans can work through
- Everyday assumptions that don't block understanding
- General statements or opinions
- Heated but productive exchanges

PHILOSOPHICAL APPROACH (When intervention IS warranted):

🧠 SOCRATIC QUESTIONING:
- Ask probing questions that reveal deeper truths
- Challenge assumptions with "How do you know that?"
- Seek definitions: "What do we mean by [concept]?"
- Use the Socratic method to guide discovery
- Admit when you don't know something ("I know that I know nothing")
- Help others examine their beliefs and reasoning

🕯️ BUDDHIST WISDOM:
- Promote compassionate understanding of all perspectives
- Encourage mindful consideration before responding
- Seek harmony and reduce suffering in discourse
- Find middle paths through conflicts
- Listen deeply to underlying values and emotions
- Speak with gentle wisdom and patience

INTEGRATED APPROACH:
You fluidly combine Socratic questioning with Buddhist compassion:
- When confusion arises → Use Socratic questioning
- When conflict emerges → Offer Buddhist compassion and middle paths
- When assumptions need challenging → Apply gentle but persistent inquiry
- When wisdom is sought → Draw from both traditions

KNOWLEDGE ACCESS:
You have access to specialized knowledge from:
- Socratic questioning techniques and philosophical inquiry
- Buddhist meditation, mindfulness, and conflict resolution wisdom

COMMUNICATION STYLE (When you do speak):
- **BE CONCISE AND PROFOUND** - Short questions that cut to the heart of the matter
- For challenging assumptions: One simple, penetrating question
- For offering wisdom: Brief, memorable insights (like ancient proverbs)
- For finding middle ground: "What if both views have merit here?"
- **Maximum 1-2 sentences** - let the question or insight resonate
- Speak like the historical Socrates: brief, memorable, thought-provoking
- **NO lengthy philosophical lectures** - save time for human discovery

Remember: Your PRIMARY role is to practice mindful listening and let humans discover their own wisdom through natural debate. Your interventions should be rare but deeply meaningful - quality over quantity. The greatest wisdom often comes from patient observation."""

        super().__init__(instructions=instructions)
        
        # Socrates with compassionate wisdom
        self.philosophical_voices = ["socrates"]
        self.last_voice = None
        
        logger.info("🧠🕯️ Socrates (Inquisitive Challenger) Agent initialized")

    @function_tool
    async def access_philosophical_knowledge(self, context, query: str, approach: str = "socratic"):
        """Access specialized philosophical knowledge for Socratic questioning and wisdom
        
        Args:
            query: Question or topic to explore philosophically
            approach: Type of approach (socratic, compassionate)
        """
        if not KNOWLEDGE_AVAILABLE:
            return {"knowledge": "Knowledge system not available", "sources": []}
            
        try:
            # Choose knowledge source based on approach
            knowledge_source = "socrates"  # Default to Socratic knowledge
            if approach == "compassionate":
                knowledge_source = "socrates"  # Still use Socrates but could be Buddha-focused
            
            knowledge_items = await get_agent_knowledge(knowledge_source, query, max_items=3)
            
            if knowledge_items:
                knowledge_text = "\n\n".join([
                    f"Source: {item['source']}\n{item['content'][:400]}..." 
                    for item in knowledge_items
                ])
                return {
                    "knowledge": knowledge_text,
                    "sources": [item['source'] for item in knowledge_items],
                    "approach": approach.title()
                }
            else:
                return {"knowledge": "No relevant philosophical knowledge found", "sources": []}
                
        except Exception as e:
            logger.error(f"Knowledge access error: {e}")
            return {"error": f"Knowledge access failed: {str(e)}"}

    @function_tool
    async def suggest_philosophical_question(self, context, topic: str, approach: str = "socratic"):
        """Suggest philosophical questions to deepen the discussion
        
        Args:
            topic: Current discussion topic or statement
            approach: Type of questioning (socratic, analytical, compassionate)
        """
        question_templates = {
            "socratic": [
                f"What assumptions underlie the idea that {topic}?",
                f"How do we know {topic} is true?",
                f"What would someone who disagrees with {topic} say?",
                f"What does '{topic}' really mean?",
                f"What are the implications if {topic}?"
            ],
            "analytical": [
                f"What evidence supports {topic}?",
                f"What are the logical consequences of {topic}?",
                f"How can we categorize the different aspects of {topic}?",
                f"What are the practical applications of {topic}?",
                f"What causes {topic} and what effects does it have?"
            ],
            "compassionate": [
                f"How does {topic} affect different people's wellbeing?",
                f"What fears or hopes drive people's views on {topic}?",
                f"Where might we find common ground regarding {topic}?",
                f"How can we approach {topic} with greater understanding?",
                f"What would a middle path look like for {topic}?"
            ]
        }
        
        questions = question_templates.get(approach, question_templates["socratic"])
        suggested = random.choice(questions)
        
        approach_map = {
            "socratic": "🧠 Socratic questioning",
            "analytical": "📚 Aristotelian analysis", 
            "compassionate": "🕯️ Buddhist wisdom"
        }
        
        return f"{approach_map[approach]}: {suggested}"

    @function_tool
    async def get_debate_topic(self, context):
        """Get the current debate topic"""
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        return f"Current debate topic: {topic}"

async def entrypoint(ctx: JobContext):
    """Debate Philosopher agent entrypoint - only joins rooms marked for sage debates"""
    
    logger.info("🧠 Sage AI Debate Philosopher checking room metadata...")
    await ctx.connect()
    
    # ENHANCED TOPIC DETECTION - Check job metadata first (from agent dispatch)
    topic = "The impact of AI on society"  # Default fallback
    
    # Method 1: Check job metadata (primary method for agent dispatch)
    try:
        if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            logger.info(f"📋 Found job metadata: {ctx.job.metadata}")
            job_metadata = json.loads(ctx.job.metadata)
            job_topic = job_metadata.get("debate_topic")
            if job_topic:
                topic = job_topic
                logger.info(f"✅ Socrates found topic from job metadata: {topic}")
            else:
                logger.warning("⚠️ No 'debate_topic' key in job metadata")
        else:
            logger.info("📭 No job metadata available")
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"❌ Failed to parse job metadata: {e}")
    
    # Method 2: Check room metadata (fallback)
    room_metadata = None
    try:
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            room_metadata = json.loads(ctx.room.metadata)
            logger.info(f"🏠 Found room metadata: {room_metadata}")
            room_topic = room_metadata.get("debate_topic")
            if room_topic and topic == "The impact of AI on society":  # Only use if we didn't get from job
                topic = room_topic
                logger.info(f"✅ Socrates found topic from room metadata: {topic}")
    except Exception as e:
        logger.warning(f"Could not parse room metadata: {e}")
    
    # Method 3: Environment variable (final fallback)
    if topic == "The impact of AI on society":
        env_topic = os.getenv("DEBATE_TOPIC")
        if env_topic:
            topic = env_topic
            logger.info(f"✅ Using environment topic: {topic}")
    
    logger.info(f"🎯 SOCRATES FINAL TOPIC: {topic}")
    
    # REMOVED RESTRICTIVE ROOM FILTERING - Agents should join all rooms
    # The frontend doesn't set room_type="sage_debate" metadata, so this was blocking all rooms
    logger.info(f"✅ Joining room: {ctx.room.name}")
    
    logger.info(f"✅ Philosopher connected to room: {ctx.room.name}")
    room_name = ctx.room.name
    logger.info(f"🤔 Exploring the philosophical implications of: {topic}")
    
    # Initialize memory if available
    room_id = None
    memory_context = ""
    
    if SUPABASE_AVAILABLE:
        try:
            room_id = await create_or_get_debate_room(
                room_name=room_name,
                debate_topic=topic,
                livekit_token=room_name  # Using room_name as token
            )
            
            memory_data = await get_debate_memory(room_id)
            if memory_data["recent_segments"]:
                logger.info(f"📚 Loaded {len(memory_data['recent_segments'])} conversation segments")
                recent_summary = memory_data.get("session_summaries", [])
                if recent_summary:
                    memory_context = f"\n\nPrevious Discussion Context:\n{recent_summary[-1]}"
            
            logger.info(f"✅ Memory initialized for room {room_id}")
        except Exception as e:
            logger.warning(f"⚠️ Memory initialization failed: {e}")
    
    # Create philosopher agent
    philosopher = DebatePhilosopherAgent()
    
    # Enhanced instructions with memory and dynamic topic
    enhanced_instructions = philosopher.instructions + memory_context + f"\n\nDEBATE TOPIC: \"{topic}\"\nFocus your philosophical inquiry on this specific topic."
    
    # Import turn detector
    try:
        from livekit.plugins.turn_detector import EnglishModel
        turn_detector = EnglishModel.load()
        logger.info("✅ Using semantic turn detection")
    except ImportError:
        turn_detector = None
        logger.warning("⚠️ Semantic turn detection not available")
    
    # Create agent session with MALE voice and enhanced turn detection
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="onyx",  # FIXED: Deep, serious male voice for Socrates
            temperature=0.8,  # Higher temperature for more creative questioning
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        turn_detector=turn_detector,  # Semantic turn detection
        min_endpointing_delay=1.0,  # Socrates waits 1.0s minimum (different from Aristotle)
        max_endpointing_delay=3.5,
    )
    
    # Start session - LiveKit framework handles lifecycle automatically  
    await session.start(
        agent=Agent(instructions=enhanced_instructions),
        room=ctx.room
    )
    
    logger.info("✅ Debate Philosopher is ready to explore truth through inquiry!")

def main():
    """Main function"""
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("🚀 Starting Socrates (Inquisitive Challenger) Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="socrates"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 