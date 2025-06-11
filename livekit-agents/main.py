
import asyncio
import logging
from typing import Dict, List
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from livekit import rtc
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebateAgent:
    def __init__(self, name: str, role: str, persona: str, instructions: str):
        self.name = name
        self.role = role
        self.persona = persona
        self.instructions = instructions
        self.active = True

class DebateModerationService:
    def __init__(self):
        self.agents = {
            "socrates": DebateAgent(
                "Socrates", 
                "Clarifier",
                "Ask clarifying questions when assumptions are made",
                "You are Socrates, an AI debate moderator. Ask clarifying questions when participants make assumptions or logical jumps. Only interject when clarity is needed. Keep questions brief and thought-provoking."
            ),
            "solon": DebateAgent(
                "Solon",
                "Rule Enforcer", 
                "Enforce debate rules and ensure fair turn-taking",
                "You are Solon, an AI debate moderator. Enforce debate rules like no interruptions, no personal attacks, and fair speaking time. Only speak when rules are violated. Be firm but respectful."
            ),
            "buddha": DebateAgent(
                "Buddha",
                "Peacekeeper",
                "Monitor tone and diffuse conflict",
                "You are Buddha, an AI debate moderator. Monitor emotional tone and intervene when discussions become heated or aggressive. Promote calm, respectful dialogue. Only speak when tone needs adjustment."
            ),
            "hermes": DebateAgent(
                "Hermes", 
                "Summarizer",
                "Provide summaries and logical transitions",
                "You are Hermes, an AI debate moderator. Summarize key points and provide logical transitions during natural breaks. Help structure the conversation. Only speak during appropriate pauses."
            ),
            "aristotle": DebateAgent(
                "Aristotle",
                "Fact-Checker", 
                "Request sources for factual claims",
                "You are Aristotle, an AI debate moderator. Listen for factual claims and request sources when evidence is lacking. Promote logical reasoning and evidence-based arguments. Only speak when facts need verification."
            )
        }
        self.current_agent = None
        self.transcript = []

    def get_active_agents(self) -> List[DebateAgent]:
        return [agent for agent in self.agents.values() if agent.active]

    def determine_appropriate_agent(self, conversation_context: str) -> DebateAgent:
        # Simple agent selection logic - in production this could be more sophisticated
        active_agents = self.get_active_agents()
        if not active_agents:
            return list(self.agents.values())[0]
        
        # For now, rotate through active agents
        # TODO: Implement smarter agent selection based on context
        import random
        return random.choice(active_agents)

    def get_moderation_instructions(self) -> str:
        active_agents = self.get_active_agents()
        agent_descriptions = "\n".join([
            f"- {agent.name} ({agent.role}): {agent.persona}"
            for agent in active_agents
        ])
        
        return f"""You are part of a multi-agent AI moderation system for live voice debates.

Active moderators:
{agent_descriptions}

Your role is to moderate the debate according to your assigned persona. Only speak when your specific moderation criteria are met. Keep interventions brief (1-2 sentences), polite, and focused on your role.

Current debate rules:
- No personal attacks
- Provide sources for factual claims  
- Respect speaking turns
- Stay on topic

Listen carefully to the conversation and only interject when necessary according to your role."""

async def entrypoint(ctx: JobContext):
    logger.info("Starting SAGE debate moderation agent")
    
    # Initialize moderation service
    moderation_service = DebateModerationService()
    
    # Wait for participant to connect
    await ctx.wait_for_participant()
    logger.info("Participant connected to debate room")

    # Create voice assistant with OpenAI Realtime API
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(
            model="gpt-4o-realtime-preview-2024-12-17",
            instructions=moderation_service.get_moderation_instructions(),
            temperature=0.8,
        ),
        tts=openai.TTS(voice="alloy"),
        chat_ctx=llm.ChatContext(),
    )

    # Handle chat context updates for agent coordination
    @assistant.on("function_calls_finished")
    def on_function_calls_finished(called_functions: list):
        logger.info(f"Function calls finished: {called_functions}")

    # Start the voice assistant
    assistant.start(ctx.room)
    
    # Listen for room events to coordinate agents
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant connected: {participant.identity}")

    @ctx.room.on("participant_disconnected")  
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity}")

    # Send periodic updates about moderation status
    async def send_moderation_status():
        while True:
            try:
                # Send status to frontend via data channel
                status_data = {
                    "type": "moderation_status",
                    "active_agents": [
                        {"name": agent.name, "role": agent.role, "active": agent.active}
                        for agent in moderation_service.agents.values()
                    ],
                    "transcript_length": len(moderation_service.transcript)
                }
                
                # Publish data to room
                await ctx.room.local_participant.publish_data(
                    json.dumps(status_data).encode(),
                    destination_identities=[]  # Send to all participants
                )
                
                await asyncio.sleep(5)  # Send status every 5 seconds
            except Exception as e:
                logger.error(f"Error sending moderation status: {e}")
                await asyncio.sleep(5)

    # Start status updates
    asyncio.create_task(send_moderation_status())
    
    logger.info("SAGE debate moderation agent is ready")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Allow agent to automatically subscribe to participant tracks
            auto_subscribe=AutoSubscribe.AUDIO_ONLY,
        )
    )
