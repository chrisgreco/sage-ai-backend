#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Minimal LiveKit Implementation
Based on Context7 LiveKit documentation patterns
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional

# Core LiveKit imports (based on Context7 docs)
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import openai, silero, deepgram

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebateModerator:
    """Minimal Debate Moderator following LiveKit patterns"""
    
    def __init__(self):
        self.current_topic = None
        self.participants = []
        self.debate_phase = "opening"

    @function_tool
    async def set_debate_topic(
        self,
        context: RunContext,
        topic: str,
        context_info: Optional[str] = None
    ) -> str:
        """Set the debate topic"""
        self.current_topic = topic
        response = f"Debate topic set: '{topic}'"
        if context_info:
            response += f"\n\nContext: {context_info}"
        return response

    @function_tool
    async def moderate_discussion(
        self,
        context: RunContext,
        action: str,
        participant: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        """Moderate the discussion flow"""
        valid_actions = ["give_floor", "request_clarification", "summarize_points", "transition_topic"]
        
        if action not in valid_actions:
            return f"Invalid action. Valid actions: {', '.join(valid_actions)}"
        
        if action == "give_floor":
            return f"The floor is now given to {participant or 'the next speaker'}."
        elif action == "request_clarification":
            return f"Could {participant or 'the speaker'} please clarify their position?"
        elif action == "summarize_points":
            return "Let me summarize the key points made so far in this discussion."
        elif action == "transition_topic":
            return "Let's transition to the next aspect of this topic."

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        statement: str,
        speaker: Optional[str] = None
    ) -> str:
        """Fact-check a statement using Perplexity via LiveKit LLM"""
        try:
            fact_check_prompt = f"""
            Fact-check this statement briefly: "{statement}"
            Respond in under 15 words with format: "According to [source], [fact]" or "That's correct."
            """
            
            # Use the session's LLM (configured with Perplexity)
            response = await context.llm.agenerate(fact_check_prompt)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Fact-check error: {e}")
            return "Unable to verify that right now."

def get_persona_instructions(persona: str = "Aristotle") -> str:
    """Get persona-specific instructions"""
    personas = {
        "Aristotle": """You are Aristotle, the ancient Greek philosopher and master of debate moderation.
        
        Your role is to facilitate thoughtful, structured debates using your expertise in:
        - Logical reasoning and rhetoric
        - Identifying fallacies and weak arguments  
        - Ensuring balanced participation
        - Maintaining civil discourse
        - Asking probing questions to deepen understanding
        
        Use your function tools to:
        - Set debate topics with proper context
        - Moderate discussion flow and give speaking turns
        - Fact-check claims when needed
        - Guide transitions between topics
        
        Speak with wisdom and authority, but remain encouraging and supportive of all participants.
        Keep responses concise but substantive."""
    }
    return personas.get(persona, personas["Aristotle"])

async def entrypoint(ctx: JobContext):
    """Main entrypoint following Context7 LiveKit patterns"""
    
    # Connect to room first
    await ctx.connect()
    logger.info("Connected to LiveKit room")
    
    # Initialize moderator
    moderator = DebateModerator()
    
    # Get persona instructions
    persona = os.getenv("MODERATOR_PERSONA", "Aristotle")
    instructions = get_persona_instructions(persona)
    
    # Create agent with tools
    agent = Agent(
        instructions=instructions,
        tools=[
            moderator.set_debate_topic,
            moderator.moderate_discussion,
            moderator.fact_check_statement,
        ],
    )
    
    # Verify API keys
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not perplexity_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    logger.info("API keys verified")
    
    # Configure LLM with Perplexity (following Context7 docs)
    try:
        perplexity_model = os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-small-128k-online")
        llm = openai.LLM.with_perplexity(
            model=perplexity_model,
            api_key=perplexity_key,
            temperature=0.7
        )
        logger.info(f"Perplexity LLM configured: {perplexity_model}")
        
        # Test connection
        test_response = await llm.chat([{"role": "user", "content": "Hello"}])
        if test_response:
            logger.info("Perplexity API connection successful")
        
    except Exception as e:
        logger.error(f"Perplexity LLM setup failed: {e}")
        raise
    
    # Configure TTS with OpenAI
    try:
        tts = openai.TTS(
            voice="alloy",
            api_key=openai_key,
        )
        logger.info("OpenAI TTS configured")
    except Exception as e:
        logger.error(f"OpenAI TTS setup failed: {e}")
        raise
    
    # Create session with all components
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2"),
        llm=llm,
        tts=tts,
    )
    
    # Start the session
    try:
        await session.start(agent=agent, room=ctx.room)
        logger.info("Agent session started successfully")
        
        # Generate initial greeting
        greeting = f"Greetings! I am {persona}, your debate moderator. I'm here to facilitate a thoughtful and structured discussion. What topic would you like to explore today?"
        await session.generate_reply(instructions=greeting)
        logger.info("Initial greeting sent")
        
    except Exception as e:
        logger.error(f"Session start failed: {e}")
        raise

def main():
    """Main function"""
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

if __name__ == "__main__":
    main() 