#!/usr/bin/env python3

"""
Audio Bridge Integration Module
==============================

This module handles forwarding audio data from WebRTC rooms to LiveKit AI agents.
It provides the core functionality to bridge the gap between human participants
using WebRTC and AI agents operating in LiveKit rooms.

Key Features:
- Converts WebRTC audio data to LiveKit-compatible format
- Manages audio streaming to AI agents
- Handles audio processing and buffering
- Provides real-time audio forwarding capabilities
"""

import asyncio
import logging
import numpy as np
import base64
import io
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

try:
    from livekit import rtc
    from livekit.api import AccessToken, VideoGrants
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    logging.warning("LiveKit not available for audio bridge")

logger = logging.getLogger(__name__)

class AudioBridgeManager:
    """Manages audio bridging between WebRTC and LiveKit AI agents"""
    
    def __init__(self, livekit_url: str, api_key: str, api_secret: str):
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.active_bridges: Dict[str, 'AudioBridge'] = {}
        self.audio_buffer_size = 1024  # Audio samples per buffer
        self.sample_rate = 16000  # 16kHz sample rate
        
    async def create_bridge(self, room_name: str) -> 'AudioBridge':
        """Create a new audio bridge for a room"""
        if room_name in self.active_bridges:
            logger.info(f"Audio bridge already exists for room: {room_name}")
            return self.active_bridges[room_name]
            
        bridge = AudioBridge(
            room_name=room_name,
            livekit_url=self.livekit_url,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        await bridge.initialize()
        self.active_bridges[room_name] = bridge
        
        logger.info(f"✅ Audio bridge created for room: {room_name}")
        return bridge
    
    async def get_bridge(self, room_name: str) -> Optional['AudioBridge']:
        """Get existing audio bridge for a room"""
        return self.active_bridges.get(room_name)
    
    async def forward_audio(self, room_name: str, audio_data: np.ndarray, participant_name: str) -> bool:
        """Forward audio data to AI agents in the specified room"""
        bridge = await self.get_bridge(room_name)
        if not bridge:
            logger.warning(f"No audio bridge found for room: {room_name}")
            return False
            
        return await bridge.send_audio_to_agents(audio_data, participant_name)
    
    async def cleanup_bridge(self, room_name: str):
        """Clean up and remove audio bridge for a room"""
        if room_name in self.active_bridges:
            bridge = self.active_bridges[room_name]
            await bridge.cleanup()
            del self.active_bridges[room_name]
            logger.info(f"🧹 Audio bridge cleaned up for room: {room_name}")

class AudioBridge:
    """Individual audio bridge for a specific room"""
    
    def __init__(self, room_name: str, livekit_url: str, api_key: str, api_secret: str):
        self.room_name = room_name
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.room: Optional[rtc.Room] = None
        self.is_connected = False
        self.audio_track: Optional[rtc.LocalAudioTrack] = None
        self.audio_source: Optional[rtc.AudioSource] = None
        
    async def initialize(self):
        """Initialize the audio bridge connection to LiveKit"""
        if not LIVEKIT_AVAILABLE:
            logger.error("LiveKit not available - cannot initialize audio bridge")
            return False
            
        try:
            # Create LiveKit room connection for the audio bridge
            self.room = rtc.Room()
            
            # Generate bridge token
            token = AccessToken()
            token.with_identity(f"audio-bridge-{self.room_name}")
            token.with_name("Audio Bridge")
            token.with_grants(VideoGrants(
                room_join=True,
                room=self.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))
            
            bridge_token = token.to_jwt()
            
            # Connect to room
            await self.room.connect(self.livekit_url, bridge_token)
            self.is_connected = True
            
            # Create audio source for streaming
            self.audio_source = rtc.AudioSource(16000, 1)  # 16kHz, mono
            self.audio_track = rtc.LocalAudioTrack.create_audio_track(
                "bridge-audio", self.audio_source
            )
            
            # Publish the audio track
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE
            await self.room.local_participant.publish_track(self.audio_track, options)
            
            logger.info(f"🎵 Audio bridge connected to room: {self.room_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize audio bridge: {str(e)}")
            return False
    
    async def send_audio_to_agents(self, audio_data: np.ndarray, participant_name: str) -> bool:
        """Send audio data to AI agents via LiveKit"""
        if not self.is_connected or not self.audio_source:
            logger.warning("Audio bridge not connected - cannot send audio")
            return False
            
        try:
            # Ensure audio data is the right format (16-bit PCM, 16kHz)
            if audio_data.dtype != np.int16:
                # Convert float32 to int16
                if audio_data.dtype == np.float32:
                    audio_data = (audio_data * 32767).astype(np.int16)
                else:
                    audio_data = audio_data.astype(np.int16)
            
            # Create audio frame
            audio_frame = rtc.AudioFrame(
                data=audio_data.tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=len(audio_data)
            )
            
            # Send to audio source
            await self.audio_source.capture_frame(audio_frame)
            
            logger.debug(f"🎤 Forwarded {len(audio_data)} audio samples from {participant_name} to AI agents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to agents: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up the audio bridge connection"""
        try:
            if self.audio_track:
                await self.room.local_participant.unpublish_track(self.audio_track)
                
            if self.room and self.is_connected:
                await self.room.disconnect()
                
            self.is_connected = False
            logger.info(f"🧹 Audio bridge cleaned up for room: {self.room_name}")
            
        except Exception as e:
            logger.error(f"Error cleaning up audio bridge: {str(e)}")

class AudioProcessor:
    """Processes and formats audio data for AI agents"""
    
    @staticmethod
    def decode_webrtc_audio(base64_audio: str) -> np.ndarray:
        """Decode base64 encoded Float32Array from WebRTC"""
        try:
            # Decode base64 to bytes
            audio_bytes = base64.b64decode(base64_audio)
            
            # Convert bytes to numpy Float32Array
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Error decoding WebRTC audio: {str(e)}")
            raise
    
    @staticmethod
    def prepare_for_ai_agents(audio_data: np.ndarray, target_sample_rate: int = 16000) -> np.ndarray:
        """Prepare audio data for AI agent consumption"""
        try:
            # Ensure audio is in the right format for AI processing
            if audio_data.dtype == np.float32:
                # Convert float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # TODO: Add resampling if needed
            # For now, assume input is already 16kHz
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error preparing audio for AI agents: {str(e)}")
            raise

# Global audio bridge manager instance
_bridge_manager: Optional[AudioBridgeManager] = None

def initialize_audio_bridge_manager(livekit_url: str, api_key: str, api_secret: str) -> AudioBridgeManager:
    """Initialize the global audio bridge manager"""
    global _bridge_manager
    _bridge_manager = AudioBridgeManager(livekit_url, api_key, api_secret)
    return _bridge_manager

def get_audio_bridge_manager() -> Optional[AudioBridgeManager]:
    """Get the global audio bridge manager"""
    return _bridge_manager

async def process_webrtc_audio_for_agents(
    room_name: str, 
    base64_audio: str, 
    participant_name: str
) -> Dict[str, Any]:
    """
    Main function to process WebRTC audio and forward it to AI agents
    
    Args:
        room_name: The room where AI agents are running
        base64_audio: Base64 encoded Float32Array from WebRTC
        participant_name: Name of the participant sending audio
        
    Returns:
        Dict with processing results and status
    """
    try:
        # Decode the audio data
        audio_data = AudioProcessor.decode_webrtc_audio(base64_audio)
        
        # Prepare for AI agents
        processed_audio = AudioProcessor.prepare_for_ai_agents(audio_data)
        
        # Get the bridge manager
        bridge_manager = get_audio_bridge_manager()
        if not bridge_manager:
            return {
                "status": "error",
                "message": "Audio bridge manager not initialized",
                "audio_processed": False
            }
        
        # Forward audio to AI agents
        success = await bridge_manager.forward_audio(room_name, processed_audio, participant_name)
        
        return {
            "status": "success" if success else "warning",
            "message": f"Audio {'forwarded to' if success else 'failed to reach'} AI agents",
            "room_name": room_name,
            "participant_name": participant_name,
            "audio_samples": len(audio_data),
            "audio_duration_seconds": round(len(audio_data) / 16000, 2),
            "audio_processed": success
        }
        
    except Exception as e:
        logger.error(f"Error processing WebRTC audio: {str(e)}")
        return {
            "status": "error",
            "message": f"Audio processing error: {str(e)}",
            "audio_processed": False
        } 