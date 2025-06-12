
import { useState, useCallback, useEffect } from 'react';

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

// Fetch with retry logic for handling sleeping backend
const fetchWithRetry = async (url: string, options: RequestInit, retries = 3, delay = 2000): Promise<Response> => {
  try {
    const response = await fetch(url, options);
    if (response.ok) return response;
    throw new Error(`Failed with status: ${response.status}`);
  } catch (error) {
    if (retries <= 0) throw error;
    console.log(`Request failed, retrying in ${delay}ms... (${retries} retries left)`);
    await new Promise(resolve => setTimeout(resolve, delay));
    return fetchWithRetry(url, options, retries - 1, delay * 1.5); // Exponential backoff
  }
};

export const useBackendAPI = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWarming, setIsWarming] = useState(false);

  // Pre-warm the backend when the hook is first used
  useEffect(() => {
    const preWarmBackend = async () => {
      try {
        setIsWarming(true);
        console.log('Pre-warming backend...');
        await fetchWithRetry(`${BACKEND_API_URL}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }, 5, 3000); // More retries for warming up
        console.log('Backend pre-warming successful');
      } catch (error) {
        console.log('Backend pre-warming failed, it may be asleep or unavailable');
      } finally {
        setIsWarming(false);
      }
    };

    preWarmBackend();
  }, []);

  const createDebate = useCallback(async (topic: string, roomName?: string): Promise<CreateDebateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      console.log('Creating debate with topic:', topic);
      console.log('Backend URL:', BACKEND_API_URL);
      
      const response = await fetchWithRetry(`${BACKEND_API_URL}/debate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic,
          room_name: roomName
        })
      }, 4, 2000); // 4 retries with 2 second initial delay

      const data = await response.json();
      console.log('Debate created successfully:', data);
      return data;
    } catch (err) {
      console.error('Failed to create debate:', err);
      let errorMessage = 'Failed to create debate';
      
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        errorMessage = 'Unable to connect to the debate server. The server may be starting up - please wait a moment and try again.';
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
      const response = await fetchWithRetry(`${BACKEND_API_URL}/connect`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      }, 3, 1500);

      const data = await response.json();
      console.log('Connection token received:', data);
      return data;
    } catch (err) {
      console.error('Failed to connect to room:', err);
      let errorMessage = 'Failed to connect to room';
      
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        errorMessage = 'Unable to connect to the debate server. The server may be starting up - please wait a moment and try again.';
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
      const response = await fetchWithRetry(`${BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }, 2, 1000); // Fewer retries for health checks
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
    error,
    isWarming
  };
};
