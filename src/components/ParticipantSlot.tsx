
import React from 'react';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';

interface ParticipantSlotProps {
  type: 'speaker' | 'listener' | 'agent';
  isActive?: boolean;
  isSpeaking?: boolean;
  participantName?: string;
  agentName?: string;
  isConnected?: boolean;
  onToggleMic?: () => void;
  onToggleAudio?: () => void;
}

const ParticipantSlot: React.FC<ParticipantSlotProps> = ({
  type,
  isActive = false,
  isSpeaking = false,
  participantName,
  agentName,
  isConnected = false,
  onToggleMic,
  onToggleAudio
}) => {
  const getSlotClasses = () => {
    let baseClasses = 'glass-panel p-3 w-full';
    
    if (type === 'agent') {
      if (isActive) baseClasses += ' ring-2 ring-liquid-400';
    } else {
      if (isActive) baseClasses += ' ring-2 ring-blue-400';
      if (isSpeaking) baseClasses += ' ring-2 ring-green-400';
    }
    
    return baseClasses;
  };

  const getStatusColor = () => {
    if (type === 'agent') return isActive ? 'text-liquid-700' : 'text-content-muted';
    if (isSpeaking) return 'text-green-600';
    if (isActive) return 'text-blue-600';
    return 'text-content-muted';
  };

  const getTypeLabel = () => {
    switch (type) {
      case 'speaker':
        return 'Speaker';
      case 'listener':
        return 'Audience';
      case 'agent':
        return 'AI Agent';
      default:
        return 'Participant';
    }
  };

  return (
    <div className={getSlotClasses()}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Avatar/Icon */}
          <div className={`w-12 h-12 rounded-full glass-panel flex items-center justify-center ${getStatusColor()}`}>
            {type === 'agent' ? (
              <div className="w-6 h-6 bg-gradient-to-br from-liquid-500 to-liquid-600 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">AI</span>
              </div>
            ) : (
              <div className={`w-6 h-6 rounded-full ${isConnected ? 'bg-green-500' : 'bg-content-muted'}`} />
            )}
          </div>
          
          {/* Participant Info */}
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-medium text-content-primary">
                {type === 'agent' ? agentName || 'AI Moderator' : participantName || `${getTypeLabel()} Slot`}
              </h3>
              {isSpeaking && (
                <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full animate-pulse">
                  Speaking
                </span>
              )}
            </div>
            <p className="text-sm text-content-secondary">
              {type === 'agent' ? 'Moderating Discussion' : getTypeLabel()}
              {isConnected && type !== 'agent' && ' • Connected'}
            </p>
          </div>
        </div>
        
        {/* Controls */}
        <div className="flex items-center space-x-2">
          {type === 'speaker' && onToggleMic && (
            <button
              onClick={onToggleMic}
              className={`p-2 rounded-lg transition-all duration-200 hover:scale-105 ${
                isActive 
                  ? 'glass-button bg-green-100 text-green-600 hover:bg-green-200' 
                  : 'glass-button bg-red-100 text-red-600 hover:bg-red-200'
              }`}
            >
              {isActive ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
            </button>
          )}
          
          {(type === 'listener' || type === 'agent') && onToggleAudio && (
            <button
              onClick={onToggleAudio}
              className={`p-2 rounded-lg transition-all duration-200 hover:scale-105 ${
                isActive 
                  ? 'glass-button bg-blue-100 text-blue-600 hover:bg-blue-200' 
                  : 'glass-button bg-content-muted/20 text-content-muted hover:bg-content-muted/30'
              }`}
            >
              {isActive ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>
      
      {/* Speaking indicator */}
      {isSpeaking && (
        <div className="mt-3 flex items-center space-x-1">
          <div className="flex space-x-1">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-green-500 rounded-full animate-pulse"
                style={{
                  height: `${Math.random() * 20 + 10}px`,
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
          <span className="text-xs text-green-600 font-medium ml-2">Audio Active</span>
        </div>
      )}
    </div>
  );
};

export default ParticipantSlot;
