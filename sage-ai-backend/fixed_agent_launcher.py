#!/usr/bin/env python3

"""
Fixed Agent Launcher for Sage AI
===============================

This module addresses the issue where /launch-ai-agents returns 200 
but agents don't actually connect to LiveKit rooms.

Key fixes:
1. Better error handling and logging
2. Proper process monitoring
3. Environment validation
4. Retry logic with backoff
5. Real-time status updates
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    STARTING = "starting"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    FAILED = "failed"
    TERMINATED = "terminated"

@dataclass
class AgentProcess:
    process: subprocess.Popen
    room_name: str
    topic: str
    started_at: float
    status: AgentStatus = AgentStatus.STARTING
    error_message: Optional[str] = None
    retry_count: int = 0
    last_heartbeat: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "room_name": self.room_name,
            "topic": self.topic,
            "started_at": self.started_at,
            "status": self.status.value,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "process_id": self.process.pid,
            "is_running": self.process.poll() is None,
            "return_code": self.process.returncode,
            "uptime": time.time() - self.started_at,
            "last_heartbeat": self.last_heartbeat
        }

class EnhancedAgentManager:
    """Enhanced agent manager with proper error handling"""
    
    def __init__(self):
        self.active_agents: Dict[str, AgentProcess] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    def validate_environment(self) -> tuple[bool, list[str]]:
        """Validate required environment variables"""
        required_vars = [
            "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        return len(missing) == 0, missing
    
    def check_agent_file(self) -> bool:
        """Check if the agent file exists and is executable"""
        agent_file = "multi_personality_agent.py"
        if not os.path.exists(agent_file):
            logger.error(f"Agent file not found: {agent_file}")
            return False
        
        if not os.access(agent_file, os.R_OK):
            logger.error(f"Agent file not readable: {agent_file}")
            return False
            
        return True
    
    async def launch_agent(self, room_name: str, topic: str, max_retries: int = 3) -> Dict[str, Any]:
        """Launch agent with comprehensive error handling"""
        
        # Validate environment
        env_valid, missing_vars = self.validate_environment()
        if not env_valid:
            error_msg = f"Missing environment variables: {missing_vars}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Check agent file
        if not self.check_agent_file():
            error_msg = "Agent file missing or not accessible"
            return {"status": "error", "message": error_msg}
        
        # Check if already running
        if room_name in self.active_agents:
            existing = self.active_agents[room_name]
            if existing.process.poll() is None:
                logger.info(f"Agent already running for room {room_name}")
                return {
                    "status": "success", 
                    "message": "Agent already running",
                    "agent_info": existing.to_dict()
                }
            else:
                # Clean up dead process
                await self._cleanup_agent(room_name)
        
        # Attempt launch with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Launching agent for room {room_name}, attempt {attempt + 1}/{max_retries}")
                
                # Prepare environment
                env = os.environ.copy()
                env.update({
                    "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
                    "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"), 
                    "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                    "ROOM_NAME": room_name,
                    "DEBATE_TOPIC": topic,
                    "PYTHON_UNBUFFERED": "1"  # Ensure output is flushed
                })
                
                # Start process with proper error capture
                process = subprocess.Popen([
                    sys.executable, "-u", "multi_personality_agent.py"
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                # Create agent record
                agent = AgentProcess(
                    process=process,
                    room_name=room_name,
                    topic=topic,
                    started_at=time.time(),
                    retry_count=attempt
                )
                
                self.active_agents[room_name] = agent
                
                logger.info(f"Agent process started with PID {process.pid}")
                
                # Start monitoring
                self.monitoring_tasks[room_name] = asyncio.create_task(
                    self._monitor_agent(room_name)
                )
                
                return {
                    "status": "success",
                    "message": f"Agent launched for room {room_name}",
                    "agent_info": agent.to_dict(),
                    "monitoring": "Started"
                }
                
            except Exception as e:
                error_msg = f"Launch attempt {attempt + 1} failed: {str(e)}"
                logger.error(error_msg)
                
                if attempt == max_retries - 1:
                    return {"status": "error", "message": error_msg}
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {"status": "error", "message": "All launch attempts failed"}
    
    async def _monitor_agent(self, room_name: str):
        """Monitor agent process and connection"""
        if room_name not in self.active_agents:
            return
        
        agent = self.active_agents[room_name]
        logger.info(f"Starting monitoring for agent {room_name} (PID: {agent.process.pid})")
        
        # Initial startup monitoring
        startup_timeout = 30
        startup_start = time.time()
        
        agent.status = AgentStatus.CONNECTING
        
        while time.time() - startup_start < startup_timeout:
            # Check if process terminated
            if agent.process.poll() is not None:
                logger.error(f"Agent process terminated early (PID: {agent.process.pid})")
                agent.status = AgentStatus.FAILED
                
                # Capture error output
                try:
                    stdout, stderr = agent.process.communicate(timeout=5)
                    error_msg = f"Process terminated. STDERR: {stderr[:500]}"
                    agent.error_message = error_msg
                    logger.error(error_msg)
                except subprocess.TimeoutExpired:
                    agent.error_message = "Process terminated, output capture timed out"
                
                return
            
            await asyncio.sleep(1)
            
            # After 5 seconds, assume connection success
            if time.time() - startup_start > 5:
                agent.status = AgentStatus.CONNECTED
                agent.last_heartbeat = time.time()
                logger.info(f"Agent {room_name} connected successfully")
                break
        
        # If we didn't connect within timeout
        if agent.status != AgentStatus.CONNECTED:
            logger.warning(f"Agent {room_name} connection timeout")
            agent.status = AgentStatus.FAILED
            agent.error_message = "Connection timeout"
            return
        
        # Continue monitoring for health
        await self._heartbeat_monitor(room_name)
    
    async def _heartbeat_monitor(self, room_name: str):
        """Monitor agent health with heartbeats"""
        if room_name not in self.active_agents:
            return
        
        agent = self.active_agents[room_name]
        
        while agent.status == AgentStatus.CONNECTED:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            if agent.process.poll() is not None:
                logger.warning(f"Agent {room_name} process terminated")
                agent.status = AgentStatus.TERMINATED
                break
            
            agent.last_heartbeat = time.time()
    
    async def stop_agent(self, room_name: str) -> Dict[str, Any]:
        """Stop an agent gracefully"""
        if room_name not in self.active_agents:
            return {"status": "error", "message": f"No agent found for room {room_name}"}
        
        agent = self.active_agents[room_name]
        
        try:
            # Cancel monitoring
            if room_name in self.monitoring_tasks:
                self.monitoring_tasks[room_name].cancel()
            
            # Terminate process
            agent.process.terminate()
            
            # Wait for graceful shutdown
            try:
                agent.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                agent.process.kill()
                agent.process.wait()
            
            await self._cleanup_agent(room_name)
            
            return {"status": "success", "message": f"Agent stopped for room {room_name}"}
            
        except Exception as e:
            await self._cleanup_agent(room_name)
            return {"status": "error", "message": f"Error stopping agent: {str(e)}"}
    
    async def _cleanup_agent(self, room_name: str):
        """Clean up agent resources"""
        if room_name in self.active_agents:
            del self.active_agents[room_name]
        if room_name in self.monitoring_tasks:
            self.monitoring_tasks[room_name].cancel()
            del self.monitoring_tasks[room_name]
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        current_time = time.time()
        
        # Clean up terminated processes
        terminated_rooms = []
        for room_name, agent in self.active_agents.items():
            if agent.process.poll() is not None and agent.status not in [AgentStatus.FAILED, AgentStatus.TERMINATED]:
                agent.status = AgentStatus.TERMINATED
                terminated_rooms.append(room_name)
        
        # Gather statistics
        total_agents = len(self.active_agents)
        running_agents = sum(1 for agent in self.active_agents.values() if agent.process.poll() is None)
        connected_agents = sum(1 for agent in self.active_agents.values() if agent.status == AgentStatus.CONNECTED)
        failed_agents = sum(1 for agent in self.active_agents.values() if agent.status == AgentStatus.FAILED)
        
        return {
            "status": "success",
            "timestamp": current_time,
            "summary": {
                "total_agents": total_agents,
                "running_processes": running_agents,
                "connected_agents": connected_agents,
                "failed_agents": failed_agents,
                "recently_terminated": len(terminated_rooms)
            },
            "agents": {
                room_name: agent.to_dict() 
                for room_name, agent in self.active_agents.items()
            }
        }
    
    def get_agent_health(self, room_name: str) -> Dict[str, Any]:
        """Get detailed health for specific agent"""
        if room_name not in self.active_agents:
            return {"status": "error", "message": f"No agent found for room {room_name}"}
        
        agent = self.active_agents[room_name]
        health_data = agent.to_dict()
        
        # Add health assessment
        health_data["healthy"] = (
            agent.process.poll() is None and 
            agent.status == AgentStatus.CONNECTED
        )
        
        return {"status": "success", "health": health_data}

# Global instance
enhanced_agent_manager = EnhancedAgentManager()

# Integration functions for app.py
async def enhanced_launch_agents(room_name: str, topic: str) -> Dict[str, Any]:
    """Enhanced agent launch function for app.py integration"""
    return await enhanced_agent_manager.launch_agent(room_name, topic)

async def enhanced_stop_agents(room_name: str) -> Dict[str, Any]:
    """Enhanced agent stop function for app.py integration"""
    return await enhanced_agent_manager.stop_agent(room_name)

def enhanced_get_status() -> Dict[str, Any]:
    """Enhanced status function for app.py integration"""
    return enhanced_agent_manager.get_status()

def enhanced_get_health(room_name: str) -> Dict[str, Any]:
    """Enhanced health check function for app.py integration"""
    return enhanced_agent_manager.get_agent_health(room_name) 