#!/usr/bin/env python3

"""
Audio Bridge Test Script
=======================

This script tests the audio bridge functionality by simulating WebRTC audio data
and verifying that it can be processed and forwarded to AI agents.
"""

import asyncio
import numpy as np
import base64
import json
import logging
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_audio(duration_seconds=2.0, sample_rate=16000, frequency=440):
    """Generate test audio data (sine wave)"""
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples, False)
    audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    return audio_data

def encode_audio_for_webrtc(audio_data):
    """Encode audio data as base64 string like WebRTC would send"""
    audio_bytes = audio_data.tobytes()
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    return base64_audio

async def test_audio_bridge_integration():
    """Test the audio bridge integration module"""
    try:
        from audio_bridge_integration import (
            AudioProcessor,
            process_webrtc_audio_for_agents,
            initialize_audio_bridge_manager,
            get_audio_bridge_manager
        )
        
        logger.info("✅ Audio bridge integration imported successfully")
        
        # Test audio processing
        logger.info("🎵 Generating test audio...")
        test_audio = generate_test_audio(duration_seconds=1.0)
        logger.info(f"Generated {len(test_audio)} audio samples")
        
        # Encode as WebRTC would
        base64_audio = encode_audio_for_webrtc(test_audio)
        logger.info(f"Encoded audio as base64: {len(base64_audio)} characters")
        
        # Test decoding
        logger.info("🔄 Testing audio decoding...")
        decoded_audio = AudioProcessor.decode_webrtc_audio(base64_audio)
        logger.info(f"Decoded {len(decoded_audio)} audio samples")
        
        # Verify data integrity
        if np.allclose(test_audio, decoded_audio):
            logger.info("✅ Audio encoding/decoding test passed")
        else:
            logger.error("❌ Audio data integrity test failed")
            return False
        
        # Test audio preparation for AI agents
        logger.info("🤖 Testing audio preparation for AI agents...")
        prepared_audio = AudioProcessor.prepare_for_ai_agents(decoded_audio)
        logger.info(f"Prepared audio: {prepared_audio.dtype}, range: {prepared_audio.min()} to {prepared_audio.max()}")
        
        # Test bridge manager initialization
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if all([livekit_url, livekit_api_key, livekit_api_secret]):
            logger.info("🔗 Testing bridge manager initialization...")
            bridge_manager = initialize_audio_bridge_manager(
                livekit_url, livekit_api_key, livekit_api_secret
            )
            
            if get_audio_bridge_manager():
                logger.info("✅ Bridge manager initialized successfully")
            else:
                logger.error("❌ Bridge manager initialization failed")
                return False
        else:
            logger.warning("⚠️ LiveKit credentials not found - skipping bridge manager test")
        
        # Test the full processing pipeline
        logger.info("🔄 Testing full audio processing pipeline...")
        result = await process_webrtc_audio_for_agents(
            room_name="test-room",
            base64_audio=base64_audio,
            participant_name="test-participant"
        )
        
        logger.info(f"Processing result: {json.dumps(result, indent=2)}")
        
        if result["status"] in ["success", "warning"]:
            logger.info("✅ Audio processing pipeline test passed")
            return True
        else:
            logger.error("❌ Audio processing pipeline test failed")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Failed to import audio bridge integration: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Audio bridge test failed: {e}")
        return False

async def test_backend_api():
    """Test the backend API audio bridge endpoint"""
    try:
        import aiohttp
        
        # Generate test audio
        test_audio = generate_test_audio(duration_seconds=0.5)
        base64_audio = encode_audio_for_webrtc(test_audio)
        
        # Prepare request data
        request_data = {
            "room_name": "test-room",
            "audio_data": base64_audio,
            "participant_name": "test-participant",
            "timestamp": 1234567890.123
        }
        
        # Test the endpoint
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8000/audio-bridge"
            
            logger.info(f"🌐 Testing audio bridge endpoint: {url}")
            
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ API test passed: {json.dumps(result, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API test failed: {response.status} - {error_text}")
                    return False
                    
    except ImportError:
        logger.warning("⚠️ aiohttp not available - skipping API test")
        return True
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Audio Bridge Tests")
    logger.info("=" * 50)
    
    # Test the integration module
    integration_test = await test_audio_bridge_integration()
    
    # Test the API endpoint (only if backend is running)
    api_test = await test_backend_api()
    
    logger.info("=" * 50)
    if integration_test and api_test:
        logger.info("🎉 All audio bridge tests passed!")
        return True
    else:
        logger.error("❌ Some audio bridge tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 