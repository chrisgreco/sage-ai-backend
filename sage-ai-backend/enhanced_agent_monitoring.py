#!/usr/bin/env python3

"""
Enhanced Agent Monitoring System for Sage AI
==========================================

This module provides comprehensive monitoring, retry logic, and status tracking
for AI agent connections to LiveKit rooms.
"""

import asyncio
import logging
import time
import subprocess
import sys
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    STARTING = "starting"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class AgentInfo:
    process: subprocess.Popen
    topic: str
    started_at: float
    room_name: str
    retry_count: int = 0
    status: AgentStatus = AgentStatus.STARTING
    connection_result: Optional[Dict] = None
    connection_error: Optional[str] = None
    last_heartbeat: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['process_id'] = self.process.pid
        data['process_running'] = self.process.poll() is None
        data['uptime_seconds'] = round(time.time() - self.started_at, 2)
        data['uptime_minutes'] = round((time.time() - self.started_at) / 60, 2)
        if not data['process_running']:
            data['return_code'] = self.process.returncode
        # Remove non-serializable process object
        del data['process']
        return data

class AgentMonitoringManager:
    """Manages AI agent processes with comprehensive monitoring"""
    
    def __init__(self):
        self.active_agents: Dict[str, AgentInfo] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    async def launch_agent(self, room_name: str, topic: str, env_vars: Dict[str, str], 
                          max_retries: int = 3) -> Dict[str, Any]:
        """Launch an AI agent with retry logic and monitoring"""
        
        # Check if agents are already running for this room
        if room_name in self.active_agents:
            agent_info = self.active_agents[room_name]
            if agent_info.process.poll() is None:
                logger.info(f"Agents already running for room {room_name}")
                return {
                    "status": "success",
                    "message": f"AI agents already running for room: {room_name}",
                    "room_name": room_name,
                    "agents_active": True,
                    "agent_info": agent_info.to_dict()
                }
            else:
                # Process died, clean it up
                logger.warning(f"Found dead agent process for room {room_name}, cleaning up")
                await self.cleanup_agent(room_name)
        
        # Attempt to launch with retries
        for retry_count in range(max_retries):
            try:
                logger.info(f"Attempt {retry_count + 1}/{max_retries} to launch agents for room {room_name}")
                
                # Start the multi-personality agent as a subprocess
                process = subprocess.Popen([
                    sys.executable, "-u", "multi_personality_agent.py"
                ], 
                env=env_vars, 
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
                )
                
                # Create agent info
                agent_info = AgentInfo(
                    process=process,
                    topic=topic,
                    started_at=time.time(),
                    room_name=room_name,
                    retry_count=retry_count,
                    status=AgentStatus.STARTING
                )
                
                self.active_agents[room_name] = agent_info
                
                logger.info(f"Agent process launched with PID {process.pid} for room {room_name}")
                
                # Start monitoring task
                self.monitoring_tasks[room_name] = asyncio.create_task(
                    self._monitor_agent(room_name)
                )
                
                return {
                    "status": "success",
                    "message": f"AI agents launched for room: {room_name}",
                    "room_name": room_name,
                    "topic": topic,
                    "agents_active": True,
                    "process_id": process.pid,
                    "retry_count": retry_count,
                    "monitoring": "Agent connection monitoring started"
                }
                
            except FileNotFoundError:
                error_msg = "multi_personality_agent.py not found"
                logger.error(f"Retry {retry_count + 1} failed: {error_msg}")
                if retry_count == max_retries - 1:
                    return {"status": "error", "message": error_msg}
                    
            except Exception as e:
                error_msg = f"Failed to start AI agents: {str(e)}"
                logger.error(f"Retry {retry_count + 1} failed: {error_msg}")
                if retry_count == max_retries - 1:
                    return {"status": "error", "message": error_msg}
            
            if retry_count < max_retries - 1:
                logger.info(f"Waiting 2 seconds before retry {retry_count + 2}")
                await asyncio.sleep(2)
        
        return {"status": "error", "message": f"Failed to launch agents after {max_retries} attempts"}
    
    async def _monitor_agent(self, room_name: str, max_wait_time: int = 30):
        """Monitor agent connection and update status"""
        if room_name not in self.active_agents:
            return
        
        agent_info = self.active_agents[room_name]
        logger.info(f"Starting agent connection monitoring for room {room_name}, PID {agent_info.process.pid}")
        
        start_time = time.time()
        agent_info.status = AgentStatus.CONNECTING
        
        # Monitor connection process
        while time.time() - start_time < max_wait_time:
            # Check if process is still running
            if agent_info.process.poll() is not None:
                return_code = agent_info.process.returncode
                logger.error(f"Agent process {agent_info.process.pid} terminated early with code {return_code}")
                agent_info.status = AgentStatus.FAILED
                agent_info.connection_result = {
                    "connected": False, 
                    "error": f"Process terminated with code {return_code}"
                }
                return
            
            await asyncio.sleep(1)
            
            # For now, assume connection after 5 seconds
            # In production, you'd check LiveKit API for participant presence
            if time.time() - start_time > 5:
                agent_info.status = AgentStatus.CONNECTED
                agent_info.connection_result = {
                    "connected": True, 
                    "connection_time": time.time() - start_time
                }
                logger.info(f"✅ Agents successfully connected for room {room_name}")
                
                # Start heartbeat monitoring
                await self._start_heartbeat_monitoring(room_name)
                return
        
        # Connection timeout
        logger.warning(f"Agent connection timeout for room {room_name}")
        agent_info.status = AgentStatus.FAILED
        agent_info.connection_result = {"connected": False, "error": "Connection timeout"}
    
    async def _start_heartbeat_monitoring(self, room_name: str):
        """Monitor agent health with periodic heartbeats"""
        if room_name not in self.active_agents:
            return
        
        agent_info = self.active_agents[room_name]
        
        while agent_info.status == AgentStatus.CONNECTED:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            if agent_info.process.poll() is not None:
                logger.warning(f"Agent process for room {room_name} has terminated")
                agent_info.status = AgentStatus.DISCONNECTED
                break
            
            agent_info.last_heartbeat = time.time()
    
    async def stop_agent(self, room_name: str) -> Dict[str, Any]:
        """Stop agents for a specific room"""
        if room_name not in self.active_agents:
            return {
                "status": "success",
                "message": f"No AI agents running for room: {room_name}",
                "room_name": room_name,
                "agents_active": False
            }
        
        try:
            agent_info = self.active_agents[room_name]
            process = agent_info.process
            
            # Cancel monitoring task
            if room_name in self.monitoring_tasks:
                self.monitoring_tasks[room_name].cancel()
                del self.monitoring_tasks[room_name]
            
            # Terminate the process
            process.terminate()
            
            # Wait for it to finish (with timeout)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()
            
            # Remove from active agents
            del self.active_agents[room_name]
            
            logger.info(f"AI agents stopped successfully for room {room_name}")
            
            return {
                "status": "success",
                "message": f"AI agents stopped for room: {room_name}",
                "room_name": room_name,
                "agents_active": False
            }
            
        except Exception as e:
            logger.error(f"Failed to stop AI agents: {str(e)}")
            # Clean up the entry even if stopping failed
            await self.cleanup_agent(room_name)
            return {"status": "error", "message": f"Failed to stop AI agents: {str(e)}"}
    
    async def cleanup_agent(self, room_name: str):
        """Clean up agent resources"""
        if room_name in self.active_agents:
            del self.active_agents[room_name]
        if room_name in self.monitoring_tasks:
            self.monitoring_tasks[room_name].cancel()
            del self.monitoring_tasks[room_name]
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all agents"""
        # Clean up dead processes
        dead_rooms = []
        for room_name, agent_info in self.active_agents.items():
            if agent_info.process.poll() is not None and agent_info.status != AgentStatus.DISCONNECTED:
                agent_info.status = AgentStatus.DISCONNECTED
                dead_rooms.append(room_name)
        
        detailed_status = {
            room_name: agent_info.to_dict() 
            for room_name, agent_info in self.active_agents.items()
        }
        
        # Summary statistics
        running_count = sum(1 for info in detailed_status.values() if info["process_running"])
        failed_count = sum(1 for info in detailed_status.values() if info["status"] == "failed")
        connected_count = sum(1 for info in detailed_status.values() if info["status"] == "connected")
        
        return {
            "status": "success",
            "timestamp": time.time(),
            "summary": {
                "total_rooms": len(detailed_status),
                "running_agents": running_count,
                "connected_agents": connected_count,
                "failed_agents": failed_count,
                "recently_disconnected": len(dead_rooms)
            },
            "rooms": detailed_status,
            "monitoring_info": {
                "agent_connection_timeout": 30,
                "heartbeat_interval": 10,
                "max_retries": 3,
                "retry_delay": 2
            }
        }
    
    def get_agent_health(self, room_name: str) -> Dict[str, Any]:
        """Get detailed health information for a specific room's agents"""
        if room_name not in self.active_agents:
            return {
                "status": "error", 
                "message": f"No agents found for room: {room_name}"
            }
        
        agent_info = self.active_agents[room_name]
        health_data = agent_info.to_dict()
        
        # Add health assessment
        health_data["healthy"] = (
            health_data["process_running"] and 
            health_data["status"] == "connected"
        )
        
        health_data["last_check"] = time.time()
        
        return {"status": "success", "health": health_data}

# Global instance for use in app.py
agent_manager = AgentMonitoringManager() 