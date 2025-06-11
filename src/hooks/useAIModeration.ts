
import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/integrations/supabase/client';

interface AIAgent {
  name: string;
  role: string;
  active: boolean;
  persona: string;
}

interface UseAIModerationProps {
  roomId: string;
  isConnected: boolean;
  agents: AIAgent[];
}

export const useAIModeration = ({ roomId, isConnected, agents }: UseAIModerationProps) => {
  const [aiConnected, setAiConnected] = useState(false);
  const [aiConnecting, setAiConnecting] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<Array<{ speaker: string; text: string; timestamp: Date }>>([]);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to AI moderation when WebRTC is connected
  useEffect(() => {
    if (isConnected && !aiConnected && !aiConnecting) {
      connectToAI();
    } else if (!isConnected && aiConnected) {
      disconnectFromAI();
    }
  }, [isConnected]);

  const connectToAI = useCallback(async () => {
    if (aiConnecting || aiConnected) return;

    try {
      setAiConnecting(true);
      setError(null);
      console.log('Connecting to AI moderation...');

      // Connect to our OpenAI Realtime relay using the correct WebSocket URL
      const wsUrl = `wss://zpfouxphwgtqhgalzyqk.supabase.co/functions/v1/openai-realtime-relay`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('AI moderation WebSocket connected');
        setAiConnected(true);
        setAiConnecting(false);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleAIMessage(message);
        } catch (err) {
          console.error('Error parsing AI message:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('AI moderation WebSocket disconnected:', event.code, event.reason);
        setAiConnected(false);
        setAiConnecting(false);
        if (event.code !== 1000) { // Not a normal closure
          setError('AI connection lost unexpectedly');
        }
      };

      ws.onerror = (error) => {
        console.error('AI WebSocket error:', error);
        setError('Failed to connect to AI moderation service');
        setAiConnecting(false);
      };

    } catch (err) {
      console.error('Error connecting to AI:', err);
      setError(err instanceof Error ? err.message : 'AI connection failed');
      setAiConnecting(false);
    }
  }, [aiConnecting, aiConnected]);

  const handleAIMessage = useCallback((message: any) => {
    console.log('AI message received:', message);

    switch (message.type) {
      case 'session.created':
        console.log('AI session created, configuring...');
        configureSession();
        break;
      
      case 'response.audio_transcript.delta':
        if (message.delta) {
          // AI is speaking
          const agentName = determineActiveAgent(message);
          setActiveAgent(agentName);
          
          // Add to transcript
          setTranscript(prev => {
            const lastEntry = prev[prev.length - 1];
            if (lastEntry && lastEntry.speaker === agentName) {
              // Append to existing entry
              return [
                ...prev.slice(0, -1),
                { ...lastEntry, text: lastEntry.text + message.delta }
              ];
            } else {
              // New entry
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
        // Add user speech indicator
        setTranscript(prev => [
          ...prev,
          { speaker: 'You', text: '(speaking...)', timestamp: new Date() }
        ]);
        break;
      
      case 'input_audio_buffer.speech_stopped':
        console.log('User stopped speaking, AI analyzing...');
        // Remove the "speaking..." indicator
        setTranscript(prev => prev.filter(entry => entry.text !== '(speaking...)'));
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (message.transcript) {
          // Add user's completed transcript
          setTranscript(prev => [
            ...prev.filter(entry => entry.text !== '(speaking...)'),
            { speaker: 'You', text: message.transcript, timestamp: new Date() }
          ]);
        }
        break;

      case 'error':
        console.error('AI error:', message);
        setError(message.error?.message || 'AI error occurred');
        break;
    }
  }, []);

  const configureSession = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    // Get active agents' instructions
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

  const generateModerationInstructions = (activeAgents: AIAgent[]): string => {
    const agentDescriptions = activeAgents.map(agent => 
      `${agent.name} (${agent.role}): ${agent.persona}`
    ).join('\n');

    return `You are part of a multi-agent AI moderation system for live voice debates. 

Active moderators:
${agentDescriptions}

Your role depends on your assigned persona. Only speak when your specific moderation criteria are met:
- Socrates: Ask clarifying questions when assumptions are made
- Solon: Enforce rules when violations occur (interruptions, personal attacks)
- Buddha: Intervene when tone becomes aggressive or hostile
- Hermes: Summarize key points during natural breaks
- Aristotle: Request sources for factual claims

Keep interventions brief (1-2 sentences), polite, and focused on your specific role. Only one agent should speak at a time.`;
  };

  const determineActiveAgent = (message: any): string => {
    // For now, rotate between agents or use a simple mapping
    // In a full implementation, this would be more sophisticated
    const activeAgentsList = agents.filter(a => a.active);
    if (activeAgentsList.length === 0) return 'AI Moderator';
    
    // Simple rotation for demo - in production this would be smarter
    const index = Math.floor(Math.random() * activeAgentsList.length);
    return activeAgentsList[index].name;
  };

  const sendAudioToAI = useCallback((audioData: Float32Array) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not ready, skipping audio data');
      return;
    }

    // Convert Float32Array to base64 PCM16
    const int16Array = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      const s = Math.max(-1, Math.min(1, audioData[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = '';
    const chunkSize = 0x8000;
    
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
      const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length));
      binary += String.fromCharCode.apply(null, Array.from(chunk));
    }
    
    const base64Audio = btoa(binary);

    const audioMessage = {
      type: 'input_audio_buffer.append',
      audio: base64Audio
    };

    wsRef.current.send(JSON.stringify(audioMessage));
  }, []);

  const disconnectFromAI = useCallback(() => {
    console.log('Disconnecting from AI moderation...');
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setAiConnected(false);
    setActiveAgent(null);
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnectFromAI();
    };
  }, [disconnectFromAI]);

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
