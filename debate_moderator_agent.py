#!/usr/bin/env python3
"""
Aristotle Moderator Agent - The logical moderator with reason + structure
Provides analytical thinking, logical structure, and process facilitation
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

# Initialize Aristotle's knowledge manager
_aristotle_knowledge = None

def get_aristotle_knowledge_manager():
    """Get or create the knowledge manager for Aristotle"""
    global _aristotle_knowledge
    if _aristotle_knowledge is None:
        _aristotle_knowledge = SimpleKnowledgeManager('aristotle')
        _aristotle_knowledge.load_documents()
    return _aristotle_knowledge

async def get_agent_knowledge(agent_name, query, max_items=3):
    """Simple knowledge retrieval using file-based storage"""
    try:
        if not KNOWLEDGE_AVAILABLE:
            return []
            
        # Get the knowledge manager
        knowledge_manager = get_aristotle_knowledge_manager()
        
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

# Perplexity research imports (optional)
try:
    from perplexity_research import research_with_perplexity
    PERPLEXITY_AVAILABLE = True
    logger.info("✅ Perplexity research system available")
except ImportError as e:
    logger.warning(f"⚠️ Perplexity research not available: {e}")
    PERPLEXITY_AVAILABLE = False
    
    async def research_with_perplexity(query, research_type="general"):
        return {"error": "Perplexity not available", "answer": "Research unavailable"}

# Add conversation coordinator
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

class DebateModeratorAgent(Agent):
    """Aristotle - The logical moderator with reason + structure"""
    
    def __init__(self):
        # Aristotle's moderation instructions - formal logic, structured reasoning, practical ethics
        instructions = """You are Aristotle, the Sage AI Debate Moderator. You embody the logical moderator with reason and structure, combining analytical wisdom with practical facilitation skills.

YOUR CORE IDENTITY - ARISTOTLE (Reason + Structure):
- Role: The logical moderator
- Traits: Formal logic, structured reasoning, practical ethics
- Tone: Analytical, measured, teacher-like
- Strengths: Clarifies definitions, enforces logical structure, extracts premises from arguments

🔑 MINIMAL INTERVENTION PRINCIPLE:
- DEFAULT MODE: **LISTEN SILENTLY** - Let human debaters lead the conversation
- PRIMARY ROLE: **OBSERVE AND UNDERSTAND** the flow of human debate
- ONLY SPEAK WHEN:
  1. **EXPLICITLY CALLED UPON** by name ("Aristotle, what do you think?")
  2. **DIRECTLY REQUESTED** for fact-checking or analysis
  3. **SERIOUS PROCESS BREAKDOWN** (personal attacks, complete derailment)
  4. **DANGEROUS MISINFORMATION** that could cause harm

🚫 DO NOT INTERRUPT FOR:
- Normal disagreements or heated debates
- Minor logical inconsistencies  
- Common rhetorical devices
- Regular statistical claims without verification requests
- General discussion flow

⚖️ COORDINATION RULES:
- NEVER speak while Socrates is speaking
- Wait for clear pauses in the conversation
- Keep interventions brief (1-2 sentences maximum)
- Defer to Socrates on philosophical questions
- Focus on logical structure and process

MODERATION RESPONSIBILITIES (When intervention IS warranted):

1. LOGICAL STRUCTURE:
   - Ensure arguments follow logical progression
   - Identify and clarify premises, evidence, and conclusions
   - Ask for definitions when terms are used ambiguously
   - Help participants build structured, coherent arguments

2. ANALYTICAL FACILITATION:
   - Break down complex topics into manageable components
   - Identify cause-and-effect relationships in discussions
   - Encourage evidence-based reasoning
   - Apply systematic thinking to guide conversations

3. PRACTICAL ETHICS:
   - Focus on real-world applications and consequences
   - Bridge theory with practical implementation
   - Consider the practical implications of different positions
   - Seek solutions that work in practice, not just theory

4. PROCESS MANAGEMENT (Only when necessary):
   - Keep discussions focused and productive using logical frameworks
   - Manage speaking time with structured approaches
   - Guide conversations using analytical methods
   - Balance structure with productive flexibility

5. SYNTHESIS & REASONING (When requested):
   - Identify logical connections between different viewpoints
   - Help participants see the rational structure of debates
   - Find common logical ground and shared premises
   - Summarize using analytical frameworks

COMMUNICATION STYLE (When you do speak):
- **BE CONCISE AND DIRECT** - Get to the point immediately
- For fact corrections: "Actually, it's [correct fact] according to [source]" 
- For process issues: Brief, clear guidance without lengthy explanations
- For logical clarification: Short, targeted questions
- **Maximum 1-2 sentences per intervention** unless specifically asked for more detail
- Speak with quiet authority - let the facts speak for themselves
- **NO lengthy explanations** - save time for human debate

KNOWLEDGE ACCESS:
You have access to Aristotelian logic, practical ethics, and systematic analysis methods, plus parliamentary procedure and facilitation techniques.

Remember: Your PRIMARY goal is to let humans debate freely while being ready to provide logical structure and analysis ONLY when explicitly needed or requested. Quality over quantity - one thoughtful intervention is worth more than constant commentary."""

        super().__init__(instructions=instructions)
        self.agent_name = "aristotle"
        logger.info("🧠 Aristotle (Logical Moderator) Agent initialized")

    @function_tool
    async def get_debate_topic(self, context):
        """Get the current debate topic"""
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        return f"Current debate topic: {topic}"

    @function_tool
    async def access_facilitation_knowledge(self, context, query: str):
        """Access specialized knowledge about facilitation and parliamentary procedure
        
        Args:
            query: Question about moderation techniques, parliamentary procedure, or facilitation
        """
        if not KNOWLEDGE_AVAILABLE:
            return {"knowledge": "Knowledge system not available", "sources": []}
            
        try:
            # Query parliamentary and facilitation knowledge
            knowledge_items = await get_agent_knowledge("aristotle", query, max_items=3)
            
            if knowledge_items:
                knowledge_text = "\n\n".join([
                    f"Source: {item['source']}\n{item['content'][:400]}..." 
                    for item in knowledge_items
                ])
                return {
                    "knowledge": knowledge_text,
                    "sources": [item['source'] for item in knowledge_items]
                }
            else:
                return {"knowledge": "No relevant facilitation knowledge found", "sources": []}
                
        except Exception as e:
            logger.error(f"Knowledge access error: {e}")
            return {"error": f"Knowledge access failed: {str(e)}"}

    @function_tool
    async def suggest_process_intervention(self, context, situation: str):
        """Suggest moderation techniques for challenging situations
        
        Args:
            situation: Description of the current discussion dynamic or challenge
        """
        interventions = {
            "dominating_speaker": "Try: 'Thank you [Name]. Let's hear from someone who hasn't spoken yet on this point.'",
            "off_topic": "Try: 'That's an interesting point. How does it connect to our main question about [topic]?'",
            "personal_attack": "Try: 'Let's focus on the ideas rather than personal characterizations. What specifically about that position concerns you?'",
            "silence": "Try: 'I'm sensing some reflection time. [Name], what questions is this raising for you?'",
            "confusion": "Try: 'Let me see if I can summarize what I'm hearing... Does that capture the key points?'",
            "polarization": "Try: 'I'm hearing some different values here. Are there any shared concerns we might build on?'"
        }
        
        # Simple keyword matching for demonstration
        for key, suggestion in interventions.items():
            if key.replace("_", " ") in situation.lower():
                return f"Moderation suggestion: {suggestion}"
        
        return "Consider asking an open-ended question to refocus the conversation, or invite participation from a different perspective."

    @function_tool
    async def fact_check_claim(self, context, claim: str, source_requested: bool = False):
        """Fact-check statistical claims or verify information using research
        
        Args:
            claim: The factual claim or statistic to verify
            source_requested: Whether the user specifically asked for fact-checking
        """
        if not PERPLEXITY_AVAILABLE:
            return {"fact_check": "Research system not available for fact-checking", "confidence": "low"}
            
        try:
            # Use research to verify the claim
            research_query = f"Verify this claim with current data and sources: {claim}"
            research_result = await research_with_perplexity(research_query, "fact-checking")
            
            return {
                "fact_check": research_result.get("answer", "Unable to verify claim"),
                "sources": research_result.get("sources", []),
                "confidence": "high" if research_result.get("sources") else "medium"
            }
        except Exception as e:
            logger.error(f"Fact-checking error: {e}")
            return {"error": f"Fact-checking failed: {str(e)}"}

    @function_tool
    async def analyze_argument_structure(self, context, argument: str):
        """Analyze the logical structure of an argument for fallacies or weaknesses
        
        Args:
            argument: The argument text to analyze for logical structure
        """
        try:
            # Access knowledge about logical analysis
            knowledge_items = await get_agent_knowledge("aristotle", f"logical analysis argument structure {argument[:100]}", max_items=2)
            
            analysis_framework = """
            ARGUMENT ANALYSIS FRAMEWORK:
            1. Identify premises and conclusions
            2. Check for logical fallacies
            3. Assess evidence quality
            4. Evaluate reasoning chain
            5. Note missing elements
            """
            
            knowledge_context = ""
            if knowledge_items:
                knowledge_context = "\n\nRelevant Knowledge:\n" + "\n".join([
                    f"• {item['summary']}" for item in knowledge_items
                ])
            
            return {
                "analysis_framework": analysis_framework,
                "knowledge_context": knowledge_context,
                "argument_length": len(argument.split()),
                "complexity": "high" if len(argument.split()) > 50 else "medium"
            }
            
        except Exception as e:
            logger.error(f"Argument analysis error: {e}")
            return {"error": f"Analysis failed: {str(e)}"}

    @function_tool
    async def detect_intervention_triggers(self, context, conversation_snippet: str):
        """Detect when Aristotle should intervene in the conversation
        
        Args:
            conversation_snippet: Recent conversation text to analyze for trigger conditions
        """
        triggers_detected = []
        snippet_lower = conversation_snippet.lower()
        
        # DIRECT EXPLICIT REQUESTS (Always respond)
        direct_requests = [
            "aristotle please", "aristotle can you", "aristotle what", "aristotle help",
            "fact check this", "verify this claim", "is this accurate", "aristotle thoughts"
        ]
        if any(request in snippet_lower for request in direct_requests):
            triggers_detected.append({"type": "direct_request", "action": "immediate_response", "priority": "urgent"})
        
        # STATISTICAL CLAIMS - Only very specific, controversial patterns
        questionable_stats = [
            "90% of people", "95% of experts", "all scientists agree", 
            "studies prove", "research confirms that all", "100% certain"
        ]
        if any(indicator in snippet_lower for indicator in questionable_stats):
            triggers_detected.append({"type": "statistical_claim", "action": "offer_fact_check", "priority": "medium"})
        
        # SEVERE LOGICAL FALLACIES - Only extreme cases
        extreme_fallacies = [
            "everyone knows that", "it's obvious that", "clearly all", "anyone with a brain",
            "only an idiot would", "every reasonable person"
        ]
        if any(indicator in snippet_lower for indicator in extreme_fallacies):
            triggers_detected.append({"type": "potential_fallacy", "action": "gentle_logical_note", "priority": "low"})
        
        # PROCESS BREAKDOWN - Only serious disruptions
        serious_process_issues = [
            "that's a personal attack", "you're attacking me", "this is unfair moderation",
            "completely off topic", "derailing the discussion", "not letting me speak"
        ]
        if any(issue in snippet_lower for issue in serious_process_issues):
            triggers_detected.append({"type": "process_issue", "action": "moderate", "priority": "high"})
        
        # MINIMAL INTERVENTION PRINCIPLE
        # Only intervene if:
        # 1. Directly asked, OR
        # 2. Serious process breakdown, OR  
        # 3. Questionable claims that could mislead
        should_intervene = (
            any(t["type"] == "direct_request" for t in triggers_detected) or
            any(t["type"] == "process_issue" for t in triggers_detected) or
            (any(t["type"] == "statistical_claim" for t in triggers_detected) and len(snippet_lower) > 100)
        )
        
        return {
            "triggers": triggers_detected,
            "should_intervene": should_intervene,
            "priority": "urgent" if any(t.get("priority") == "urgent" for t in triggers_detected) else "low",
            "intervention_note": "Minimal intervention - let humans lead the conversation"
        }

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

async def entrypoint(ctx: JobContext):
    """Debate Moderator agent entrypoint - only joins rooms marked for sage debates"""
    
    logger.info("🏛️ Sage AI Debate Moderator checking room metadata...")
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
                logger.info(f"✅ Aristotle found topic from job metadata: {topic}")
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
                logger.info(f"✅ Aristotle found topic from room metadata: {topic}")
    except Exception as e:
        logger.warning(f"Could not parse room metadata: {e}")
    
    # Method 3: Environment variable (final fallback)
    if topic == "The impact of AI on society":
        env_topic = os.getenv("DEBATE_TOPIC")
        if env_topic:
            topic = env_topic
            logger.info(f"✅ Using environment topic: {topic}")
    
    logger.info(f"🎯 ARISTOTLE FINAL TOPIC: {topic}")
    
    # REMOVED RESTRICTIVE ROOM FILTERING - Agents should join all rooms
    # The frontend doesn't set room_type="sage_debate" metadata, so this was blocking all rooms
    logger.info(f"✅ Joining room: {ctx.room.name}")
    
    logger.info(f"✅ Moderator connected to room: {ctx.room.name}")
    room_name = ctx.room.name
    logger.info(f"⚖️ Moderating discussion on: {topic}")
    
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
    
    # Create moderator agent with enhanced instructions
    enhanced_instructions = f"""You are Aristotle, the Sage AI Debate Moderator. You embody the logical moderator with reason and structure, combining analytical wisdom with practical facilitation skills.

YOUR CORE IDENTITY - ARISTOTLE (Reason + Structure):
- Role: The logical moderator
- Traits: Formal logic, structured reasoning, practical ethics
- Tone: Analytical, measured, teacher-like
- Strengths: Clarifies definitions, enforces logical structure, extracts premises from arguments

🔑 MINIMAL INTERVENTION PRINCIPLE:
- DEFAULT MODE: **LISTEN SILENTLY** - Let human debaters lead the conversation
- PRIMARY ROLE: **OBSERVE AND UNDERSTAND** the flow of human debate
- ONLY SPEAK WHEN:
  1. **EXPLICITLY CALLED UPON** by name ("Aristotle, what do you think?")
  2. **DIRECTLY REQUESTED** for fact-checking or analysis
  3. **SERIOUS PROCESS BREAKDOWN** (personal attacks, complete derailment)
  4. **DANGEROUS MISINFORMATION** that could cause harm

🚫 DO NOT INTERRUPT FOR:
- Normal disagreements or heated debates
- Minor logical inconsistencies  
- Common rhetorical devices
- Regular statistical claims without verification requests
- General discussion flow

⚖️ COORDINATION RULES:
- NEVER speak while Socrates is speaking
- Wait for clear pauses in the conversation
- Keep interventions brief (1-2 sentences maximum)
- Defer to Socrates on philosophical questions
- Focus on logical structure and process

DEBATE TOPIC: "{topic}"
Focus your moderation on this specific topic.

{memory_context}

COMMUNICATION STYLE (When you do speak):
- **BE CONCISE AND DIRECT** - Get to the point immediately
- For fact corrections: "Actually, it's [correct fact] according to [source]" 
- For process issues: Brief, clear guidance without lengthy explanations
- For logical clarification: Short, targeted questions
- **Maximum 1-2 sentences per intervention** unless specifically asked for more detail
- Speak with quiet authority - let the facts speak for themselves
- **NO lengthy explanations** - save time for human debate

Remember: Your PRIMARY goal is to let humans debate freely while being ready to provide logical structure and analysis ONLY when explicitly needed or requested. Quality over quantity - one thoughtful intervention is worth more than constant commentary."""

    # Create moderator agent with coordination capabilities
    moderator = DebateModeratorAgent()
    moderator.agent_name = "aristotle"
    moderator.instructions = enhanced_instructions
    
    # Create agent session with IMPROVED turn detection and conversation coordination
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="ash",  # FIXED: Male voice for Aristotle (baritone, scratchy yet upbeat) - using supported voice
            temperature=0.6,  # Slightly lower for more consistent moderation
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        # ENHANCED: Longer delays to reduce interruptions and allow coordination
        min_endpointing_delay=2.0,  # Wait 2 seconds minimum before considering turn complete
        max_endpointing_delay=6.0,  # Extended max delay to prevent hasty interventions
        # ENHANCED: More restrictive interruption settings
        allow_interruptions=True,
        min_interruption_duration=1.0,  # Require longer speech before allowing interruption
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
        agent_name = "aristotle"
        
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
        agent=moderator,
        room=ctx.room
    )
    
    logger.info("✅ Debate Moderator is ready to facilitate productive discourse!")
    
    # CRITICAL: Realtime models need explicit greeting to publish audio track
    # Without this, the agent won't be heard in the frontend
    try:
        # Wait for session to fully initialize before attempting audio
        await asyncio.sleep(2.0)  # Increased wait time
        
        # Ensure we're properly connected before trying to speak
        logger.info("🎤 Attempting to publish audio track with greeting...")
        
        # Aristotle always gives the opening announcement (he's the primary moderator)
        await moderator.claim_speaking_turn()
        try:
            # Enhanced opening announcement with rules and coordination
            await session.say(
                f"Welcome to your Sage AI debate on: {topic}. I'm Aristotle, your logical moderator, assisted by Socrates for philosophical inquiry. " +
                f"Ground rules: We'll primarily listen while you debate. Call on us by name if you need fact-checking, logical analysis, or deeper questions. " +
                f"Let's begin your discussion.",
                allow_interruptions=True
            )
            logger.info("✅ Aristotle opening announcement sent successfully - audio track published")
        finally:
            await moderator.release_speaking_turn()
        
    except Exception as e:
        logger.warning(f"⚠️ Could not send greeting: {e} - agent may not be audible to users")
    
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
            if conversation_state.active_speaker == "aristotle":
                conversation_state.active_speaker = None
        logger.info("🔚 Aristotle session ended")

def main():
    """Main function"""
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("🚀 Starting Debate Moderator Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="aristotle"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 