#!/usr/bin/env python3

"""
Quick Agent Fix for Sage AI
==========================

This provides immediate fixes for the agent connection issues without 
requiring major code changes. Can be integrated into existing app.py.
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def enhanced_monitor_agent_connection(room_name: str, process: subprocess.Popen, max_wait_time: int = 30):
    """Enhanced monitoring with better error capture"""
    logger.info(f"🔍 Enhanced monitoring started for room {room_name}, PID {process.pid}")
    
    start_time = time.time()
    
    # Check environment first
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"❌ Missing environment variables: {missing}")
        return {"connected": False, "error": f"Missing env vars: {missing}"}
    
    # Monitor startup process
    for i in range(max_wait_time):
        # Check if process terminated
        if process.poll() is not None:
            return_code = process.returncode
            logger.error(f"❌ Process {process.pid} terminated with code {return_code}")
            
            # Capture output for debugging
            try:
                stdout, stderr = process.communicate(timeout=5)
                logger.error(f"STDOUT: {stdout[:500] if stdout else '(empty)'}")
                logger.error(f"STDERR: {stderr[:500] if stderr else '(empty)'}")
                
                return {
                    "connected": False, 
                    "error": f"Process terminated (code: {return_code})",
                    "stdout": stdout[:500] if stdout else "",
                    "stderr": stderr[:500] if stderr else ""
                }
            except subprocess.TimeoutExpired:
                return {
                    "connected": False,
                    "error": f"Process terminated (code: {return_code}), output capture timeout"
                }
        
        # Log progress every 5 seconds
        if i % 5 == 0 and i > 0:
            logger.info(f"⏳ Process {process.pid} still running ({i}/{max_wait_time}s)")
        
        await asyncio.sleep(1)
        
        # Consider connected after 10 seconds if still running
        if time.time() - start_time > 10:
            logger.info(f"✅ Process {process.pid} appears stable after 10s")
            return {"connected": True, "connection_time": time.time() - start_time}
    
    # Timeout case
    logger.warning(f"⚠️ Monitoring timeout for process {process.pid}")
    return {"connected": False, "error": "Monitoring timeout"}

def validate_agent_environment() -> Dict[str, Any]:
    """Validate environment before launching agents"""
    issues = []
    
    # Check environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        issues.append(f"Missing environment variables: {missing_vars}")
    
    # Check agent file
    agent_file = "multi_personality_agent.py"
    if not os.path.exists(agent_file):
        issues.append(f"Agent file not found: {agent_file}")
    elif not os.access(agent_file, os.R_OK):
        issues.append(f"Agent file not readable: {agent_file}")
    
    # Check Python executable
    if not os.access(sys.executable, os.X_OK):
        issues.append(f"Python executable not accessible: {sys.executable}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "environment": {
            "python_path": sys.executable,
            "working_directory": os.getcwd(),
            "agent_file_exists": os.path.exists(agent_file)
        }
    }

async def robust_agent_launch(room_name: str, topic: str, max_retries: int = 3) -> Dict[str, Any]:
    """Robust agent launch with comprehensive error handling"""
    
    # Pre-flight validation
    validation = validate_agent_environment()
    if not validation["valid"]:
        logger.error(f"❌ Environment validation failed: {validation['issues']}")
        return {
            "status": "error",
            "message": "Environment validation failed",
            "issues": validation["issues"]
        }
    
    logger.info(f"✅ Environment validation passed for room {room_name}")
    
    # Retry loop
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Launch attempt {attempt + 1}/{max_retries} for room {room_name}")
            
            # Prepare environment with extra debugging
            env = os.environ.copy()
            env.update({
                "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
                "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
                "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
                "ROOM_NAME": room_name,
                "DEBATE_TOPIC": topic,
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY", ""),
                "CARTESIA_API_KEY": os.getenv("CARTESIA_API_KEY", ""),
                "PYTHON_UNBUFFERED": "1",
                "LIVEKIT_LOG_LEVEL": "INFO"  # Enable LiveKit debugging
            })
            
            # Start process with better error capture
            process = subprocess.Popen([
                sys.executable, "-u", "multi_personality_agent.py"
            ], 
            env=env, 
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
            )
            
            logger.info(f"✅ Process started with PID {process.pid}")
            
            # Enhanced monitoring
            monitor_result = await enhanced_monitor_agent_connection(room_name, process)
            
            if monitor_result["connected"]:
                logger.info(f"🎉 Agent successfully connected for room {room_name}")
                return {
                    "status": "success",
                    "message": f"AI agents launched for room: {room_name}",
                    "room_name": room_name,
                    "topic": topic,
                    "process_id": process.pid,
                    "attempt": attempt + 1,
                    "connection_time": monitor_result.get("connection_time"),
                    "monitoring_result": monitor_result
                }
            else:
                logger.error(f"❌ Agent connection failed: {monitor_result.get('error')}")
                # Process failed, clean up
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                
                if attempt == max_retries - 1:
                    return {
                        "status": "error",
                        "message": f"Agent connection failed after {max_retries} attempts",
                        "last_error": monitor_result.get("error"),
                        "debug_info": monitor_result
                    }
        
        except Exception as e:
            error_msg = f"Launch attempt {attempt + 1} failed: {str(e)}"
            logger.error(error_msg)
            
            if attempt == max_retries - 1:
                return {
                    "status": "error",
                    "message": error_msg,
                    "attempts": max_retries
                }
        
        # Wait before retry with exponential backoff
        wait_time = 2 ** attempt
        logger.info(f"⏱️ Waiting {wait_time}s before retry...")
        await asyncio.sleep(wait_time)
    
    return {
        "status": "error",
        "message": f"All {max_retries} launch attempts failed"
    }

# Integration helper for existing app.py
def create_enhanced_launch_endpoint():
    """Returns an enhanced launch function that can replace the existing one in app.py"""
    
    async def enhanced_launch_ai_agents(request):
        """Drop-in replacement for the existing launch endpoint"""
        try:
            logger.info(f"🚀 Enhanced launch requested for room: {request.room_name}, topic: {request.topic}")
            
            # Validate LiveKit configuration  
            if not all([os.getenv("LIVEKIT_URL"), os.getenv("LIVEKIT_API_KEY"), os.getenv("LIVEKIT_API_SECRET")]):
                return {
                    "status": "error", 
                    "message": "LiveKit configuration missing"
                }
            
            room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
            
            # Use robust launch
            result = await robust_agent_launch(room_name, request.topic)
            
            logger.info(f"Enhanced launch result: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced launch error: {str(e)}")
            return {
                "status": "error",
                "message": f"Enhanced launch failed: {str(e)}"
            }
    
    return enhanced_launch_ai_agents

# Quick diagnostic function
async def diagnose_agent_issues():
    """Quick diagnostic to identify common issues"""
    logger.info("🔧 Running agent diagnostics...")
    
    validation = validate_agent_environment()
    print(f"Environment validation: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
    
    if not validation["valid"]:
        print("Issues found:")
        for issue in validation["issues"]:
            print(f"  - {issue}")
    
    # Test a quick launch
    try:
        test_result = await robust_agent_launch("diagnostic-test", "Diagnostic Test", max_retries=1)
        print(f"Test launch: {'✅ SUCCESS' if test_result['status'] == 'success' else '❌ FAILED'}")
        if test_result["status"] == "error":
            print(f"Error: {test_result.get('message')}")
    except Exception as e:
        print(f"Test launch failed: {e}")

if __name__ == "__main__":
    # Run diagnostics
    asyncio.run(diagnose_agent_issues()) 