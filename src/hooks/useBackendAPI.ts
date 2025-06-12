
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
      console.log('Creating debate with topic:', topic);
      console.log('Backend URL:', BACKEND_API_URL);
      
      // First check if the backend is healthy
      const healthCheck = await fetch(`${BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!healthCheck.ok) {
        throw new Error(`Backend health check failed (${healthCheck.status})`);
      }

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
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      console.log('Debate created successfully:', data);
      return data;
    } catch (err) {
      console.error('Failed to create debate:', err);
      let errorMessage = 'Failed to create debate';
      
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        errorMessage = 'Unable to connect to the debate server. Please check your internet connection and try again.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
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
      console.log('Getting connection token from backend...');
      const response = await fetch(`${BACKEND_API_URL}/connect`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      console.log('Connection token received:', data);
      return data;
    } catch (err) {
      console.error('Failed to connect to room:', err);
      let errorMessage = 'Failed to connect to room';
      
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        errorMessage = 'Unable to connect to the debate server. Please check your internet connection and try again.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      console.log('Checking backend health...');
      const response = await fetch(`${BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const isHealthy = response.ok;
      console.log('Backend health check result:', isHealthy);
      return isHealthy;
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
