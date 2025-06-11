
import React, { useEffect } from 'react';
import { Mic, MicOff, PhoneOff, Users } from 'lucide-react';
import { useWebRTCRoom } from '@/hooks/useWebRTCRoom';
import { useAuth } from '@/hooks/useAuth';

interface WebRTCAudioRoomProps {
  roomId: string;
  onLeave?: () => void;
}

const WebRTCAudioRoom: React.FC<WebRTCAudioRoomProps> = ({ roomId, onLeave }) => {
  const { user } = useAuth();
  
  const {
    isConnected,
    isConnecting,
    participants,
    isMicrophoneEnabled,
    error,
    connectToRoom,
    disconnectFromRoom,
    toggleMicrophone
  } = useWebRTCRoom({
    roomName: roomId,
    participantName: user?.email || 'Anonymous'
  });

  // Auto-connect when component mounts
  useEffect(() => {
    if (!isConnected && !isConnecting) {
      connectToRoom();
    }
  }, [connectToRoom, isConnected, isConnecting]);

  const handleLeaveRoom = () => {
    disconnectFromRoom();
    onLeave?.();
  };

  if (isConnecting) {
    return (
      <div className="glass-panel p-6 max-w-2xl mx-auto">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-content-primary mb-2">Connecting to Room</h2>
          <p className="text-sm text-content-secondary">Setting up audio connection...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 max-w-2xl mx-auto">
      {/* Room Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-content-primary">Audio Room</h2>
          <p className="text-sm text-content-secondary">
            {isConnected ? `Connected to ${roomId}` : 'Disconnected'}
          </p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-content-muted">
          <Users className="w-4 h-4" />
          <span>{participants.length + (isConnected ? 1 : 0)} participants</span>
        </div>
      </div>

      {/* Participants Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {/* Local Participant */}
        {isConnected && (
          <div className="participant-slot speaking text-center">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-2 flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user?.email?.charAt(0).toUpperCase() || 'Y'}
              </span>
            </div>
            <p className="text-sm font-medium text-content-primary truncate">You</p>
            <p className="text-xs text-content-muted">
              {isMicrophoneEnabled ? 'Speaking' : 'Muted'}
            </p>
          </div>
        )}

        {/* Remote Participants */}
        {participants.map((participant) => (
          <div key={participant.sid} className="participant-slot text-center">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-600 rounded-full mx-auto mb-2 flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {participant.identity.charAt(0).toUpperCase()}
              </span>
            </div>
            <p className="text-sm font-medium text-content-primary truncate">
              {participant.identity}
            </p>
            <p className="text-xs text-content-muted">
              {participant.isSpeaking ? 'Speaking' : 'Listening'}
            </p>
          </div>
        ))}

        {/* Empty slots */}
        {Array.from({ length: Math.max(0, 4 - participants.length - 1) }).map((_, index) => (
          <div key={`empty-${index}`} className="participant-slot text-center opacity-50">
            <div className="w-12 h-12 border-2 border-dashed border-content-muted rounded-full mx-auto mb-2 flex items-center justify-center">
              <Users className="w-5 h-5 text-content-muted" />
            </div>
            <p className="text-xs text-content-muted">Waiting...</p>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center space-x-4">
        <button
          onClick={toggleMicrophone}
          disabled={!isConnected}
          className={`glass-button p-4 rounded-full transition-all duration-200 ${
            isMicrophoneEnabled 
              ? 'bg-green-500 text-white hover:bg-green-600' 
              : 'bg-red-500 text-white hover:bg-red-600'
          } disabled:opacity-50`}
        >
          {isMicrophoneEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </button>
        
        <button
          onClick={handleLeaveRoom}
          className="glass-button p-4 rounded-full bg-red-500 text-white hover:bg-red-600 transition-all duration-200"
        >
          <PhoneOff className="w-5 h-5" />
        </button>
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg bg-red-100 border border-red-200">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
    </div>
  );
};

export default WebRTCAudioRoom;
