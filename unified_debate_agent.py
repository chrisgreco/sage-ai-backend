#!/usr/bin/env python3
"""
Unified Sage AI Debate Agent - Dual Persona System
Handles both Aristotle (logical moderator) and Socrates (philosophical questioner) in one worker
"""

import os
import sys
import asyncio
import logging
import json
import time
import random
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Dict, List

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

# Perplexity research via LiveKit integration (optional)
try:
    from livekit.plugins import openai
    PERPLEXITY_AVAILABLE = True
    logger.info("✅ Perplexity research system available via LiveKit")
except ImportError as e:
    logger.warning(f"⚠️ Perplexity research not available: {e}")
    PERPLEXITY_AVAILABLE = False

@dataclass
class PersonaState:
    """State for individual personas"""
    name: str
    active: bool = False
    last_spoke_time: float = 0
    intervention_count: int = 0
    knowledge_manager: Optional[SimpleKnowledgeManager] = None

@dataclass
class UnifiedAgentState:
    """Unified state for dual-persona agent"""
    current_persona: Optional[str] = None  # "aristotle" or "socrates"
    user_speaking: bool = False
    last_intervention_time: float = 0
    total_interventions: int = 0
    personas: Dict[str, PersonaState] = None
    
    def __post_init__(self):
        if self.personas is None:
            self.personas = {
                "aristotle": PersonaState("aristotle"),
                "socrates": PersonaState("socrates")
            }

# Global unified state
unified_state = UnifiedAgentState()

# Initialize knowledge managers for both personas
def initialize_knowledge_managers():
    """Initialize knowledge managers for both personas"""
    if not KNOWLEDGE_AVAILABLE:
        return
        
    try:
        # Aristotle knowledge manager
        aristotle_km = SimpleKnowledgeManager('aristotle')
        aristotle_km.load_documents()
        unified_state.personas["aristotle"].knowledge_manager = aristotle_km
        logger.info("✅ Aristotle knowledge manager initialized")
        
        # Socrates knowledge manager  
        socrates_km = SimpleKnowledgeManager('socrates')
        socrates_km.load_documents()
        unified_state.personas["socrates"].knowledge_manager = socrates_km
        logger.info("✅ Socrates knowledge manager initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize knowledge managers: {e}")

async def get_persona_knowledge(persona_name: str, query: str, max_items: int = 3) -> List[Dict]:
    """Get knowledge for specific persona"""
    if not KNOWLEDGE_AVAILABLE:
        return []
        
    try:
        persona = unified_state.personas.get(persona_name)
        if not persona or not persona.knowledge_manager:
            return []
            
        if not persona.knowledge_manager.is_ready():
            logger.warning(f"📚 Knowledge manager not ready for {persona_name}")
            return []
        
        results = persona.knowledge_manager.search_knowledge(query, max_results=max_items)
        
        if results:
            logger.debug(f"📚 Retrieved {len(results)} knowledge items for {persona_name}")
            return [
                {
                    'content': result['content'],
                    'source': result['title'],
                    'relevance': result['relevance_score']
                }
                for result in results
            ]
        else:
            logger.debug(f"🔍 No relevant knowledge found for {persona_name}")
            return []
        
    except Exception as e:
        logger.error(f"Error in knowledge retrieval for {persona_name}: {e}")
        return []

def determine_active_persona(user_message: str, conversation_context: str = "") -> str:
    """Determine which persona should respond based on context and keywords"""
    message_lower = user_message.lower()
    
    # Direct persona calls
    if "aristotle" in message_lower:
        return "aristotle"
    if "socrates" in message_lower:
        return "socrates"
    
    # Keyword-based persona selection
    aristotle_keywords = [
        "fact", "research", "data", "statistic", "source", "evidence", 
        "logical", "structure", "organize", "moderate", "process",
        "parliamentary", "procedure", "rules", "order"
    ]
    
    socrates_keywords = [
        "why", "what if", "assume", "belief", "meaning", "define",
        "question", "examine", "explore", "deeper", "philosophy",
        "truth", "wisdom", "understanding", "assumption"
    ]
    
    aristotle_score = sum(1 for keyword in aristotle_keywords if keyword in message_lower)
    socrates_score = sum(1 for keyword in socrates_keywords if keyword in message_lower)
    
    # If clear preference, use it
    if aristotle_score > socrates_score + 1:
        return "aristotle"
    elif socrates_score > aristotle_score + 1:
        return "socrates"
    
    # Default rotation based on recent activity
    current_time = time.time()
    aristotle_persona = unified_state.personas["aristotle"]
    socrates_persona = unified_state.personas["socrates"]
    
    # Prefer the persona that spoke less recently
    if aristotle_persona.last_spoke_time < socrates_persona.last_spoke_time:
        return "aristotle"
    else:
        return "socrates"

def should_intervene(persona_name: str, conversation_context: str) -> bool:
    """Determine if persona should intervene in conversation"""
    current_time = time.time()
    
    # Don't speak if user is speaking
    if unified_state.user_speaking:
        return False
    
    # Don't speak if other persona is active
    if unified_state.current_persona and unified_state.current_persona != persona_name:
        return False
    
    # Rate limiting: minimum 8 seconds between any interventions
    if current_time - unified_state.last_intervention_time < 8.0:
        return False
    
    # Escalating delay: wait longer after each intervention
    min_delay = 8.0 + (unified_state.total_interventions * 2.0)
    if current_time - unified_state.last_intervention_time < min_delay:
        return False
    
    return True

def claim_speaking_turn(persona_name: str):
    """Claim speaking turn for specific persona"""
    current_time = time.time()
    unified_state.current_persona = persona_name
    unified_state.last_intervention_time = current_time
    unified_state.total_interventions += 1
    unified_state.personas[persona_name].last_spoke_time = current_time
    unified_state.personas[persona_name].intervention_count += 1
    logger.info(f"🎤 {persona_name.capitalize()} claimed speaking turn")

def release_speaking_turn():
    """Release speaking turn"""
    if unified_state.current_persona:
        logger.info(f"🔇 {unified_state.current_persona.capitalize()} released speaking turn")
        unified_state.current_persona = None

# Function tools for Aristotle persona
@function_tool
async def aristotle_fact_check(context, claim: str):
    """Aristotle's fact-checking using Perplexity research"""
    if not PERPLEXITY_AVAILABLE:
        return {"fact_check": "Research system not available", "confidence": "low"}
        
    try:
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY required")
        
        perplexity_llm = openai.LLM.with_perplexity(
            model="sonar",
            temperature=0.2,
            api_key=api_key
        )
        
        research_prompt = f"""As Aristotle, fact-check this claim with maximum brevity:

CLAIM: {claim}

Provide ONLY:
1. Direct correction in 1-2 sentences maximum
2. Accurate fact/statistic with current data
3. Authoritative source

Format: "Actually, [correct fact] according to [source]."

BE EXTREMELY CONCISE."""

        from livekit.agents.llm import ChatContext
        chat_ctx = ChatContext()
        chat_ctx.add_message(role="user", content=research_prompt)
        
        stream = perplexity_llm.chat(chat_ctx=chat_ctx)
        response_chunks = []
        async for chunk in stream:
            if hasattr(chunk, 'delta') and chunk.delta and chunk.delta.content:
                response_chunks.append(chunk.delta.content)
        
        fact_check_result = ''.join(response_chunks) if response_chunks else "Unable to verify claim"
        
        return {
            "fact_check": fact_check_result,
            "confidence": "high",
            "source": "Perplexity AI with current data"
        }
        
    except Exception as e:
        logger.error(f"Fact-checking error: {e}")
        return {"error": f"Fact-checking failed: {str(e)}"}

@function_tool
async def aristotle_research(context, query: str):
    """Aristotle's live research capabilities"""
    if not PERPLEXITY_AVAILABLE:
        return {"research": "Research system not available", "confidence": "low"}
        
    try:
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY required")
        
        perplexity_llm = openai.LLM.with_perplexity(
            model="sonar",
            temperature=0.3,
            api_key=api_key
        )
        
        research_prompt = f"""Provide current, comprehensive information on: {query}

Include:
1. Key facts and current data
2. Multiple authoritative sources
3. Recent developments if relevant

BE FACTUAL and well-sourced."""
        
        from livekit.agents.llm import ChatContext
        chat_ctx = ChatContext()
        chat_ctx.add_message(role="user", content=research_prompt)
        
        stream = perplexity_llm.chat(chat_ctx=chat_ctx)
        response_chunks = []
        async for chunk in stream:
            if hasattr(chunk, 'delta') and chunk.delta and chunk.delta.content:
                response_chunks.append(chunk.delta.content)
        
        research_result = ''.join(response_chunks) if response_chunks else "No research results available"
        
        return {
            "research": research_result,
            "confidence": "high",
            "source": "Perplexity AI with current data"
        }
        
    except Exception as e:
        logger.error(f"Research error: {e}")
        return {"error": f"Research failed: {str(e)}"}

@function_tool
async def aristotle_knowledge_access(context, query: str):
    """Access Aristotle's specialized knowledge"""
    knowledge_items = await get_persona_knowledge("aristotle", query, max_items=3)
    
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

@function_tool
async def socrates_knowledge_access(context, query: str):
    """Access Socrates' philosophical knowledge"""
    knowledge_items = await get_persona_knowledge("socrates", query, max_items=3)
    
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
        return {"knowledge": "No relevant philosophical knowledge found", "sources": []}

@function_tool
async def get_debate_topic(context):
    """Get the current debate topic"""
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    return f"Current debate topic: {topic}"

async def entrypoint(ctx: JobContext):
    """Unified Sage AI Debate Agent entrypoint"""
    
    logger.info("🏛️🤔 Unified Sage AI Debate Agent starting...")
    await ctx.connect()
    
    # Initialize knowledge managers
    initialize_knowledge_managers()
    
    # Enhanced topic detection
    topic = "The impact of AI on society"  # Default fallback
    
    # Method 1: Check job metadata
    try:
        if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            logger.info(f"📋 Found job metadata: {ctx.job.metadata}")
            job_metadata = json.loads(ctx.job.metadata)
            job_topic = job_metadata.get("debate_topic")
            if job_topic:
                topic = job_topic
                logger.info(f"✅ Found topic from job metadata: {topic}")
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"❌ Failed to parse job metadata: {e}")
    
    # Method 2: Check room metadata
    try:
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            room_metadata = json.loads(ctx.room.metadata)
            logger.info(f"🏠 Found room metadata: {room_metadata}")
            room_topic = room_metadata.get("debate_topic")
            if room_topic and topic == "The impact of AI on society":
                topic = room_topic
                logger.info(f"✅ Found topic from room metadata: {topic}")
    except Exception as e:
        logger.warning(f"Could not parse room metadata: {e}")
    
    # Method 3: Environment variable
    if topic == "The impact of AI on society":
        env_topic = os.getenv("DEBATE_TOPIC")
        if env_topic:
            topic = env_topic
            logger.info(f"✅ Using environment topic: {topic}")
    
    logger.info(f"🎯 UNIFIED AGENT TOPIC: {topic}")
    logger.info(f"✅ Joining room: {ctx.room.name}")
    
    room_name = ctx.room.name
    logger.info(f"🏛️🤔 Both Aristotle and Socrates ready for: {topic}")
    
    # Initialize memory if available
    room_id = None
    memory_context = ""
    
    if SUPABASE_AVAILABLE:
        try:
            room_id = await create_or_get_debate_room(
                room_name=room_name,
                debate_topic=topic,
                livekit_token=room_name
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
    
    # Create unified instructions that handle both personas
    unified_instructions = f"""You are the Unified Sage AI Debate Agent, embodying BOTH Aristotle and Socrates in a single system. You dynamically switch between these two personas based on context and need.

🏛️ ARISTOTLE (Logical Moderator) - Use when:
- Fact-checking or research is requested
- Statistical claims need verification  
- Process moderation is needed
- Logical structure is required
- Parliamentary procedure questions arise

ARISTOTLE'S TRAITS:
- Analytical, measured, teacher-like
- Focuses on logical structure and evidence
- Uses live research capabilities via Perplexity AI
- Provides fact-checking with current data
- Enforces process and structure

🤔 SOCRATES (Philosophical Questioner) - Use when:
- Deeper philosophical exploration is needed
- Assumptions should be examined
- Questions would deepen understanding
- Wisdom and reflection are called for
- Definitional clarity is needed

SOCRATES' TRAITS:
- Curious, humble, question-focused
- Uses Socratic method of inquiry
- Challenges assumptions gently
- Seeks deeper meaning and truth
- Models intellectual humility

🔑 UNIFIED INTERVENTION PRINCIPLES:
- **PRIMARY MODE: LISTEN SILENTLY** - Let humans lead
- **ONLY SPEAK WHEN:**
  1. Explicitly called by name ("Aristotle" or "Socrates")
  2. Fact-checking/research directly requested
  3. Philosophical depth would benefit discussion
  4. Serious process breakdown occurs

🎭 PERSONA SELECTION LOGIC:
- Direct calls: Respond as the named persona
- Research/facts: Use Aristotle
- Questions/philosophy: Use Socrates  
- Ambiguous: Alternate based on recent activity

DEBATE TOPIC: "{topic}"

{memory_context}

COMMUNICATION STYLE:
- **IDENTIFY YOUR PERSONA**: Start with "As Aristotle..." or "As Socrates..."
- **BE EXTREMELY CONCISE**: 1-2 sentences maximum unless asked for detail
- **STAY IN CHARACTER**: Maintain distinct persona traits
- **COORDINATE INTERNALLY**: Don't switch personas mid-response

🎭 VOICE & SPEAKING PATTERNS:
- **ARISTOTLE**: Speak with measured authority, clear diction, structured delivery
  - Use declarative statements: "The data shows..." "According to research..."
  - Pause for emphasis before key facts
  - Speak at moderate pace with logical flow
- **SOCRATES**: Speak with gentle curiosity, rising intonation for questions
  - Use questioning tone: "I wonder if..." "What might happen if..."
  - Slightly faster pace, more conversational rhythm
  - Natural pauses that invite reflection

Remember: You are ONE agent with TWO personas. The voice characteristics are set for the session, but use distinct speaking patterns, pace, and intonation to differentiate the personas. Always identify which persona is speaking."""

    # Create unified agent with all tools
    unified_agent = Agent(
        instructions=unified_instructions,
        tools=[
            get_debate_topic,
            aristotle_fact_check,
            aristotle_research,
            aristotle_knowledge_access,
            socrates_knowledge_access
        ]
    )
    
    # Configure LLM - use Perplexity when available for research capabilities
    if PERPLEXITY_AVAILABLE:
        try:
            research_llm = openai.LLM.with_perplexity(
                model="sonar",
                temperature=0.7  # Balanced for both personas
            )
            logger.info("✅ Using Perplexity LLM for unified agent")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity, using realtime model: {e}")
            # ENHANCED: Intelligent voice selection for personas
            # Choose voice based on expected primary persona or room metadata
            primary_persona = "aristotle"  # Default to Aristotle for logical moderation
            
            # Check if room metadata suggests a primary persona preference
            try:
                if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
                    room_metadata = json.loads(ctx.room.metadata)
                    preferred_persona = room_metadata.get("primary_persona", "aristotle")
                    if preferred_persona in ["aristotle", "socrates"]:
                        primary_persona = preferred_persona
            except:
                pass
            
            # Voice mapping for personas
            voice_mapping = {
                "aristotle": "ash",     # Deeper, more authoritative voice for logical moderator
                "socrates": "echo"      # Warmer, more questioning voice for philosopher
            }
            
            selected_voice = voice_mapping.get(primary_persona, "ash")
            logger.info(f"🎭 Selected voice '{selected_voice}' for primary persona: {primary_persona}")
            
            research_llm = openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview-2024-12-17",
                voice=selected_voice,
                temperature=0.7,
                speed=1.2
            )
    else:
        # ENHANCED: Same intelligent voice selection for non-Perplexity mode
        primary_persona = "aristotle"
        
        # Check room metadata for persona preference
        try:
            if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
                room_metadata = json.loads(ctx.room.metadata)
                preferred_persona = room_metadata.get("primary_persona", "aristotle")
                if preferred_persona in ["aristotle", "socrates"]:
                    primary_persona = preferred_persona
        except:
            pass
        
        voice_mapping = {
            "aristotle": "ash",     # Deeper, more authoritative
            "socrates": "echo"      # Warmer, more questioning
        }
        
        selected_voice = voice_mapping.get(primary_persona, "ash")
        logger.info(f"🎭 Selected voice '{selected_voice}' for primary persona: {primary_persona}")
        
        research_llm = openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=selected_voice,
            temperature=0.7,
            speed=1.2
        )

    # Create unified session
    session = AgentSession(
        llm=research_llm,
        vad=silero.VAD.load(),
        min_endpointing_delay=2.0,
        max_endpointing_delay=6.0,
        allow_interruptions=True,
        min_interruption_duration=1.0,
    )
    
    # Set up event handlers
    def on_user_state_changed(ev: UserStateChangedEvent):
        """Monitor user speaking state"""
        if ev.new_state == "speaking":
            unified_state.user_speaking = True
            if unified_state.current_persona:
                logger.info("👤 User started speaking - agent should yield")
                release_speaking_turn()
        elif ev.new_state == "listening":
            unified_state.user_speaking = False
            logger.info("👂 User stopped speaking - agent may respond if appropriate")

    def on_agent_state_changed(ev: AgentStateChangedEvent):
        """Monitor agent speaking state"""
        if ev.new_state == "speaking":
            logger.info(f"🎤 Unified agent started speaking")
        elif ev.new_state in ["idle", "listening", "thinking"]:
            if unified_state.current_persona:
                logger.info(f"🔇 Unified agent finished speaking")
                release_speaking_turn()

    session.on("user_state_changed", on_user_state_changed)
    session.on("agent_state_changed", on_agent_state_changed)
    
    # Start session
    await session.start(
        agent=unified_agent,
        room=ctx.room
    )
    
    logger.info("✅ Unified Sage AI Debate Agent is ready!")
    
    # Single greeting from unified agent
    try:
        await asyncio.sleep(2.0)
        logger.info("🎤 Publishing audio track with unified greeting...")
        
        await session.say(
            f"Welcome to your Sage AI debate on: {topic}. I embody both Aristotle, your logical moderator with live research capabilities, and Socrates, your philosophical questioner. " +
            f"I'll primarily listen while you debate. Call on 'Aristotle' for fact-checking and research, or 'Socrates' for deeper questions and philosophical exploration. " +
            f"Let's begin your discussion.",
            allow_interruptions=True
        )
        logger.info("✅ Unified greeting sent successfully - single audio track published")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not send greeting: {e}")
    
    # Keep session alive
    try:
        logger.info("🔄 Starting unified session monitoring...")
        
        while True:
            try:
                if not session.agent_state or session.agent_state == "disconnected":
                    logger.warning("⚠️ Unified agent session disconnected")
                    break
                
                await asyncio.wait_for(session.wait_for_completion(), timeout=300.0)
                break
                
            except asyncio.TimeoutError:
                logger.info("🔄 Session timeout reached, checking connection...")
                continue
            except Exception as inner_e:
                logger.warning(f"⚠️ Session monitoring error: {inner_e}")
                await asyncio.sleep(1.0)
                continue
                
    except Exception as e:
        logger.error(f"❌ Unified agent session error: {e}")
    finally:
        release_speaking_turn()
        logger.info("🔚 Unified Sage AI Debate Agent session ended")

def main():
    """Main function"""
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("🚀 Starting Unified Sage AI Debate Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="sage-unified"
        )
    )

if __name__ == "__main__":
    main() 