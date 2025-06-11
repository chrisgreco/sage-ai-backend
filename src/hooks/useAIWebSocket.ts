
import { useRef, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
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
  const connectionAttemptRef = useRef(0);

  const configureSession = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not ready for session configuration');
      return;
    }

    const instructions = generateModerationInstructions(agents);

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

    console.log('Configuring AI session with instructions');
    wsRef.current.send(JSON.stringify(sessionUpdate));
  }, [agents]);

  const connect = useCallback(() => {
    try {
      onError(null);
      sessionConfiguredRef.current = false;
      connectionAttemptRef.current += 1;
      const attemptNumber = connectionAttemptRef.current;
      
      onConnectionChange(false, true);
      console.log(`Connecting to AI moderation (attempt ${attemptNumber})...`);

      // Use the correct WebSocket URL format
      const wsUrl = `wss://${window.location.hostname === 'localhost' ? 'localhost:54321' : window.location.hostname}/functions/v1/openai-realtime-relay`;
      console.log('Connecting to WebSocket URL:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Set a connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.log('Connection timeout, closing...');
          ws.close();
          onError('Connection timeout - please check your internet connection');
          onConnectionChange(false, false);
        }
      }, 15000); // 15 second timeout

      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log(`AI moderation WebSocket connected successfully (attempt ${attemptNumber})`);
        onConnectionChange(true, false);
        onError(null);
        connectionAttemptRef.current = 0; // Reset counter on successful connection
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('AI message received:', message.type);
          
          if (message.type === 'connection_status') {
            console.log('Connection status:', message.status, message.message);
            if (message.status === 'disconnected') {
              onConnectionChange(false, false);
              onError(message.message || 'Connection to AI service lost');
              return;
            }
          }
          
          if (message.type === 'session.created' && !sessionConfiguredRef.current) {
            console.log('AI session created, configuring...');
            configureSession();
          } else if (message.type === 'session.updated') {
            console.log('AI session configured successfully');
            sessionConfiguredRef.current = true;
          } else if (message.type === 'error') {
            console.error('AI error:', message.error);
            onError(message.error?.message || 'AI service error');
          }
          
          onMessage(message);
        } catch (err) {
          console.error('Error parsing AI message:', err);
          onError('Failed to process AI response');
        }
      };

      ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log(`AI moderation WebSocket disconnected (attempt ${attemptNumber}):`, event.code, event.reason);
        onConnectionChange(false, false);
        sessionConfiguredRef.current = false;
        
        if (event.code !== 1000) {
          // Only show error if it wasn't a normal closure
          const errorMessage = event.reason || 'AI connection lost unexpectedly';
          onError(errorMessage);
          
          // Auto-reconnect with exponential backoff, but limit attempts
          if (connectionAttemptRef.current < 3) {
            const delay = Math.min(1000 * Math.pow(2, connectionAttemptRef.current - 1), 5000);
            console.log(`Scheduling reconnection in ${delay}ms...`);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, delay);
          } else {
            onError('Failed to connect to AI service after multiple attempts. Please try the Reconnect button.');
          }
        }
      };

      ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error(`AI WebSocket error (attempt ${attemptNumber}):`, error);
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
    connectionAttemptRef.current = 0; // Reset connection attempts
  }, [onConnectionChange, onError]);

  const sendMessage = useCallback((message: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not ready, skipping message');
      return;
    }

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (err) {
      console.error('Error sending message to AI:', err);
      onError('Failed to send message to AI');
    }
  }, [onError]);

  return {
    connect,
    disconnect,
    sendMessage,
    isSessionConfigured: () => sessionConfiguredRef.current
  };
};
