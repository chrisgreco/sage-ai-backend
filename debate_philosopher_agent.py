#!/usr/bin/env python3
"""
Socrates Philosopher Agent - The inquisitive challenger with wisdom + questions
Provides philosophical inquiry, Socratic questioning, and deeper exploration
"""

import os
import sys
import asyncio
import logging
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
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool, AutoSubscribe
    from livekit.plugins import openai, silero
    from livekit.agents import UserStateChangedEvent, AgentStateChangedEvent
    from livekit import rtc  # For audio track handling
    logger.info("✅ LiveKit Agents core successfully imported")
    
    # NOTE: Transcription is handled automatically by the Agent framework
    # No need for manual STTSegmentsForwarder - LiveKit handles this internally
    logger.info("📝 Transcription will be handled by Agent framework automatically")
        
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
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

# Create philosopher agent helper instance
philosopher_agent_helper = DebatePhilosopherAgent()

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
    """Debate Philosopher agent entrypoint - joins rooms to provide philosophical inquiry"""
    
    logger.info("🤔 Sage AI Debate Philosopher checking room metadata...")
        # ENHANCED: Connect with auto_subscribe to hear all participants including other agents  
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    
    # ENHANCED: Set up audio track monitoring for inter-agent coordination
    audio_tracks = {}  # Track audio sources from other participants
    other_agents = set()  # Track other agent identities
    
    # NOTE: Transcription is automatically handled by the Agent framework
    # The Agent pattern with openai.realtime.RealtimeModel includes built-in transcription
    # Clients will receive transcription via LiveKit's native transcription events
    
    def on_track_subscribed(track, publication, participant):
        """Handle when we subscribe to an audio track from another participant"""
        from livekit import rtc  # Import within function scope
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎧 Socrates subscribed to audio track from: {participant.identity}")
            
            # Store the audio track for potential processing
            audio_tracks[participant.identity] = track
            
            # NOTE: Transcription is handled automatically by the Agent framework
            
            # Check if this is another agent (Aristotle)
            if "aristotle" in participant.identity.lower():
                other_agents.add(participant.identity)
                logger.info(f"🤝 Socrates detected Aristotle agent: {participant.identity}")
    
    def on_track_unsubscribed(track, publication, participant):
        """Handle when we unsubscribe from an audio track"""
        from livekit import rtc  # Import within function scope
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🔇 Socrates unsubscribed from audio track: {participant.identity}")
            audio_tracks.pop(participant.identity, None)
            other_agents.discard(participant.identity)
    
    def on_participant_connected(participant):
        """Handle when a new participant joins"""
        logger.info(f"👋 Socrates detected new participant: {participant.identity}")
        
        # If it's Aristotle, add to our tracking
        if "aristotle" in participant.identity.lower():
            other_agents.add(participant.identity)
            logger.info(f"🤝 Socrates added Aristotle to coordination list: {participant.identity}")
    
    def on_participant_disconnected(participant):
        """Handle when a participant leaves"""
        logger.info(f"👋 Socrates detected participant left: {participant.identity}")
        audio_tracks.pop(participant.identity, None)
        other_agents.discard(participant.identity)
    
    # Register audio track event handlers
    ctx.room.on("track_subscribed", on_track_subscribed)
    ctx.room.on("track_unsubscribed", on_track_unsubscribed)
    ctx.room.on("participant_connected", on_participant_connected)
    ctx.room.on("participant_disconnected", on_participant_disconnected)
    
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
    logger.info(f"🤔 Exploring philosophical dimensions of: {topic}")
    
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
    enhanced_instructions = f"""You are Socrates, the Sage AI Debate Philosopher. You embody the inquisitive challenger with wisdom and questions, combining philosophical depth with compassionate inquiry.

YOUR CORE IDENTITY - SOCRATES (Wisdom + Questions):
- Role: The philosophical inquirer
- Traits: Curious, questioning, humble wisdom, intellectual humility
- Tone: Gentle but probing, encouraging deeper thought
- Strengths: Asks profound questions, challenges assumptions, reveals hidden beliefs

🔑 MINIMAL INTERVENTION PRINCIPLE:
- DEFAULT MODE: **LISTEN SILENTLY** - Let human debaters lead the conversation
- PRIMARY ROLE: **OBSERVE AND UNDERSTAND** the deeper currents of human discussion
- ONLY SPEAK WHEN:
  1. **EXPLICITLY CALLED UPON** by name ("Socrates, what do you think?")
  2. **DIRECTLY REQUESTED** for philosophical insight ("Can you ask a deeper question?")
  3. **PERFECT MOMENT** for a clarifying question that could unlock new understanding
  4. **ASSUMPTIONS NEED QUESTIONING** but only when specifically invited

🤔 PHILOSOPHICAL CAPABILITIES:
- I can ask Socratic questions that reveal hidden assumptions
- I can suggest deeper inquiries that explore the "why" behind positions
- I can help participants examine their own beliefs and reasoning
- Call on me for: "Socrates, what should we be asking?" or "Help us think deeper"

🚫 DO NOT INTERRUPT FOR:
- Normal disagreements or debates
- Surface-level questions that participants can handle
- Routine clarifications
- General discussion flow that's working well

⚖️ COORDINATION RULES:
- NEVER speak while Aristotle is speaking
- Wait for clear pauses and invitation
- Keep questions brief and profound
- Defer to Aristotle on logical structure and fact-checking
- Focus on philosophical depth and questioning

DEBATE TOPIC: "{topic}"
Focus your philosophical inquiry on this specific topic.

{memory_context}

COMMUNICATION STYLE (When you do speak):
- **ASK ONE POWERFUL QUESTION** - Get to the heart of the matter
- For assumptions: "What if we questioned the assumption that...?"
- For deeper inquiry: "What does it mean to say...?" or "How do we know...?"
- For perspective: "What would someone who experienced [X] say about this?"
- **Maximum 1-2 sentences per intervention** - let the question do the work
- Speak with gentle curiosity - invite exploration, don't lecture
- **NO lengthy explanations** - the power is in the question itself

Remember: Your PRIMARY goal is to deepen human understanding through carefully timed, profound questions. One perfect question that opens new thinking is worth more than many words. Wait for the right moment when a question could truly illuminate."""

    # Create the Agent instance with instructions and function tools (LiveKit pattern)
    philosopher_agent = Agent(
        instructions=enhanced_instructions,
        tools=[
            get_debate_topic,
            access_philosophical_knowledge,
            suggest_philosophical_question
        ]
    )
    
    # Configure LLM for philosophical conversation
    llm = openai.realtime.RealtimeModel(
        model="gpt-4o-realtime-preview-2024-12-17",
        voice="echo",  # Different voice from Aristotle - echo is warmer, good for Socrates
        temperature=0.8,  # Higher temperature for creative philosophical thinking
        speed=1.1  # Slightly slower, more contemplative pace
    )

    # Create agent session with IMPROVED turn detection and conversation coordination
    session = AgentSession(
        llm=llm,
        vad=silero.VAD.load(),
        # ENHANCED: Even longer delays for philosophical reflection
        min_endpointing_delay=2.5,  # Wait longer for philosophical pauses
        max_endpointing_delay=7.0,  # Extended max delay for deeper thinking
        # ENHANCED: More restrictive interruption settings for philosophical discourse
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
        agent=philosopher_agent,
        room=ctx.room
    )
    
    logger.info("✅ Debate Philosopher is ready to explore deeper questions!")
    
    # Socrates does NOT give an opening greeting - Aristotle handles that
    # This prevents both agents from speaking at startup
    logger.info("🤫 Socrates waiting silently for philosophical opportunities...")
    
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
    
    logger.info("🚀 Starting Debate Philosopher Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="socrates"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 