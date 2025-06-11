
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseOpenAIRealtimeProps {
  onMessage?: (message: any) => void;
  agentPersona?: string;
}

export const useOpenAIRealtime = ({ onMessage, agentPersona = 'Socrates' }: UseOpenAIRealtimeProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(async () => {
    if (isConnecting || isConnected) return;

    try {
      setIsConnecting(true);
      setError(null);

      // Connect to our Supabase edge function WebSocket relay
      const projectId = 'zpfouxphwgtqhgalzyqk';
      const wsUrl = `wss://${projectId}.functions.supabase.co/functions/v1/openai-realtime-relay`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`${agentPersona} AI agent connected`);
        setIsConnected(true);
        setIsConnecting(false);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log(`${agentPersona} received:`, message);
          onMessage?.(message);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        console.log(`${agentPersona} AI agent disconnected`);
        setIsConnected(false);
        setIsConnecting(false);
      };

      ws.onerror = (error) => {
        console.error(`${agentPersona} WebSocket error:`, error);
        setError('Failed to connect to AI agent');
        setIsConnecting(false);
      };

    } catch (err) {
      console.error('Error connecting to OpenAI:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setIsConnecting(false);
    }
  }, [isConnecting, isConnected, agentPersona, onMessage]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage
  };
};
