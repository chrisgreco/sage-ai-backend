
import { useState, useCallback, useRef, useEffect } from 'react';
import { 
  Room, 
  RoomEvent, 
  RemoteParticipant,
  LocalParticipant,
  Track,
  RemoteTrack,
  RemoteTrackPublication
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
        
        // Add initial connection message
        setTranscript(prev => [...prev, {
          speaker: 'System',
          text: 'Connected to AI moderation agents. Start speaking to see live transcription.',
          timestamp: new Date()
        }]);
      });

      room.on(RoomEvent.Disconnected, (reason) => {
        console.log('Disconnected from LiveKit Agent room:', reason);
        setIsConnected(false);
        setIsConnecting(false);
        setActiveAgent(null);
        onConnectionChange?.(false, false);
      });

      // Handle incoming audio tracks and transcription
      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        console.log('Track subscribed:', track.kind, participant.identity);
        
        if (track.kind === Track.Kind.Audio) {
          console.log('Agent audio track subscribed from:', participant.identity);
          setActiveAgent(participant.identity);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          console.log('Agent stopped speaking');
          setActiveAgent(null);
        }
      });

      // Enhanced data message handling
      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
        try {
          const message = JSON.parse(new TextDecoder().decode(payload));
          console.log('Received data from agent:', message, 'from participant:', participant?.identity);
          
          // Handle different message types from the Python agent
          switch (message.type) {
            case 'moderation_status':
              console.log('Moderation status update:', message);
              onMessage?.(message);
              break;
              
            case 'transcript':
            case 'transcription':
              console.log('Adding transcript entry:', message);
              setTranscript(prev => [...prev, {
                speaker: message.speaker || participant?.identity || 'User',
                text: message.text || message.content || message.transcript,
                timestamp: new Date()
              }]);
              break;
              
            case 'agent_intervention':
            case 'agent_response':
              console.log('Agent intervention:', message);
              setActiveAgent(message.agent || participant?.identity || 'AI Agent');
              setTranscript(prev => [...prev, {
                speaker: message.agent || participant?.identity || 'AI Agent',
                text: message.text || message.response,
                timestamp: new Date()
              }]);
              break;
              
            case 'user_speech':
            case 'speech_detected':
              console.log('User speech detected:', message);
              setTranscript(prev => [...prev, {
                speaker: 'You',
                text: message.text || message.transcript,
                timestamp: new Date()
              }]);
              break;
              
            case 'system_message':
              console.log('System message:', message);
              setTranscript(prev => [...prev, {
                speaker: 'System',
                text: message.text || message.message,
                timestamp: new Date()
              }]);
              break;
              
            default:
              console.log('Unknown message type:', message.type, message);
              // Try to extract any text content for display
              if (message.text || message.content) {
                setTranscript(prev => [...prev, {
                  speaker: participant?.identity || 'Agent',
                  text: message.text || message.content,
                  timestamp: new Date()
                }]);
              }
          }
        } catch (err) {
          console.error('Error parsing agent data:', err, 'Raw payload:', new TextDecoder().decode(payload));
        }
      });

      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log('Agent participant connected:', participant.identity);
        
        setTranscript(prev => [...prev, {
          speaker: 'System',
          text: `${participant.identity} has joined the moderation session.`,
          timestamp: new Date()
        }]);
      });

      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        console.log('Agent participant disconnected:', participant.identity);
        
        setTranscript(prev => [...prev, {
          speaker: 'System',
          text: `${participant.identity} has left the moderation session.`,
          timestamp: new Date()
        }]);
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
    setTranscript([]);
    onConnectionChange?.(false, false);
  }, [onConnectionChange]);

  const updateAgents = useCallback(async (newAgents: AIAgent[]) => {
    if (!roomRef.current || !isConnected) return;

    try {
      // Send agent configuration update to the room
      const agentUpdate = {
        type: 'update_agents',
        agents: newAgents.filter(a => a.active),
        timestamp: Date.now()
      };

      await roomRef.current.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(agentUpdate))
      );

      console.log('Sent agent update to LiveKit Agent:', agentUpdate);
      
      setTranscript(prev => [...prev, {
        speaker: 'System',
        text: `Updated AI agents: ${newAgents.filter(a => a.active).map(a => a.name).join(', ')}`,
        timestamp: new Date()
      }]);
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
