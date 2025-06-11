
import { useRef, useCallback } from 'react';
import type { AIAgent } from '@/types/aiModeration';
import { generateModerationInstructions } from '@/utils/aiModerationUtils';

interface UseAIWebSocketProps {
  onMessage: (message: any) => void;
  onConnectionChange: (connected: boolean, connecting: boolean) => void;
  onError: (error: string | null) => void;
  agents: AIAgent[];
}

export const useAIWebSocket = ({ onMessage, onConnectionChange, onError, agents }: UseAIWebSocketProps) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const sessionConfiguredRef = useRef(false);

  const configureSession = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not ready for session configuration');
      return;
    }

    const activeAgents = agents.filter(agent => agent.active);
    const instructions = generateModerationInstructions(activeAgents);

    const sessionUpdate = {
      type: 'session.update',
      session: {
        modalities: ['text', 'audio'],
        instructions,
        voice: 'alloy',
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        input_audio_transcription: {
          model: 'whisper-1'
        },
        turn_detection: {
          type: 'server_vad',
          threshold: 0.5,
          prefix_padding_ms: 300,
          silence_duration_ms: 1000
        },
        temperature: 0.8,
        max_response_output_tokens: 'inf'
      }
    };

    console.log('Configuring AI session:', sessionUpdate);
    wsRef.current.send(JSON.stringify(sessionUpdate));
  }, [agents]);

  const connect = useCallback(() => {
    try {
      onError(null);
      sessionConfiguredRef.current = false;
      console.log('Connecting to AI moderation...');

      const wsUrl = `wss://zpfouxphwgtqhgalzyqk.supabase.co/functions/v1/openai-realtime-relay`;
      console.log('Connecting to WebSocket URL:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('AI moderation WebSocket connected successfully');
        onConnectionChange(true, false);
        onError(null);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('AI message received:', message.type, message);
          
          if (message.type === 'session.created' && !sessionConfiguredRef.current) {
            console.log('AI session created, configuring...');
            configureSession();
          } else if (message.type === 'session.updated') {
            console.log('AI session configured successfully');
            sessionConfiguredRef.current = true;
          }
          
          onMessage(message);
        } catch (err) {
          console.error('Error parsing AI message:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('AI moderation WebSocket disconnected:', event.code, event.reason);
        onConnectionChange(false, false);
        sessionConfiguredRef.current = false;
        
        if (event.code !== 1000) {
          onError('AI connection lost unexpectedly');
        }
      };

      ws.onerror = (error) => {
        console.error('AI WebSocket error:', error);
        onError('Failed to connect to AI moderation service');
        onConnectionChange(false, false);
      };

    } catch (err) {
      console.error('Error connecting to AI:', err);
      onError(err instanceof Error ? err.message : 'AI connection failed');
      onConnectionChange(false, false);
    }
  }, [onMessage, onConnectionChange, onError, configureSession]);

  const disconnect = useCallback(() => {
    console.log('Disconnecting from AI moderation...');
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
    }
    
    onConnectionChange(false, false);
    onError(null);
    sessionConfiguredRef.current = false;
  }, [onConnectionChange, onError]);

  const sendMessage = useCallback((message: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !sessionConfiguredRef.current) {
      console.warn('WebSocket not ready or session not configured, skipping message');
      return;
    }

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (err) {
      console.error('Error sending message to AI:', err);
    }
  }, []);

  return {
    connect,
    disconnect,
    sendMessage,
    isSessionConfigured: () => sessionConfiguredRef.current
  };
};
