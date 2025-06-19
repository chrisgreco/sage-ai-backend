#!/usr/bin/env python3
"""
Conversation Coordinator for Sage AI Dual-Agent System
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent conversation states"""
    LISTENING = "listening"
    SPEAKING = "speaking" 
    WAITING_TURN = "waiting_turn"

@dataclass
class AgentStatus:
    """Current status of an agent"""
    agent_name: str
    state: AgentState
    wants_to_speak: bool = False
    trigger_priority: str = "medium"
    intervention_reason: Optional[str] = None

class ConversationCoordinator:
    """Coordinates conversation flow between multiple AI agents"""
    
    def __init__(self, agent_names: List[str]):
        self.agent_names = agent_names
        self.agents: Dict[str, AgentStatus] = {}
        self.current_speaker: Optional[str] = None
        
        # Priority levels for intervention urgency
        self.priority_levels = {
            "urgent": 4,    # Immediate intervention needed (factual errors, safety)
            "high": 3,      # Important clarification or correction
            "medium": 2,    # General contribution or question
            "low": 1        # Optional comment or observation
        }
        
        # Anti-domination tracking
        self.speaking_counts = {name: 0 for name in agent_names}
        self.last_intervention_time = {name: 0 for name in agent_names}
        
        # Initialize agent statuses
        for name in agent_names:
            self.agents[name] = AgentStatus(agent_name=name, state=AgentState.LISTENING)
        
        logger.info(f"🎭 Coordinator initialized for: {agent_names}")

    async def request_speaking_turn(self, agent_name: str, trigger_type: str = "general", 
                                  priority: str = "medium", reason: str = "") -> bool:
        """Agent requests permission to speak"""
        if agent_name not in self.agents:
            return False
            
        agent = self.agents[agent_name]
        agent.wants_to_speak = True
        agent.trigger_priority = priority
        agent.intervention_reason = reason
        
        # Check if agent can speak immediately
        can_speak = self._evaluate_speaking_permission(agent_name)
        
        if can_speak:
            self._grant_speaking_turn(agent_name)
            return True
        else:
            agent.state = AgentState.WAITING_TURN
            return False

    def _evaluate_speaking_permission(self, requesting_agent: str) -> bool:
        """Evaluate whether an agent should be allowed to speak now"""
        # No current speaker - go ahead
        if not self.current_speaker:
            return True
        
        # Don't interrupt yourself
        if self.current_speaker == requesting_agent:
            return False
        
        # Check priority levels
        current_speaker_agent = self.agents[self.current_speaker]
        requesting_agent_obj = self.agents[requesting_agent]
        
        current_priority = self.priority_levels.get(current_speaker_agent.trigger_priority, 2)
        request_priority = self.priority_levels.get(requesting_agent_obj.trigger_priority, 2)
        
        # High priority can interrupt medium/low priority
        return request_priority > current_priority

    def _grant_speaking_turn(self, agent_name: str):
        """Grant speaking permission to an agent"""
        # End previous speaker's turn if needed
        if self.current_speaker and self.current_speaker != agent_name:
            self.agents[self.current_speaker].state = AgentState.LISTENING
        
        # Start new turn
        self.current_speaker = agent_name
        agent = self.agents[agent_name]
        agent.state = AgentState.SPEAKING
        agent.wants_to_speak = False
        
        logger.info(f"✅ Speaking turn granted to {agent_name}")

    def agent_finished_speaking(self, agent_name: str):
        """Notify coordinator that agent has stopped speaking"""
        if agent_name in self.agents:
            self.agents[agent_name].state = AgentState.LISTENING
            if self.current_speaker == agent_name:
                self.current_speaker = None

# Global coordinator instance
conversation_coordinator: Optional[ConversationCoordinator] = None

def initialize_coordinator(agent_names: List[str]) -> ConversationCoordinator:
    """Initialize the global conversation coordinator"""
    global conversation_coordinator
    conversation_coordinator = ConversationCoordinator(agent_names)
    return conversation_coordinator

def get_coordinator() -> Optional[ConversationCoordinator]:
    """Get the global conversation coordinator"""
    return conversation_coordinator 
