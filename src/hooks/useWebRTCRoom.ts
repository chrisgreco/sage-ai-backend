
import { useState, useEffect, useCallback } from 'react';
import { 
  Room, 
  RoomEvent, 
  Track, 
  RemoteParticipant, 
  RemoteTrackPublication,
  AudioTrack,
  LocalTrack,
  createLocalAudioTrack
} from 'livekit-client';

interface UseWebRTCRoomProps {
  roomName: string;
  participantName: string;
  serverUrl?: string;
}

export const useWebRTCRoom = ({ roomName, participantName, serverUrl = 'wss://sage-livekit.livekit.cloud' }: UseWebRTCRoomProps) => {
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
      setIsConnected(true);
      setIsConnecting(false);
      updateParticipants();
    });
    room.on(RoomEvent.Disconnected, () => {
      setIsConnected(false);
      setIsConnecting(false);
    });

    // Handle incoming audio tracks
    room.on(RoomEvent.TrackSubscribed, (track: RemoteTrackPublication, participant: RemoteParticipant) => {
      if (track.kind === Track.Kind.Audio) {
        const audioElement = track.audioTrack?.attach();
        if (audioElement) {
          document.body.appendChild(audioElement);
        }
      }
    });

    return () => {
      room.removeAllListeners();
    };
  }, [room]);

  const connectToRoom = useCallback(async (token: string) => {
    try {
      setIsConnecting(true);
      setError(null);
      await room.connect(serverUrl, token);
    } catch (err) {
      console.error('Failed to connect to room:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to room');
      setIsConnecting(false);
    }
  }, [room, serverUrl]);

  const disconnectFromRoom = useCallback(() => {
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
      } else {
        // Enable microphone
        const audioTrack = await createLocalAudioTrack();
        await room.localParticipant.publishTrack(audioTrack);
        setLocalAudioTrack(audioTrack);
        setIsMicrophoneEnabled(true);
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
