
import { useState, useCallback } from 'react';

interface CreateDebateResponse {
  status: string;
  message: string;
  room_name: string;
  token: string;
  livekit_url: string;
}

interface ConnectResponse {
  status: string;
  message: string;
  livekit_url: string;
  token: string;
}

const BACKEND_API_URL = 'https://sage-ai-backend.onrender.com';

export const useBackendAPI = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createDebate = useCallback(async (topic: string, roomName?: string): Promise<CreateDebateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_API_URL}/debate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic,
          room_name: roomName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Debate created:', data);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create debate';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const connectToRoom = useCallback(async (): Promise<ConnectResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_API_URL}/connect`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Connection token received:', data);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to room';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/health`);
      return response.ok;
    } catch (err) {
      console.error('Backend health check failed:', err);
      return false;
    }
  }, []);

  return {
    createDebate,
    connectToRoom,
    checkHealth,
    isLoading,
    error
  };
};
