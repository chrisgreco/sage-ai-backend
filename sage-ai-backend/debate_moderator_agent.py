#!/usr/bin/env python3
"""
Aristotle Moderator Agent - The logical moderator with reason + structure
Provides analytical thinking, logical structure, and process facilitation
"""

import os
import sys
import asyncio
import logging
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

MODERATION RESPONSIBILITIES (Based on Aristotelian Logic + Deliberative Democracy Research):

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

4. PROCESS MANAGEMENT:
   - Keep discussions focused and productive using logical frameworks
   - Manage speaking time with structured approaches
   - Guide conversations using analytical methods
   - Balance structure with productive flexibility

5. SYNTHESIS & REASONING:
   - Identify logical connections between different viewpoints
   - Help participants see the rational structure of debates
   - Find common logical ground and shared premises
   - Summarize using analytical frameworks

COMMUNICATION STYLE:
- Ask clarifying questions about definitions and logic
- Use phrases like: "Let's examine the premises...", "What evidence supports this?", "How do these ideas connect logically?"
- Apply systematic analysis to complex topics
- Speak with measured authority and analytical precision
- Keep responses structured and well-reasoned

KNOWLEDGE ACCESS:
You have access to Aristotelian logic, practical ethics, and systematic analysis methods, plus parliamentary procedure and facilitation techniques.

Remember: Your goal is to facilitate productive dialogue through logical structure, clear reasoning, and analytical thinking while maintaining fairness and process integrity."""

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
        
        # Statistical claim triggers
        stat_indicators = ["percent", "%", "statistics", "data shows", "studies show", "research indicates", "according to"]
        if any(indicator in snippet_lower for indicator in stat_indicators):
            triggers_detected.append({"type": "statistical_claim", "action": "offer_fact_check"})
        
        # Direct request triggers  
        direct_requests = ["aristotle please", "aristotle can you", "fact check", "verify this", "is this true"]
        if any(request in snippet_lower for request in direct_requests):
            triggers_detected.append({"type": "direct_request", "action": "immediate_response"})
        
        # Logical fallacy triggers
        fallacy_indicators = ["always", "never", "everyone", "all", "obviously", "clearly false"]
        if any(indicator in snippet_lower for indicator in fallacy_indicators):
            triggers_detected.append({"type": "potential_fallacy", "action": "logical_analysis"})
        
        # Process breakdown triggers
        process_issues = ["off topic", "personal attack", "interrupt", "shouting", "unfair"]
        if any(issue in snippet_lower for issue in process_issues):
            triggers_detected.append({"type": "process_issue", "action": "moderate"})
        
        return {
            "triggers": triggers_detected,
            "should_intervene": len(triggers_detected) > 0,
            "priority": "high" if any(t["type"] == "direct_request" for t in triggers_detected) else "medium"
        }

async def entrypoint(ctx: JobContext):
    """Debate Moderator agent entrypoint"""
    
    logger.info("🏛️ Sage AI Debate Moderator joining the room...")
    await ctx.connect()
    logger.info(f"✅ Moderator connected to room: {ctx.room.name}")
    
    # Get debate topic
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    room_name = ctx.room.name
    logger.info(f"⚖️ Moderating discussion on: {topic}")
    
    # Initialize memory if available
    room_id = None
    memory_context = ""
    
    if SUPABASE_AVAILABLE:
        try:
            room_id = await create_or_get_debate_room(
                room_token=room_name,
                topic=topic,
                max_duration_hours=24
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
    
    # Create agent session
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="shimmer",
            temperature=0.6  # Slightly lower for more consistent moderation
        ),
        vad=silero.VAD.load(),
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
    )
    
    # Start session
    await session.start(
        agent=Agent(instructions=enhanced_instructions),
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