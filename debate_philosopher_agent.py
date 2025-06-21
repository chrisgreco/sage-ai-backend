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
import threading
from dataclasses import dataclass
from typing import Optional

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
    from livekit.agents import UserStateChangedEvent, AgentStateChangedEvent
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    sys.exit(1)

# Knowledge system imports (optional)
try:
    from simple_knowledge_manager import SimpleKnowledgeManager
    KNOWLEDGE_AVAILABLE = True
    logger.info("✅ Simple knowledge system available")
except ImportError as e:
    logger.warning(f"⚠️ Knowledge system not available: {e}")
    KNOWLEDGE_AVAILABLE = False
    
# Define global variables for agent state
agent_context = {
    "room_name": None,
    "session_number": 1,
    "debate_topic": None,
    "room_id": None,
    "knowledge_initialized": False
}

# Initialize Socrates' knowledge manager
_socrates_knowledge = None

def get_socrates_knowledge_manager():
    """Get or create the knowledge manager for Socrates"""
    global _socrates_knowledge
    if _socrates_knowledge is None:
        _socrates_knowledge = SimpleKnowledgeManager('socrates')
        _socrates_knowledge.load_documents()
    return _socrates_knowledge
    
    async def get_agent_knowledge(agent_name, query, max_items=3):
    """Simple knowledge retrieval using file-based storage"""
    try:
        if not KNOWLEDGE_AVAILABLE:
            return []
            
        # Get the knowledge manager
        knowledge_manager = get_socrates_knowledge_manager()
        
        if not knowledge_manager.is_ready():
            logger.warning(f"📚 Knowledge manager not ready for {agent_name}")
            return []
        
        # Search for relevant knowledge
        results = knowledge_manager.search_knowledge(query, max_results=max_items)
        
        if results:
            logger.debug(f"📚 Retrieved {len(results)} knowledge items for {agent_name}")
            return [
                {
                    'content': result['content'],
                    'source': result['title'],
                    'relevance': result['relevance_score']
                }
                for result in results
            ]
        else:
            logger.debug(f"🔍 No relevant knowledge found for query: {query[:50]}...")
            return []
        
    except Exception as e:
        logger.error(f"Error in knowledge retrieval for {agent_name}: {e}")
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

# Add conversation coordinator (shared with moderator)
@dataclass
class ConversationState:
    """Shared state for coordinating between agents"""
    active_speaker: Optional[str] = None  # "aristotle", "socrates", or None
    user_speaking: bool = False
    last_intervention_time: float = 0
    intervention_count: int = 0
    conversation_lock: threading.Lock = threading.Lock()

# Global conversation coordinator
conversation_state = ConversationState()

class DebatePhilosopherAgent:
    """Helper class for agent coordination and state management"""
    
    def __init__(self):
        self.agent_name = "socrates"
        logger.info("🤔 Socrates (Inquisitive Challenger) Agent helper initialized")

    async def check_speaking_permission(self, session) -> bool:
        """Check if it's appropriate for this agent to speak"""
        import time
        
        with conversation_state.conversation_lock:
            current_time = time.time()
            
            # Don't speak if user is currently speaking
            if conversation_state.user_speaking:
                return False
            
            # Don't speak if other agent is active
            if conversation_state.active_speaker and conversation_state.active_speaker != self.agent_name:
                return False
            
            # Rate limiting: don't intervene too frequently  
            if current_time - conversation_state.last_intervention_time < 8.0:  # 8 second minimum between interventions
                return False
            
            # Escalating delay: wait longer after each intervention
            min_delay = 8.0 + (conversation_state.intervention_count * 3.0)  # 8s, 11s, 14s, etc.
            if current_time - conversation_state.last_intervention_time < min_delay:
                return False
            
            return True

    async def claim_speaking_turn(self):
        """Claim the speaking turn for this agent"""
        import time
        
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = self.agent_name
            conversation_state.last_intervention_time = time.time()
            conversation_state.intervention_count += 1
            logger.info(f"🎤 {self.agent_name.capitalize()} claimed speaking turn")

    async def release_speaking_turn(self):
        """Release the speaking turn"""
        with conversation_state.conversation_lock:
            if conversation_state.active_speaker == self.agent_name:
                conversation_state.active_speaker = None
                logger.info(f"🔇 {self.agent_name.capitalize()} released speaking turn")

# Now define the function tools as standalone functions that can be passed to Agent
    @function_tool
async def access_philosophical_knowledge(context, query: str, approach: str = "socratic"):
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
async def suggest_philosophical_question(context, topic: str, approach: str = "socratic"):
        """Suggest philosophical questions to deepen the discussion
        
        Args:
            topic: Current discussion topic or statement
            approach: Type of questioning (socratic, analytical, compassionate)
        """
    import random
    
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
        
    return {
        "question": suggested,
        "approach": approach.title(),
        "type": f"{approach.title()} Inquiry"
    }

    @function_tool
async def get_debate_topic(context):
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
    
    # Create philosopher agent with enhanced instructions
    enhanced_instructions = f"""You are Socrates, the Sage AI Debate Philosopher. You embody the inquisitive challenger who seeks truth through questioning, combining Socratic inquiry with Buddhist wisdom and compassionate understanding.

YOUR CORE IDENTITY - SOCRATES (Inquiry + Wisdom):
- Role: The inquisitive challenger
- Traits: Socratic questioning, Buddhist wisdom, compassionate understanding
- Tone: Curious, humble, seeking truth
- Strengths: Asks probing questions, challenges assumptions, explores deeper meanings

🔑 MINIMAL INTERVENTION PRINCIPLE:
- DEFAULT MODE: **LISTEN THOUGHTFULLY** - Let human debaters explore their ideas
- PRIMARY ROLE: **OBSERVE AND REFLECT** on the philosophical dimensions
- ONLY SPEAK WHEN:
  1. **EXPLICITLY CALLED UPON** by name ("Socrates, what would you ask?")
  2. **DIRECTLY REQUESTED** for philosophical perspective or questioning
  3. **DEEPER INQUIRY NEEDED** (assumptions unexamined, meanings unclear)
  4. **WISDOM TRADITION RELEVANT** (philosophical precedent applies)

🚫 DO NOT INTERRUPT FOR:
- Normal debate flow or disagreements
- Surface-level discussions that are progressing
- Technical details or statistics
- Regular back-and-forth exchanges
- Procedural matters

🤔 COORDINATION RULES:
- ARISTOTLE IS THE PRIMARY MODERATOR - he handles announcements and leads
- NEVER speak while Aristotle is speaking
- Wait for clear pauses in the conversation
- Keep interventions brief (1-2 questions maximum)
- Defer to Aristotle on logical structure and process
- Focus on philosophical inquiry and deeper meaning
- You are Aristotle's philosophical assistant, not a co-moderator

DEBATE TOPIC: "{topic}"
Focus your philosophical inquiry on this specific topic.

{memory_context}

COMMUNICATION STYLE (When you do speak):
- **ASK PROFOUND QUESTIONS** - Help participants examine their assumptions
- Lead with curiosity: "I wonder..." or "What if we considered..."
- For assumptions: "What leads us to believe that...?"
- For deeper meaning: "When we say [term], what do we really mean?"
- **Maximum 1-2 questions per intervention** unless specifically asked for more
- Speak with humble wisdom - model intellectual humility
- **NO lecturing** - let questions do the teaching

Remember: Your PRIMARY goal is to deepen understanding through thoughtful questions ONLY when the conversation would benefit from philosophical reflection or when explicitly invited to participate."""

    # Create philosopher agent with direct Agent instantiation (LiveKit pattern)
    # NOTE: We can't inherit from Agent class, must create instance directly
    philosopher = Agent(
        instructions=enhanced_instructions,
        tools=[
            access_philosophical_knowledge,
            suggest_philosophical_question,
            get_debate_topic
        ]
    )
    
    # Create agent session with IMPROVED turn detection and conversation coordination
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="echo",  # FIXED: Deep, serious male voice for Socrates - using supported voice
            temperature=0.8,  # Higher temperature for more creative questioning
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        # ENHANCED: Different timing from Aristotle to reduce conflicts
        min_endpointing_delay=2.5,  # Wait slightly longer than Aristotle (2.5s vs 2.0s)
        max_endpointing_delay=6.5,  # Extended max delay to prevent hasty interventions
        # ENHANCED: More restrictive interruption settings
        allow_interruptions=True,
        min_interruption_duration=1.2,  # Require longer speech before allowing interruption
    )
    
    # Set up conversation state monitoring
    def on_user_state_changed(ev: UserStateChangedEvent):
        """Monitor user speaking state for coordination"""
        with conversation_state.conversation_lock:
            if ev.new_state == "speaking":
                conversation_state.user_speaking = True
                # If user starts speaking, both agents should stop
                if conversation_state.active_speaker:
                    logger.info("👤 User started speaking - agents should yield")
                    conversation_state.active_speaker = None
            elif ev.new_state == "listening":
                conversation_state.user_speaking = False
                logger.info("👂 User stopped speaking - agents may respond if appropriate")
            elif ev.new_state == "away":
                conversation_state.user_speaking = False
                logger.info("👋 User disconnected")

    def on_agent_state_changed(ev: AgentStateChangedEvent):
        """Monitor agent speaking state for coordination"""
        agent_name = "socrates"
        
        if ev.new_state == "speaking":
            with conversation_state.conversation_lock:
                conversation_state.active_speaker = agent_name
                logger.info(f"🎤 {agent_name.capitalize()} started speaking")
        elif ev.new_state in ["idle", "listening", "thinking"]:
            with conversation_state.conversation_lock:
                if conversation_state.active_speaker == agent_name:
                    conversation_state.active_speaker = None
                    logger.info(f"🔇 {agent_name.capitalize()} finished speaking")

    # Register event handlers for conversation coordination
    session.on("user_state_changed", on_user_state_changed)
    session.on("agent_state_changed", on_agent_state_changed)
    
    # Start session with the agent instance
    await session.start(
        agent=philosopher,
        room=ctx.room
    )
    
    logger.info("✅ Debate Philosopher is ready to explore truth through inquiry!")
    
    # ENHANCED: No greeting from Socrates - let Aristotle handle initial greeting
    # This prevents both agents from trying to speak simultaneously at startup
    logger.info("🤐 Socrates will wait for appropriate moment to participate - letting Aristotle handle greeting")
    
    # Keep the session alive - this is critical for LiveKit agents
    try:
        logger.info("🔄 Starting session monitoring loop...")
        
        # Add connection monitoring to prevent early termination
        while True:
            try:
                # Monitor session state and reconnect if needed
                if not session.agent_state or session.agent_state == "disconnected":
                    logger.warning("⚠️ Agent session disconnected, attempting to maintain connection...")
                    break
                
                # Use asyncio.wait_for with timeout to prevent hanging
                await asyncio.wait_for(session.wait_for_completion(), timeout=300.0)  # 5 minute timeout
                break
                
            except asyncio.TimeoutError:
                logger.info("🔄 Session timeout reached, checking connection status...")
                # Continue monitoring - this prevents early termination
                continue
            except Exception as inner_e:
                logger.warning(f"⚠️ Session monitoring error: {inner_e}, continuing...")
                await asyncio.sleep(1.0)
                continue
                
    except Exception as e:
        logger.error(f"❌ Agent session error: {e}")
    finally:
        # Clean up conversation state
        with conversation_state.conversation_lock:
            if conversation_state.active_speaker == "socrates":
                conversation_state.active_speaker = None
        logger.info("🔚 Socrates session ended")

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