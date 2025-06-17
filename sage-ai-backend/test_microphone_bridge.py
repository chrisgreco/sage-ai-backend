#!/usr/bin/env python3

"""
Microphone Test for Audio Bridge
================================

This script captures audio from your microphone and sends it to the audio bridge
endpoint, simulating what the frontend does. Perfect for testing the complete
voice interaction with AI agents.
"""

import asyncio
import numpy as np
import base64
import requests
import json
import time
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MicrophoneTester:
    def __init__(self, backend_url="http://localhost:8000", room_name="demo", participant_name="mic-tester"):
        self.backend_url = backend_url
        self.room_name = room_name
        self.participant_name = participant_name
        self.is_recording = False
        
    def test_backend_connection(self):
        """Test if the backend is accessible"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                logger.info(f"✅ Backend is healthy: {health}")
                return True
            else:
                logger.error(f"❌ Backend health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to backend: {e}")
            return False
    
    def test_ai_agents_status(self):
        """Check if AI agents are running"""
        try:
            response = requests.get(f"{self.backend_url}/ai-agents/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                logger.info(f"🤖 AI Agents Status: {status}")
                return status['active_agent_rooms'] > 0
            else:
                logger.error(f"❌ AI agents status check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot check AI agents status: {e}")
            return False
    
    def launch_ai_agents(self):
        """Launch AI agents for testing"""
        try:
            data = {
                "room_name": self.room_name,
                "topic": "Microphone testing with AI agents"
            }
            response = requests.post(f"{self.backend_url}/launch-ai-agents", json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🚀 AI Agents launched: {result['message']}")
                logger.info(f"🎭 Active agents: {result.get('agents_launched', [])}")
                return True
            else:
                logger.error(f"❌ Failed to launch AI agents: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error launching AI agents: {e}")
            return False
    
    def generate_test_audio(self, duration=1.0, frequency=440, sample_rate=16000):
        """Generate test audio data (sine wave)"""
        num_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, num_samples, False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        return audio_data
    
    def encode_audio_for_bridge(self, audio_data):
        """Encode audio data as Base64 for the bridge"""
        audio_bytes = audio_data.tobytes()
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        return base64_audio
    
    def send_audio_to_bridge(self, audio_data):
        """Send audio data to the audio bridge endpoint"""
        try:
            base64_audio = self.encode_audio_for_bridge(audio_data)
            
            data = {
                "room_name": self.room_name,
                "audio_data": base64_audio,
                "participant_name": self.participant_name,
                "timestamp": time.time()
            }
            
            response = requests.post(f"{self.backend_url}/audio-bridge", json=data, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🎤 Audio sent: {result['status']} - {result['message']}")
                return result.get('audio_processed', False)
            else:
                logger.error(f"❌ Audio bridge failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending audio to bridge: {e}")
            return False
    
    def test_with_simulated_audio(self):
        """Test the audio bridge with simulated microphone data"""
        logger.info("🎵 Testing with simulated microphone audio...")
        
        # Generate test tones
        test_frequencies = [220, 440, 880]  # A3, A4, A5
        
        for freq in test_frequencies:
            logger.info(f"🎵 Generating test tone: {freq}Hz")
            audio_data = self.generate_test_audio(duration=1.0, frequency=freq)
            
            success = self.send_audio_to_bridge(audio_data)
            if success:
                logger.info(f"✅ {freq}Hz tone successfully sent to AI agents")
            else:
                logger.error(f"❌ {freq}Hz tone failed to reach AI agents")
            
            time.sleep(0.5)
    
    def run_microphone_test(self):
        """Run the complete microphone test"""
        logger.info("🎤 Starting Microphone Bridge Test")
        logger.info("=" * 50)
        
        if not self.test_backend_connection():
            logger.error("❌ Backend not accessible. Make sure the backend is running.")
            return False
        
        logger.info("🤖 Launching AI agents for testing...")
        if not self.launch_ai_agents():
            logger.error("❌ Failed to launch AI agents.")
            return False
        
        logger.info("⏳ Waiting for AI agents to initialize...")
        time.sleep(3)
        
        self.test_with_simulated_audio()
        
        logger.info("=" * 50)
        logger.info("🎤 REAL MICROPHONE TEST INSTRUCTIONS:")
        logger.info("1. Open your frontend at http://localhost:8080")
        logger.info("2. Navigate to /debate/demo")
        logger.info("3. Start speaking into your microphone")
        logger.info("4. Watch the backend logs for audio bridge messages")
        logger.info("5. AI agents should respond to your voice!")
        logger.info("=" * 50)
        
        return True

def main():
    """Main function"""
    tester = MicrophoneTester()
    
    try:
        success = tester.run_microphone_test()
        if success:
            logger.info("🎉 Microphone bridge test completed successfully!")
            logger.info("💡 Your voice system is ready for testing!")
        else:
            logger.error("❌ Microphone bridge test failed.")
            
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 