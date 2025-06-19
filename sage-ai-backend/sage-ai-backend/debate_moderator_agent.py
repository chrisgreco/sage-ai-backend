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

async def entrypoint(ctx: JobContext):
    """Debate Moderator agent entrypoint - only joins rooms marked for sage debates"""
    
    logger.info("🏛️ Sage AI Debate Moderator checking room metadata...")
    await ctx.connect()
    
    # Check if this room is meant for sage debates
    room_metadata = None
    try:
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            room_metadata = json.loads(ctx.room.metadata)
            logger.info(f"Room metadata: {room_metadata}")
    except Exception as e:
        logger.warning(f"Could not parse room metadata: {e}")
    
    # Only join rooms specifically marked for sage debates
    if room_metadata:
        room_type = room_metadata.get("room_type")
        agents_needed = room_metadata.get("agents_needed", [])
        
        if room_type != "sage_debate":
            logger.info(f"❌ Skipping room {ctx.room.name} - not a sage debate room (type: {room_type})")
            return
            
        if "aristotle" not in agents_needed:
            logger.info(f"❌ Skipping room {ctx.room.name} - Aristotle not needed in this debate")
            return
            
        logger.info(f"✅ Joining sage debate room: {ctx.room.name}")
        topic = room_metadata.get("debate_topic", "The impact of AI on society")
    else:
        # Fallback for rooms without metadata (development/testing)
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        logger.info(f"⚠️ No room metadata found, using environment topic: {topic}")
    
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
    
    # Create moderator agent
    moderator = DebateModeratorAgent()
    
    # Enhanced instructions with memory
    enhanced_instructions = moderator.instructions + memory_context
    
    # Create agent session with male voice
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="alloy",  # Male voice for Aristotle
            temperature=0.6  # Slightly lower for more consistent moderation
        ),
        vad=silero.VAD.load(),
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
    )
    
    # Enhanced instructions with opening announcement
    opening_instructions = enhanced_instructions + f"""

CRITICAL OPENING PROTOCOL:
When participants first join the room, immediately provide this opening announcement:

"Greetings, and welcome to this philosophical discourse. I am Aristotle, and I shall establish the framework for our debate.

Today's topic for examination: '{topic}'

Before we begin, let me establish two fundamental rules for our discourse:

First: Each participant should present evidence-based arguments and cite sources when possible.

Second: Maintain respectful discourse - challenge ideas, not individuals.

You may now begin your discussion. I will observe and provide guidance only when directly requested or when logical structure requires attention."

This opening should be spoken IMMEDIATELY when the first participant joins, before any human discussion begins."""
    
    # Start session
    await session.start(
        agent=Agent(instructions=opening_instructions),
        room=ctx.room
    )
    
    logger.info("✅ Debate Moderator is ready to facilitate productive discourse!")

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