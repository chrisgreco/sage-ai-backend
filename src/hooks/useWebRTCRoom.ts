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
  createLocalAudioTrack
} from 'livekit-client';
import { useBackendAPI } from './useBackendAPI';

interface UseWebRTCRoomProps {
  roomName: string;
  participantName: string;
  serverUrl?: string;
  onAudioData?: (audioData: Float32Array) => void;
}

export const useWebRTCRoom = ({ roomName, participantName, onAudioData }: UseWebRTCRoomProps) => {
  const [room] = useState(() => new Room());
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [participants, setParticipants] = useState<RemoteParticipant[]>([]);
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(false);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalTrack | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasAttemptedConnection, setHasAttemptedConnection] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [processor, setProcessor] = useState<ScriptProcessorNode | null>(null);

  const { connectToRoom: getConnectionToken } = useBackendAPI();

  // Update participants when room state changes
  useEffect(() => {
    const updateParticipants = () => {
      setParticipants(Array.from(room.remoteParticipants.values()));
    };

    room.on(RoomEvent.ParticipantConnected, updateParticipants);
    room.on(RoomEvent.ParticipantDisconnected, updateParticipants);
    room.on(RoomEvent.Connected, () => {
      console.log('Successfully connected to LiveKit room');
      setIsConnected(true);
      setIsConnecting(false);
      setError(null);
      updateParticipants();
    });
    room.on(RoomEvent.Disconnected, (reason) => {
      console.log('Disconnected from LiveKit room:', reason);
      setIsConnected(false);
      setIsConnecting(false);
      // Don't auto-reconnect to prevent loops
    });

    // Handle connection errors
    room.on(RoomEvent.ConnectionQualityChanged, (quality, participant) => {
      console.log('Connection quality changed:', quality, participant?.identity);
    });

    // Handle incoming audio tracks
    room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
      if (track.kind === Track.Kind.Audio) {
        const audioElement = track.attach();
        if (audioElement) {
          document.body.appendChild(audioElement);
        }
      }
    });

    return () => {
      room.removeAllListeners();
    };
  }, [room]);

  const setupAudioCapture = useCallback(async (track: LocalTrack) => {
    if (!onAudioData) return;

    try {
      // Create audio context for capturing microphone data
      const ctx = new AudioContext({ sampleRate: 24000 });
      const stream = new MediaStream([track.mediaStreamTrack]);
      const source = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(4096, 1, 1);

      proc.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        onAudioData(new Float32Array(inputData));
      };

      source.connect(proc);
      proc.connect(ctx.destination);

      setAudioContext(ctx);
      setProcessor(proc);
      
      console.log('Audio capture setup complete');
    } catch (err) {
      console.error('Failed to setup audio capture:', err);
    }
  }, [onAudioData]);

  const connectToRoom = useCallback(async () => {
    if (isConnecting || isConnected || hasAttemptedConnection) {
      console.log('Connection already in progress or established, skipping...');
      return;
    }

    try {
      setIsConnecting(true);
      setError(null);
      setHasAttemptedConnection(true);
      console.log(`Attempting to connect to room: ${roomName}`);

      // Use the new backend API to get connection token
      const connectionData = await getConnectionToken();

      console.log('Token received successfully, connecting to LiveKit...');
      console.log('Server URL:', connectionData.livekit_url);
      console.log('Token length:', connectionData.token.length);
      
      // Connect to LiveKit server using backend token
      await room.connect(connectionData.livekit_url, connectionData.token);
      console.log(`Successfully connected to LiveKit at: ${connectionData.livekit_url}`);

    } catch (err) {
      console.error('Failed to connect to room:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to room');
      setIsConnecting(false);
      setHasAttemptedConnection(false);
    }
  }, [room, roomName, isConnecting, isConnected, hasAttemptedConnection, getConnectionToken]);

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
    
    room.disconnect();
    if (localAudioTrack) {
      localAudioTrack.stop();
      setLocalAudioTrack(null);
    }
    setIsMicrophoneEnabled(false);
    setHasAttemptedConnection(false); // Reset for potential reconnection
  }, [room, localAudioTrack, processor, audioContext]);

  const toggleMicrophone = useCallback(async () => {
    if (!isConnected) {
      console.log('Not connected, cannot toggle microphone');
      return;
    }

    try {
      if (isMicrophoneEnabled && localAudioTrack) {
        // Disable microphone
        await room.localParticipant.unpublishTrack(localAudioTrack);
        localAudioTrack.stop();
        setLocalAudioTrack(null);
        setIsMicrophoneEnabled(false);
        console.log('Microphone disabled');
      } else {
        // Enable microphone
        console.log('Enabling microphone...');
        const audioTrack = await createLocalAudioTrack();
        await room.localParticipant.publishTrack(audioTrack);
        setLocalAudioTrack(audioTrack);
        setIsMicrophoneEnabled(true);
        
        // Setup audio capture for AI
        await setupAudioCapture(audioTrack);
        
        console.log('Microphone enabled');
      }
    } catch (err) {
      console.error('Failed to toggle microphone:', err);
      setError(err instanceof Error ? err.message : 'Failed to toggle microphone');
    }
  }, [room, isMicrophoneEnabled, localAudioTrack, isConnected, setupAudioCapture]);

  return {
    room,
    isConnected,
    isConnecting,
    participants,
    isMicrophoneEnabled,
    error,
    connectToRoom,
    disconnectFromRoom,
    toggleMicrophone
  };
};
