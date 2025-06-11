
import { useState, useEffect, useCallback } from 'react';
import type { UseAIModerationProps, UseAIModerationReturn } from '@/types/aiModeration';
import { useLiveKitAgent } from './useLiveKitAgent';

export const useAIModeration = ({ roomId, isConnected, agents }: UseAIModerationProps): UseAIModerationReturn => {
  const [error, setError] = useState<string | null>(null);
  const [audioDataReceived, setAudioDataReceived] = useState(0);

  const handleMessage = useCallback((message: any) => {
    console.log('AI moderation message:', message);
    // Handle agent status updates, interventions, etc.
  }, []);

  const handleConnectionChange = useCallback((connected: boolean, connecting: boolean) => {
    console.log('LiveKit Agent connection change:', { connected, connecting });
  }, []);

  const handleError = useCallback((error: string | null) => {
    console.log('LiveKit Agent error:', error);
    setError(error);
  }, []);

  const {
    isConnected: aiConnected,
    isConnecting: aiConnecting,
    activeAgent,
    transcript,
    connect,
    disconnect,
    updateAgents,
    room
  } = useLiveKitAgent({
    roomId,
    agents,
    onMessage: handleMessage,
    onConnectionChange: handleConnectionChange,
    onError: handleError
  });

  // Connect when WebRTC is ready
  useEffect(() => {
    if (isConnected && !aiConnected && !aiConnecting) {
      console.log('WebRTC connected, connecting to LiveKit Agent...');
      connect();
    } else if (!isConnected && (aiConnected || aiConnecting)) {
      console.log('WebRTC disconnected, disconnecting from LiveKit Agent...');
      disconnect();
    }
  }, [isConnected, aiConnected, aiConnecting, connect, disconnect]);

  // Update agents when configuration changes
  useEffect(() => {
    if (aiConnected) {
      updateAgents(agents);
    }
  }, [agents, aiConnected, updateAgents]);

  const sendAudioToAI = useCallback((audioData: Float32Array) => {
    // Track audio data being received
    setAudioDataReceived(prev => prev + 1);
    
    // Send data to LiveKit room if connected
    if (room && aiConnected) {
      try {
        // Send audio data as a message to the room for the agent to process
        const audioMessage = {
          type: 'audio_data',
          timestamp: Date.now(),
          audioLength: audioData.length
        };
        
        room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(audioMessage))
        );
        
        console.log('Sent audio data notification to agent:', audioData.length);
      } catch (err) {
        console.error('Error sending audio data to agent:', err);
      }
    } else {
      console.log('Room not ready, audio data buffered');
    }
  }, [room, aiConnected]);

  const connectToAI = useCallback(() => {
    if (!aiConnecting && !aiConnected) {
      console.log('Manual LiveKit Agent connection requested');
      connect();
    }
  }, [aiConnecting, aiConnected, connect]);

  const disconnectFromAI = useCallback(() => {
    console.log('Manual LiveKit Agent disconnection requested');
    disconnect();
  }, [disconnect]);

  return {
    aiConnected,
    aiConnecting,
    activeAgent,
    transcript,
    error,
    sendAudioToAI,
    connectToAI,
    disconnectFromAI
  };
};
