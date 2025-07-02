import { useState, useEffect, useCallback } from 'react';
import { 
  Room, 
  RoomEvent, 
  Track, 
  RemoteParticipant, 
  RemoteTrackPublication,
  RemoteTrack,
  AudioTrack,
  LocalTrack,
  createLocalAudioTrack,
  LocalParticipant
} from 'livekit-client';

interface UseWebRTCRoomReturn {
  room: Room | null;
  isConnected: boolean;
  connecting: boolean;
  error: string | null;
  participants: RemoteParticipant[];
  localParticipant: LocalParticipant | null;
  participantName: string | null;
  isMicrophoneEnabled: boolean;
  connectToRoom: (roomName: string, debateTopic?: string) => Promise<void>;
  disconnectFromRoom: () => void;
  toggleMicrophone: () => Promise<void>;
}

interface UseWebRTCRoomProps {
  roomName: string;
  participantName: string;
  onAudioData?: (audioData: Float32Array) => void;
}

// Generate unique participant name to avoid LiveKit conflicts
const generateUniqueParticipantName = () => {
  const timestamp = Date.now();
  const randomId = Math.random().toString(36).substring(2, 8);
  return `participant-${timestamp}-${randomId}`;
};

export const useWebRTCRoom = ({ roomName, participantName, onAudioData }: UseWebRTCRoomProps): UseWebRTCRoomReturn => {
  const [room, setRoom] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<RemoteParticipant[]>([]);
  const [localParticipant, setLocalParticipant] = useState<LocalParticipant | null>(null);
  const [uniqueParticipantName, setUniqueParticipantName] = useState<string | null>(null);
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(false);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalTrack | null>(null);
  const [hasAttemptedConnection, setHasAttemptedConnection] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [processor, setProcessor] = useState<ScriptProcessorNode | null>(null);

  // Get token with unique participant name
  const getToken = async (roomName: string, debateTopic?: string) => {
    const uniqueName = generateUniqueParticipantName();
    
    console.log('Requesting token for participant:', uniqueName, 'room:', roomName);
    
          const response = await fetch('https://sage-ai-backend-l0en.onrender.com/participant-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        room_name: roomName,
        participant_name: uniqueName,
        topic: debateTopic || "General Discussion"
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get token: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Token received for participant:', uniqueName, 'LiveKit URL:', data.livekit_url);
    return { token: data.token, participantName: uniqueName, livekit_url: data.livekit_url };
  };

  const connectToRoom = useCallback(async (roomName: string, debateTopic?: string) => {
    if (connecting || isConnected || hasAttemptedConnection) {
      console.log('Connection already in progress or established, skipping...');
      return;
    }
    
    try {
      setConnecting(true);
      setError(null);
      setHasAttemptedConnection(true);
      
      // Get token with unique participant name
      const { token, participantName: uniqueName } = await getToken(roomName, debateTopic);
      setUniqueParticipantName(uniqueName);
      
      console.log('Connecting to LiveKit with participant:', uniqueName);
      
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
        publishDefaults: {
          videoSimulcastLayers: [
            { width: 640, height: 360, encoding: { maxBitrate: 1000000 } },
            { width: 320, height: 180, encoding: { maxBitrate: 500000 } },
          ],
        },
      });
      
      // Set up room event listeners
      newRoom.on(RoomEvent.Connected, () => {
        console.log('Connected to room:', roomName, 'as participant:', uniqueName);
        setIsConnected(true);
        setConnecting(false);
        setLocalParticipant(newRoom.localParticipant);
        setError(null);
        setParticipants(Array.from(newRoom.remoteParticipants.values()));
      });
      
      newRoom.on(RoomEvent.Disconnected, (reason) => {
        console.log('Disconnected from room:', reason);
        setIsConnected(false);
        setConnecting(false);
        setLocalParticipant(null);
        setUniqueParticipantName(null);
      });
      
      newRoom.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('Participant connected:', participant.identity);
        setParticipants(prev => [...prev, participant]);
      });
      
      newRoom.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log('Participant disconnected:', participant.identity);
        setParticipants(prev => prev.filter(p => p.identity !== participant.identity));
      });

      // Handle incoming audio tracks
      newRoom.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const audioElement = track.attach();
          if (audioElement) {
            audioElement.setAttribute('data-participant', participant.identity);
            document.body.appendChild(audioElement);
            console.log('Audio track attached for participant:', participant.identity);
          }
        }
      });
      
      // Handle audio track cleanup
      newRoom.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const audioElements = document.querySelectorAll(`audio[data-participant="${participant.identity}"]`);
          audioElements.forEach(element => {
            element.remove();
            console.log('Audio track cleaned up for participant:', participant.identity);
          });
        }
      });
      
      // Connect to LiveKit
      await newRoom.connect('wss://sage-2kpu4z1y.livekit.cloud', token, {
        autoSubscribe: true,
      });
      
      setRoom(newRoom);
      
    } catch (err) {
      console.error('Failed to connect to room:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to debate room';
      setError(errorMessage);
      setConnecting(false);
      setHasAttemptedConnection(false);
    }
  }, [connecting, isConnected, hasAttemptedConnection]);

  const disconnectFromRoom = useCallback(() => {
    console.log('Disconnecting from room...');
    
    // Clean up audio capture
    if (processor) {
      processor.disconnect();
      setProcessor(null);
    }
    if (audioContext) {
      audioContext.close();
      setAudioContext(null);
    }
    
    if (room) {
      room.disconnect();
      setRoom(null);
    }
    if (localAudioTrack) {
      localAudioTrack.stop();
      setLocalAudioTrack(null);
    }
    
    setIsConnected(false);
    setParticipants([]);
    setLocalParticipant(null);
    setUniqueParticipantName(null);
    setIsMicrophoneEnabled(false);
    setHasAttemptedConnection(false);
    setError(null);
  }, [room, localAudioTrack, processor, audioContext]);

  // Set up audio processing when microphone is enabled
  useEffect(() => {
    if (isMicrophoneEnabled && localAudioTrack && onAudioData) {
      console.log('Setting up audio processing for AI moderation');
      
      const setupAudioProcessing = async () => {
        try {
          const context = new (window.AudioContext || (window as any).webkitAudioContext)();
          const source = context.createMediaStreamSource(new MediaStream([localAudioTrack.mediaStreamTrack]));
          const scriptProcessor = context.createScriptProcessor(4096, 1, 1);
          
          scriptProcessor.onaudioprocess = (audioProcessingEvent) => {
            const inputBuffer = audioProcessingEvent.inputBuffer;
            const channelData = inputBuffer.getChannelData(0);
            
            // Send audio data to AI moderation
            if (onAudioData) {
              onAudioData(channelData);
            }
          };
          
          source.connect(scriptProcessor);
          scriptProcessor.connect(context.destination);
          
          setAudioContext(context);
          setProcessor(scriptProcessor);
          
        } catch (err) {
          console.error('Failed to setup audio processing:', err);
        }
      };
      
      setupAudioProcessing();
    }
  }, [isMicrophoneEnabled, localAudioTrack, onAudioData]);

  const toggleMicrophone = useCallback(async () => {
    if (!room) return;

    try {
      if (isMicrophoneEnabled) {
        // Disable microphone
        if (localAudioTrack) {
          await room.localParticipant.unpublishTrack(localAudioTrack);
          localAudioTrack.stop();
          setLocalAudioTrack(null);
        }
        setIsMicrophoneEnabled(false);
      } else {
        // Enable microphone
        const audioTrack = await createLocalAudioTrack({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        });
        
        await room.localParticipant.publishTrack(audioTrack);
        setLocalAudioTrack(audioTrack);
        setIsMicrophoneEnabled(true);
      }
    } catch (err) {
      console.error('Failed to toggle microphone:', err);
      setError('Failed to toggle microphone');
    }
  }, [room, isMicrophoneEnabled, localAudioTrack]);

  // Auto-connect when roomName is provided
  useEffect(() => {
    if (roomName && !hasAttemptedConnection) {
      connectToRoom(roomName);
    }
  }, [roomName, connectToRoom, hasAttemptedConnection]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (room) {
        room.disconnect();
      }
      if (audioContext) {
        audioContext.close();
      }
    };
  }, [room, audioContext]);

  return {
    room,
    isConnected,
    connecting,
    error,
    participants,
    localParticipant,
    participantName: uniqueParticipantName,
    isMicrophoneEnabled,
    connectToRoom,
    disconnectFromRoom,
    toggleMicrophone,
  };
};
