
import { useState, useEffect, useCallback, useRef } from 'react';
import type { UseAIModerationProps, UseAIModerationReturn, TranscriptEntry } from '@/types/aiModeration';
import { useAIWebSocket } from './useAIWebSocket';
import { determineActiveAgent, encodeAudioForAI } from '@/utils/aiModerationUtils';

export const useAIModeration = ({ roomId, isConnected, agents }: UseAIModerationProps): UseAIModerationReturn => {
  const [aiConnected, setAiConnected] = useState(false);
  const [aiConnecting, setAiConnecting] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // Use refs to avoid dependency changes
  const agentsRef = useRef(agents);
  const isConnectedRef = useRef(isConnected);
  
  // Update refs when props change
  useEffect(() => {
    agentsRef.current = agents;
  }, [agents]);
  
  useEffect(() => {
    isConnectedRef.current = isConnected;
  }, [isConnected]);

  const handleConnectionChange = useCallback((connected: boolean, connecting: boolean) => {
    setAiConnected(connected);
    setAiConnecting(connecting);
  }, []);

  const handleAIMessage = useCallback((message: any) => {
    console.log('AI message received:', message.type, message);
    
    switch (message.type) {
      case 'response.audio_transcript.delta':
        if (message.delta) {
          const agentName = determineActiveAgent(agentsRef.current, message);
          setActiveAgent(agentName);
          
          setTranscript(prev => {
            const lastEntry = prev[prev.length - 1];
            if (lastEntry && lastEntry.speaker === agentName) {
              return [
                ...prev.slice(0, -1),
                { ...lastEntry, text: lastEntry.text + message.delta }
              ];
            } else {
              return [
                ...prev,
                { speaker: agentName, text: message.delta, timestamp: new Date() }
              ];
            }
          });
        }
        break;
      
      case 'response.audio_transcript.done':
        setActiveAgent(null);
        break;
      
      case 'input_audio_buffer.speech_started':
        console.log('User started speaking');
        break;
      
      case 'input_audio_buffer.speech_stopped':
        console.log('User stopped speaking, AI analyzing...');
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (message.transcript) {
          console.log('User transcript completed:', message.transcript);
          setTranscript(prev => [
            ...prev,
            { speaker: 'You', text: message.transcript, timestamp: new Date() }
          ]);
        }
        break;

      case 'error':
        console.error('AI error:', message);
        setError(message.error?.message || 'AI error occurred');
        break;
        
      default:
        console.log('Unhandled AI message type:', message.type);
    }
  }, []);

  // Always call useAIWebSocket with stable dependencies
  const { connect, disconnect, sendMessage, isSessionConfigured } = useAIWebSocket({
    onMessage: handleAIMessage,
    onConnectionChange: handleConnectionChange,
    onError: setError,
    agents: [] // Use empty array to avoid dependency changes
  });

  // Connect to AI moderation when WebRTC is connected
  useEffect(() => {
    if (isConnectedRef.current && !aiConnected && !aiConnecting) {
      console.log('WebRTC connected, connecting to AI...');
      connect();
    } else if (!isConnectedRef.current && (aiConnected || aiConnecting)) {
      console.log('WebRTC disconnected, disconnecting from AI...');
      disconnect();
    }
  }, [isConnected, aiConnected, aiConnecting, connect, disconnect]);

  const sendAudioToAI = useCallback((audioData: Float32Array) => {
    if (!isSessionConfigured()) {
      console.warn('Session not configured, skipping audio data');
      return;
    }

    try {
      const base64Audio = encodeAudioForAI(audioData);
      const audioMessage = {
        type: 'input_audio_buffer.append',
        audio: base64Audio
      };
      console.log('Sending audio data to AI, length:', audioData.length);
      sendMessage(audioMessage);
    } catch (err) {
      console.error('Error sending audio to AI:', err);
    }
  }, [sendMessage, isSessionConfigured]);

  const connectToAI = useCallback(() => {
    if (!aiConnecting && !aiConnected) {
      connect();
    }
  }, [aiConnecting, aiConnected, connect]);

  const disconnectFromAI = useCallback(() => {
    disconnect();
  }, [disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
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
