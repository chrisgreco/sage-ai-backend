#!/usr/bin/env python3
"""
Download LiveKit turn-detector model files
This script downloads the required model files for the English turn detector
"""

import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def download_turn_detector_model():
    """Download the English turn detector model"""
    try:
        logger.info("📥 Downloading turn-detector model files...")
        
        # Import and initialize the EnglishModel to trigger download
        from livekit.plugins.turn_detector.english import EnglishModel
        
        # Creating the model instance will download required files
        model = EnglishModel()
        
        logger.info("✅ Turn detector model downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download turn detector model: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(download_turn_detector_model())
    if not success:
        exit(1) 