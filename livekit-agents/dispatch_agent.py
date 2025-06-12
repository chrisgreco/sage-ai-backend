import os
import sys
import logging
import asyncio
import subprocess
from dotenv import load_dotenv

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default configuration
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "wss://sage-2kpu4z1y.livekit.cloud")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "APIWQtUQUijqXVp")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI")
ROOM_NAME = os.environ.get("ROOM_NAME", "test-debate-room")

# Print environment variables at startup
logger.info(f"Environment variables:")
logger.info(f"  LIVEKIT_URL: {LIVEKIT_URL}")
logger.info(f"  LIVEKIT_API_KEY: {LIVEKIT_API_KEY}")
logger.info(f"  LIVEKIT_API_SECRET: {LIVEKIT_API_SECRET[:5]}...")
logger.info(f"  ROOM_NAME: {ROOM_NAME}")
if os.environ.get("OPENAI_API_KEY"):
    logger.info(f"  OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY')[:5]}...")
else:
    logger.warning("  OPENAI_API_KEY not set (required for agent functionality)")

async def read_stream(stream, prefix):
    """Read from a stream and log each line with the given prefix"""
    async for line in stream:
        logger.info(f"{prefix}: {line.decode().strip()}")

async def run_process(cmd, env, name):
    """Run a subprocess and log its output"""
    logger.info(f"Starting {name} process: {' '.join(cmd)}")
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    logger.info(f"{name} process started with PID: {process.pid}")
    
    # Create tasks to read from stdout and stderr
    stdout_task = asyncio.create_task(read_stream(process.stdout, f"{name} stdout"))
    stderr_task = asyncio.create_task(read_stream(process.stderr, f"{name} stderr"))
    
    # Wait for the process to complete
    await process.wait()
    
    # Wait for the output reading tasks to complete
    await stdout_task
    await stderr_task
    
    logger.info(f"{name} process exited with code: {process.returncode}")
    return process.returncode

async def dispatch_agent():
    """Dispatch the agent to a room using the LiveKit API"""
    
    # Environment variables for subprocess
    env = os.environ.copy()
    env["LIVEKIT_URL"] = LIVEKIT_URL
    env["LIVEKIT_API_KEY"] = LIVEKIT_API_KEY
    env["LIVEKIT_API_SECRET"] = LIVEKIT_API_SECRET
    env["ROOM_NAME"] = ROOM_NAME
    
    try:
        logger.info(f"Starting test client to create room: {ROOM_NAME}")
        
        # First, run the test client to create the room
        await run_process(
            ["python", "test_client.py"],
            env,
            "Test Client"
        )
        
        logger.info(f"Room creation completed, now starting agent")
        
        # Run the agent in dev mode
        await run_process(
            ["python", "run_agent.py", "dev"],
            env,
            "Agent"
        )
        
    except Exception as e:
        logger.error(f"Error in dispatch process: {e}", exc_info=True)

if __name__ == "__main__":
    # Parse command-line arguments
    if len(sys.argv) > 1:
        ROOM_NAME = sys.argv[1]
        logger.info(f"Using room name from command line: {ROOM_NAME}")
    
    # Run the dispatch function
    asyncio.run(dispatch_agent()) 