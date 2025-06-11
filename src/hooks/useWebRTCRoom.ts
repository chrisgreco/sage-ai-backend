
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
import { supabase } from '@/integrations/supabase/client';

interface UseWebRTCRoomProps {
  roomName: string;
  participantName: string;
  serverUrl?: string;
}

export const useWebRTCRoom = ({ roomName, participantName }: UseWebRTCRoomProps) => {
  const [room] = useState(() => new Room());
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [participants, setParticipants] = useState<RemoteParticipant[]>([]);
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(false);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalTrack | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const connectToRoom = useCallback(async () => {
    if (isConnecting || isConnected) {
      console.log('Already connecting or connected, skipping...');
      return;
    }

    try {
      setIsConnecting(true);
      setError(null);
      console.log(`Attempting to connect to room: ${roomName}`);

      // Get LiveKit token from our edge function
      const { data, error: tokenError } = await supabase.functions.invoke('generate-livekit-token', {
        body: { roomId: roomName }
      });

      if (tokenError) {
        console.error('Token error:', tokenError);
        throw new Error(tokenError.message || 'Failed to get room token');
      }

      if (!data?.token) {
        console.error('No token received:', data);
        throw new Error('No token received from server');
      }

      console.log('Token received successfully, connecting to LiveKit...');
      console.log('Server URL:', data.serverUrl);
      console.log('Token length:', data.token.length);
      
      // Connect to your LiveKit server
      await room.connect(data.serverUrl, data.token);
      console.log(`Successfully connected to LiveKit at: ${data.serverUrl}`);

    } catch (err) {
      console.error('Failed to connect to room:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to room');
      setIsConnecting(false);
    }
  }, [room, roomName, isConnecting, isConnected]);

  const disconnectFromRoom = useCallback(() => {
    console.log('Disconnecting from room...');
    room.disconnect();
    if (localAudioTrack) {
      localAudioTrack.stop();
      setLocalAudioTrack(null);
    }
    setIsMicrophoneEnabled(false);
  }, [room, localAudioTrack]);

  const toggleMicrophone = useCallback(async () => {
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
        console.log('Microphone enabled');
      }
    } catch (err) {
      console.error('Failed to toggle microphone:', err);
      setError(err instanceof Error ? err.message : 'Failed to toggle microphone');
    }
  }, [room, isMicrophoneEnabled, localAudioTrack]);

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
