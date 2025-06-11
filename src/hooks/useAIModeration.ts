
import { useState, useEffect, useCallback } from 'react';
import type { UseAIModerationProps, UseAIModerationReturn } from '@/types/aiModeration';
import { useLiveKitAgent } from './useLiveKitAgent';

export const useAIModeration = ({ roomId, isConnected, agents }: UseAIModerationProps): UseAIModerationReturn => {
  const [error, setError] = useState<string | null>(null);

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
    // Audio is automatically handled by LiveKit Agents
    // No need to manually send audio data
    console.log('Audio data will be processed by LiveKit Agent automatically');
  }, []);

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
