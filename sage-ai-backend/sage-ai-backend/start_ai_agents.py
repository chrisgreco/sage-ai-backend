#!/usr/bin/env python3

"""
Simple startup script for the Sage AI Multi-Agent Debate System
================================================================

This script provides an alternative way to start the AI agents system
with better error handling and logging.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for starting AI agents"""
    
    # Load environment variables
    load_dotenv()
    
    logger.info("🚀 Starting Sage AI Multi-Agent Debate System...")
    
    # Check environment variables
    required_vars = [
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please ensure all API keys and LiveKit credentials are set")
        sys.exit(1)
    
    logger.info("✅ All environment variables configured")
    logger.info(f"🎯 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    logger.info(f"🎯 Room: {os.getenv('ROOM_NAME', 'Not specified')}")
    logger.info(f"🎯 Topic: {os.getenv('DEBATE_TOPIC', 'Default topic')}")
    
    try:
        # Import and run the main AI agents system
        from ai_debate_agents import cli, WorkerOptions, entrypoint
        
        logger.info("🎭 Launching multi-agent debate system...")
        
        # Run the LiveKit agent
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint,
            )
        )
        
    except ImportError as e:
        logger.error(f"❌ Failed to import AI agents module: {e}")
        logger.error("Please ensure all required dependencies are installed:")
        logger.error("pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Error starting AI agents: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 