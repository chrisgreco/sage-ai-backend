
import { useState, useCallback, useRef, useEffect } from 'react';
import { 
  Room, 
  RoomEvent, 
  DataReceived,
  RemoteParticipant,
  LocalParticipant 
} from 'livekit-client';
import { supabase } from '@/integrations/supabase/client';
import type { AIAgent, TranscriptEntry } from '@/types/aiModeration';

interface UseLiveKitAgentProps {
  roomId: string;
  agents: AIAgent[];
  onMessage?: (message: any) => void;
  onConnectionChange?: (connected: boolean, connecting: boolean) => void;
  onError?: (error: string | null) => void;
}

export const useLiveKitAgent = ({ 
  roomId, 
  agents, 
  onMessage, 
  onConnectionChange, 
  onError 
}: UseLiveKitAgentProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const roomRef = useRef<Room | null>(null);

  const connect = useCallback(async () => {
    if (isConnecting || isConnected) return;

    try {
      setIsConnecting(true);
      setIsConnected(false);
      onError?.(null);
      onConnectionChange?.(false, true);

      console.log('Connecting to LiveKit Agent for room:', roomId);

      // Get LiveKit token for agent room
      const { data, error: tokenError } = await supabase.functions.invoke('generate-livekit-token', {
        body: { 
          roomId: `sage-debate-${roomId}`,
          participantName: 'User',
          metadata: JSON.stringify({ agents: agents.filter(a => a.active) })
        }
      });

      if (tokenError || !data?.token) {
        throw new Error(tokenError?.message || 'Failed to get room token');
      }

      // Create room and connect
      const room = new Room();
      roomRef.current = room;

      // Set up event handlers
      room.on(RoomEvent.Connected, () => {
        console.log('Connected to LiveKit Agent room');
        setIsConnected(true);
        setIsConnecting(false);
        onConnectionChange?.(true, false);
      });

      room.on(RoomEvent.Disconnected, (reason) => {
        console.log('Disconnected from LiveKit Agent room:', reason);
        setIsConnected(false);
        setIsConnecting(false);
        onConnectionChange?.(false, false);
      });

      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
        try {
          const message = JSON.parse(new TextDecoder().decode(payload));
          console.log('Received data from agent:', message);
          
          if (message.type === 'moderation_status') {
            // Update agent status
            onMessage?.(message);
          } else if (message.type === 'transcript') {
            // Add to transcript
            setTranscript(prev => [...prev, {
              speaker: message.speaker,
              text: message.text,
              timestamp: new Date()
            }]);
          } else if (message.type === 'agent_intervention') {
            // Agent is speaking
            setActiveAgent(message.agent);
            setTranscript(prev => [...prev, {
              speaker: message.agent,
              text: message.text,
              timestamp: new Date()
            }]);
          }
        } catch (err) {
          console.error('Error parsing agent data:', err);
        }
      });

      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log('Agent participant connected:', participant.identity);
        if (participant.identity.includes('agent')) {
          console.log('SAGE moderation agent is now active');
        }
      });

      // Connect to the room
      await room.connect(data.serverUrl, data.token);

    } catch (err) {
      console.error('Error connecting to LiveKit Agent:', err);
      setIsConnecting(false);
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to moderation service';
      onError?.(errorMessage);
      onConnectionChange?.(false, false);
    }
  }, [roomId, agents, isConnecting, isConnected, onMessage, onConnectionChange, onError]);

  const disconnect = useCallback(() => {
    console.log('Disconnecting from LiveKit Agent...');
    roomRef.current?.disconnect();
    roomRef.current = null;
    setIsConnected(false);
    setIsConnecting(false);
    setActiveAgent(null);
    onConnectionChange?.(false, false);
  }, [onConnectionChange]);

  const updateAgents = useCallback(async (newAgents: AIAgent[]) => {
    if (!roomRef.current || !isConnected) return;

    try {
      // Send agent configuration update to the room
      const agentUpdate = {
        type: 'update_agents',
        agents: newAgents.filter(a => a.active)
      };

      await roomRef.current.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(agentUpdate))
      );

      console.log('Sent agent update to LiveKit Agent');
    } catch (err) {
      console.error('Error updating agents:', err);
    }
  }, [isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    activeAgent,
    transcript,
    connect,
    disconnect,
    updateAgents,
    room: roomRef.current
  };
};
